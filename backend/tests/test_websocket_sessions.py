from __future__ import annotations

import asyncio
import json
import threading
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

import pytest
from fastapi.testclient import TestClient

from meeting_mvp_backend.config import Settings, get_settings
from meeting_mvp_backend.db.models import (
    CaptureMode,
    MeetingSessionStatus,
    SourcePlatform,
    TranslationStatus,
)
from meeting_mvp_backend.main import app, get_websocket_session_orchestrator
from meeting_mvp_backend.quota import QuotaDecision, QuotaDenialReason
from meeting_mvp_backend.stt_providers import SttEvent, SttFinalEvent, SttInterimEvent
from meeting_mvp_backend.translation_providers import FinalTranslationRequest
from meeting_mvp_backend.translation_retries import InMemoryTranslationRetryQueue
from meeting_mvp_backend.usage_events import UsageEventRecord, UsageEventType
from meeting_mvp_backend.ws_sessions import (
    InMemorySessionResumeRegistry,
    WebSocketSessionOrchestrator,
    hash_archive_token,
)

VALID_AUDIO_FORMAT = {
    "sample_rate_hz": 16000,
    "channels": 1,
    "encoding": "pcm16",
}
FIXED_NOW = datetime(2026, 5, 7, 3, 0, tzinfo=UTC)


@dataclass
class StoredSession:
    session_id: str
    client_id: str
    archive_token_hash: str
    source_platform: SourcePlatform
    capture_mode: CaptureMode
    retention_expires_at: datetime
    status: MeetingSessionStatus = MeetingSessionStatus.PENDING_AUDIO
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int = 0
    quota_seconds_consumed: int = 0


@dataclass
class StoredTranscriptSegment:
    segment_id: str
    session_id: str
    sequence: int
    start_ms: int
    end_ms: int
    english_text_final: str
    chinese_text_final: str
    is_key_sentence: bool
    translation_status: TranslationStatus = TranslationStatus.COMPLETED
    asr_confidence: float | None = None


class FakeSessionRepository:
    def __init__(self, initialized_client_ids: set[str] | None = None) -> None:
        self.initialized_client_ids = initialized_client_ids or set()
        self.sessions: dict[str, StoredSession] = {}
        self.transcript_segments: list[StoredTranscriptSegment] = []

    async def client_exists(self, client_id: str) -> bool:
        return client_id in self.initialized_client_ids

    async def create_pending_session(
        self,
        *,
        session_id: uuid.UUID,
        client_id: str,
        archive_token_hash: str,
        source_platform: SourcePlatform,
        capture_mode: CaptureMode,
        retention_expires_at: datetime,
    ) -> None:
        self.sessions[str(session_id)] = StoredSession(
            session_id=str(session_id),
            client_id=client_id,
            archive_token_hash=archive_token_hash,
            source_platform=source_platform,
            capture_mode=capture_mode,
            retention_expires_at=retention_expires_at,
        )

    async def mark_session_active(
        self,
        *,
        session_id: uuid.UUID,
        started_at: datetime,
    ) -> None:
        stored_session = self.sessions[str(session_id)]
        stored_session.status = MeetingSessionStatus.ACTIVE
        stored_session.started_at = started_at

    async def close_session(
        self,
        *,
        session_id: uuid.UUID,
        ended_at: datetime,
        duration_seconds: int,
        quota_seconds_consumed: int,
        status: MeetingSessionStatus,
    ) -> None:
        stored_session = self.sessions[str(session_id)]
        stored_session.status = status
        stored_session.ended_at = ended_at
        stored_session.duration_seconds = duration_seconds
        stored_session.quota_seconds_consumed = quota_seconds_consumed

    async def create_transcript_segment(
        self,
        *,
        session_id: uuid.UUID,
        sequence: int,
        start_ms: int,
        end_ms: int,
        english_text_final: str,
        chinese_text_final: str,
        is_key_sentence: bool,
        translation_status: TranslationStatus = TranslationStatus.COMPLETED,
        asr_confidence: float | None = None,
    ) -> uuid.UUID:
        segment_id = uuid.uuid4()
        self.transcript_segments.append(
            StoredTranscriptSegment(
                segment_id=str(segment_id),
                session_id=str(session_id),
                sequence=sequence,
                start_ms=start_ms,
                end_ms=end_ms,
                english_text_final=english_text_final,
                chinese_text_final=chinese_text_final,
                is_key_sentence=is_key_sentence,
                translation_status=translation_status,
                asr_confidence=asr_confidence,
            ),
        )
        return segment_id


class FakeQuotaService:
    def __init__(
        self,
        *,
        remaining_seconds_today: int = 2400,
        denial_reason: QuotaDenialReason | None = None,
    ) -> None:
        self.remaining_seconds_today = remaining_seconds_today
        self.denial_reason = denial_reason
        self.reserved_session_ids: list[str] = []
        self.released_session_ids: list[str] = []
        self.consumed_seconds: list[int] = []

    async def reserve_active_session(
        self,
        client_id: str,
        session_id: str,
    ) -> QuotaDecision:
        if self.denial_reason is not None:
            return QuotaDecision(
                allowed=False,
                remaining_seconds_today=self.remaining_seconds_today,
                reason=self.denial_reason,
            )
        self.reserved_session_ids.append(session_id)
        return QuotaDecision(
            allowed=True,
            remaining_seconds_today=self.remaining_seconds_today,
            reason=None,
        )

    async def release_active_session(self, client_id: str, session_id: str) -> None:
        self.released_session_ids.append(session_id)

    async def record_consumed_seconds(
        self,
        client_id: str,
        session_id: str,
        seconds: int,
    ) -> QuotaDecision:
        self.consumed_seconds.append(seconds)
        self.remaining_seconds_today = max(self.remaining_seconds_today - seconds, 0)
        return QuotaDecision(
            allowed=self.remaining_seconds_today > 0,
            remaining_seconds_today=self.remaining_seconds_today,
            reason=(
                None
                if self.remaining_seconds_today > 0
                else QuotaDenialReason.DAILY_QUOTA_EXHAUSTED
            ),
        )


class FakeSttProvider:
    def __init__(
        self,
        *,
        events: list[SttEvent] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.closed = False
        self.error = error
        self.events_to_yield = events or []
        self.sent_audio: list[bytes] = []

    async def send_audio(self, payload: bytes) -> None:
        self.sent_audio.append(payload)

    async def events(self) -> AsyncIterator[SttEvent]:
        await asyncio.sleep(0.001)
        if self.error is not None:
            raise self.error
        for event in self.events_to_yield:
            yield event
        while not self.closed:
            await asyncio.sleep(0.001)

    async def close(self) -> None:
        self.closed = True


class FakeInterimTranslationProvider:
    def __init__(
        self,
        *,
        delay_seconds: float = 0,
        error: Exception | None = None,
        translations: list[str] | None = None,
    ) -> None:
        self.closed = False
        self.delay_seconds = delay_seconds
        self.error = error
        self.requested_texts: list[str] = []
        self.started = threading.Event()
        self.translations = translations or []

    async def translate_interim(self, text: str) -> str:
        self.started.set()
        self.requested_texts.append(text)
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        if self.error is not None:
            raise self.error
        if self.translations:
            return self.translations.pop(0)
        return f"中文：{text}"

    async def close(self) -> None:
        self.closed = True


class FakeFinalTranslationProvider:
    def __init__(
        self,
        *,
        delay_seconds: float = 0,
        outcomes: list[str | Exception] | None = None,
    ) -> None:
        self.closed = False
        self.delay_seconds = delay_seconds
        self.outcomes = outcomes or []
        self.requested_translations: list[FinalTranslationRequest] = []
        self.started = threading.Event()

    async def translate_final(self, request: FinalTranslationRequest) -> str:
        self.started.set()
        self.requested_translations.append(request)
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return f"正式中文：{request.text}"

    async def close(self) -> None:
        self.closed = True


class FakeUsageEventRecorder:
    def __init__(self) -> None:
        self.records: list[UsageEventRecord] = []

    async def record_event(
        self,
        *,
        client_id: str,
        event_type: UsageEventType | str,
        payload: dict[str, object] | None = None,
        session_id: uuid.UUID | str | None = None,
    ) -> UsageEventRecord:
        record = UsageEventRecord(
            client_id=client_id,
            session_id=uuid.UUID(str(session_id)) if session_id is not None else None,
            event_type=UsageEventType(event_type),
            payload=payload or {},
            created_at=FIXED_NOW,
        )
        self.records.append(record)
        return record


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self._values = list(values)
        self._last = values[-1] if values else FIXED_NOW

    def __call__(self) -> datetime:
        if self._values:
            self._last = self._values.pop(0)
        return self._last


class JsonWebSocket(Protocol):
    def receive_json(self) -> dict[str, object]: ...


@pytest.fixture(autouse=True)
async def reset_app_overrides() -> AsyncIterator[None]:
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def make_client(
    *,
    repository: FakeSessionRepository,
    quota_service: FakeQuotaService,
    clock: Callable[[], datetime] | None = None,
    resume_registry: InMemorySessionResumeRegistry | None = None,
    stt_provider: FakeSttProvider | None = None,
    translation_min_interval_seconds: float = 0,
    translation_provider: FakeInterimTranslationProvider | None = None,
    translation_retry_queue: InMemoryTranslationRetryQueue | None = None,
    final_translation_provider: FakeFinalTranslationProvider | None = None,
    usage_event_recorder: FakeUsageEventRecorder | None = None,
) -> TestClient:
    settings = Settings()
    settings.public_base_url = "https://meeting.example.test"
    settings.archive_retention_days = 30

    def override_orchestrator() -> WebSocketSessionOrchestrator:
        return WebSocketSessionOrchestrator(
            repository=repository,
            quota_service=quota_service,
            settings=settings,
            clock=clock or (lambda: FIXED_NOW),
            resume_registry=resume_registry,
            stt_provider_factory=(lambda: stt_provider) if stt_provider else None,
            final_translation_provider_factory=(
                (lambda: final_translation_provider)
                if final_translation_provider
                else None
            ),
            translation_retry_queue=translation_retry_queue,
            translation_provider_factory=(
                (lambda: translation_provider) if translation_provider else None
            ),
            translation_min_interval_seconds=translation_min_interval_seconds,
            usage_event_recorder=usage_event_recorder,
        )

    app.dependency_overrides[get_websocket_session_orchestrator] = (
        override_orchestrator
    )
    return TestClient(app)


def session_start_payload(client_id: str) -> dict[str, object]:
    return {
        "type": "session_start",
        "client_id": client_id,
        "capture_mode": "tab_audio",
        "source_platform": "google_meet",
        "audio_format": VALID_AUDIO_FORMAT,
    }


def session_resume_payload(
    *,
    archive_token: str,
    client_id: str,
    session_id: str,
) -> dict[str, object]:
    return {
        "type": "session_resume",
        "client_id": client_id,
        "session_id": session_id,
        "archive_token": archive_token,
        "audio_format": VALID_AUDIO_FORMAT,
    }


def receive_until_message_type(
    websocket: JsonWebSocket,
    message_type: str,
) -> dict[str, object]:
    while True:
        message = websocket.receive_json()
        if message["type"] == message_type:
            return message


def usage_event_types(
    usage_event_recorder: FakeUsageEventRecorder,
) -> list[UsageEventType]:
    return [record.event_type for record in usage_event_recorder.records]


def timeline_items_of_type(
    timeline_update: dict[str, object],
    item_type: str,
) -> list[dict[str, object]]:
    items = timeline_update["items"]
    assert isinstance(items, list)
    return [
        item
        for item in items
        if isinstance(item, dict) and item.get("item_type") == item_type
    ]


def test_session_start_returns_session_started_and_writes_pending_session() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            message = websocket.receive_json()
            session_id = message["session_id"]
            stored_session = repository.sessions[session_id]

            assert message["type"] == "session_started"
            assert message["remaining_seconds_today"] == 2400
            assert message["archive_url"] == (
                f"https://meeting.example.test/archive/{session_id}"
                f"?token={message['archive_token']}"
            )
            assert stored_session.client_id == client_id
            assert stored_session.status is MeetingSessionStatus.PENDING_AUDIO
            assert stored_session.started_at is None
            assert stored_session.archive_token_hash == hash_archive_token(
                message["archive_token"],
            )
            assert stored_session.archive_token_hash != message["archive_token"]
            assert quota_service.reserved_session_ids == [session_id]


def test_usage_events_record_session_lifecycle_without_audio_content() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    usage_events = FakeUsageEventRecorder()
    stt_provider = FakeSttProvider()
    active_at = FIXED_NOW + timedelta(seconds=2)
    stop_at = FIXED_NOW + timedelta(seconds=9)
    clock = SequenceClock(FIXED_NOW, active_at, stop_at)

    with make_client(
        repository=repository,
        quota_service=quota_service,
        clock=clock,
        stt_provider=stt_provider,
        usage_event_recorder=usage_events,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = str(started["session_id"])
            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "audio_status")
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            receive_until_message_type(websocket, "session_closed")

    assert usage_event_types(usage_events) == [
        UsageEventType.CAPTURE_STARTED,
        UsageEventType.QUOTA_CHECKED,
        UsageEventType.SESSION_STARTED,
        UsageEventType.AUDIO_DETECTED,
        UsageEventType.SESSION_CLOSED,
    ]
    assert usage_events.records[0].session_id is None
    assert usage_events.records[0].payload == {
        "capture_mode": "tab_audio",
        "source_platform": "google_meet",
    }
    assert usage_events.records[1].payload == {
        "allowed": True,
        "remaining_seconds_today": 2400,
        "reason": None,
    }
    assert usage_events.records[2].session_id == uuid.UUID(session_id)
    assert "archive_token" not in usage_events.records[2].payload
    assert "archive_url" not in usage_events.records[2].payload
    assert usage_events.records[-1].payload == {
        "duration_seconds": 7,
        "quota_seconds_consumed": 7,
        "reason": "user_stopped",
        "remaining_seconds_today": 2393,
    }
    payload_json = json.dumps(
        [record.payload for record in usage_events.records],
        ensure_ascii=False,
    )
    assert "\\x00" not in payload_json


def test_non_empty_binary_frame_activates_session_then_stop_settles_quota() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    active_at = FIXED_NOW + timedelta(seconds=2)
    stop_at = FIXED_NOW + timedelta(seconds=9)
    clock = SequenceClock(FIXED_NOW, active_at, stop_at)

    with make_client(
        repository=repository,
        quota_service=quota_service,
        clock=clock,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            audio_status = websocket.receive_json()
            websocket.send_json({"type": "heartbeat", "session_id": session_id})
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            quota_update = receive_until_message_type(websocket, "quota_update")
            closed = receive_until_message_type(websocket, "session_closed")

    stored_session = repository.sessions[session_id]

    assert audio_status == {"type": "audio_status", "has_audio": True, "level": None}
    assert quota_update == {
        "type": "quota_update",
        "remaining_seconds_today": 2393,
    }
    assert closed == {"type": "session_closed", "reason": "user_stopped"}
    assert stored_session.status is MeetingSessionStatus.ENDED
    assert stored_session.started_at == active_at
    assert stored_session.ended_at == stop_at
    assert stored_session.duration_seconds == 7
    assert stored_session.quota_seconds_consumed == 7
    assert quota_service.consumed_seconds == [7]
    assert quota_service.released_session_ids == [session_id]


def test_usage_events_record_provider_and_archive_metadata_without_text() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    usage_events = FakeUsageEventRecorder()
    stt_provider = FakeSttProvider(
        events=[
            SttInterimEvent(text="We need to align on the launch timeline."),
            SttFinalEvent(
                sequence=1,
                start_ms=0,
                end_ms=3200,
                text="We need to align on the launch timeline before Friday.",
                confidence=0.91,
            ),
        ],
    )
    translation_provider = FakeInterimTranslationProvider(
        translations=["我们需要对齐上线时间线。"],
    )
    final_translation_provider = FakeFinalTranslationProvider(
        outcomes=["我们需要在周五前对齐上线时间线。"],
    )

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        translation_provider=translation_provider,
        final_translation_provider=final_translation_provider,
        usage_event_recorder=usage_events,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = str(started["session_id"])
            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "audio_status")
            receive_until_message_type(websocket, "translation_interim")
            receive_until_message_type(websocket, "segment_final")
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            receive_until_message_type(websocket, "session_closed")

    recorded_types = usage_event_types(usage_events)
    assert UsageEventType.ASR_INTERIM_RECEIVED in recorded_types
    assert UsageEventType.TRANSLATION_INTERIM_REQUESTED in recorded_types
    assert UsageEventType.ASR_FINAL_RECEIVED in recorded_types
    assert UsageEventType.TRANSLATION_FINAL_COMPLETED in recorded_types
    assert UsageEventType.SEGMENT_ARCHIVED in recorded_types
    segment_archived = [
        record
        for record in usage_events.records
        if record.event_type is UsageEventType.SEGMENT_ARCHIVED
    ][0]
    assert segment_archived.session_id == uuid.UUID(session_id)
    assert segment_archived.payload["sequence"] == 1
    assert segment_archived.payload["translation_status"] == "completed"
    payload_json = json.dumps(
        [record.payload for record in usage_events.records],
        ensure_ascii=False,
    )
    assert "We need to align" not in payload_json
    assert "我们需要" not in payload_json


def test_valid_audio_frame_runs_mock_provider_and_archives_final_segment() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            audio_status = websocket.receive_json()
            asr_interim = websocket.receive_json()
            warning = websocket.receive_json()
            warning_timeline = websocket.receive_json()
            translation_interim = websocket.receive_json()
            segment_final = websocket.receive_json()
            key_sentence = websocket.receive_json()
            timeline_update = websocket.receive_json()
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            websocket.receive_json()
            websocket.receive_json()

    assert audio_status == {"type": "audio_status", "has_audio": True, "level": None}
    assert asr_interim == {
        "type": "asr_interim",
        "text": "We need to align on the launch timeline.",
    }
    assert warning == {
        "type": "warning",
        "code": "mock_qwen_interim_retry",
        "message": "Mock interim provider recovered after a simulated retry.",
    }
    assert warning_timeline["type"] == "timeline_update"
    assert timeline_items_of_type(warning_timeline, "exception") == [
        {
            "id": "exception-mock_qwen_interim_retry-0",
            "item_type": "exception",
            "timestamp_ms": 0,
            "text": "临时理解出现可恢复异常",
            "segment_id": None,
        },
    ]
    assert translation_interim == {
        "type": "translation_interim",
        "text": "我们需要对齐上线时间线。",
    }
    assert segment_final["type"] == "segment_final"
    assert segment_final["sequence"] == 1
    assert segment_final["start_ms"] == 0
    assert segment_final["end_ms"] == 3200
    assert (
        segment_final["english_text_final"]
        == "We need to align on the launch timeline before Friday."
    )
    assert (
        segment_final["chinese_text_final"]
        == "我们需要在周五前对齐上线时间线。"
    )
    assert key_sentence == {
        "type": "key_sentence_update",
        "text": "我们需要在周五前对齐上线时间线。",
    }
    assert timeline_update["type"] == "timeline_update"
    assert [item["item_type"] for item in timeline_update["items"]] == [
        "exception",
        "segment_final",
        "key_sentence",
    ]
    assert timeline_items_of_type(timeline_update, "segment_final") == [
        {
            "id": f"segment-final-{segment_final['segment_id']}",
            "item_type": "segment_final",
            "timestamp_ms": 3200,
            "text": "我们需要在周五前对齐上线时间线。",
            "segment_id": segment_final["segment_id"],
        },
    ]
    assert timeline_items_of_type(timeline_update, "key_sentence") == [
        {
            "id": f"key-sentence-{segment_final['segment_id']}",
            "item_type": "key_sentence",
            "timestamp_ms": 3200,
            "text": "我们需要在周五前对齐上线时间线。",
            "segment_id": segment_final["segment_id"],
        },
    ]

    assert len(repository.transcript_segments) == 1
    stored_segment = repository.transcript_segments[0]
    assert stored_segment.session_id == session_id
    assert stored_segment.sequence == 1
    assert stored_segment.segment_id == segment_final["segment_id"]
    assert (
        stored_segment.english_text_final
        == "We need to align on the launch timeline before Friday."
    )
    assert stored_segment.chinese_text_final == "我们需要在周五前对齐上线时间线。"


def test_binary_frames_stream_to_stt_provider_and_emit_english_results() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttInterimEvent(text="We need to align on the launch timeline."),
            SttFinalEvent(
                sequence=1,
                start_ms=0,
                end_ms=3200,
                text="We need to align on the launch timeline before Friday.",
                confidence=0.91,
            ),
        ],
    )

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            audio_status = websocket.receive_json()
            websocket.send_bytes(b"\x02\x03")
            asr_interim = websocket.receive_json()
            asr_final = websocket.receive_json()
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            receive_until_message_type(websocket, "session_closed")

    assert audio_status == {"type": "audio_status", "has_audio": True, "level": None}
    assert stt_provider.sent_audio == [b"\x00\x01", b"\x02\x03"]
    assert asr_interim == {
        "type": "asr_interim",
        "text": "We need to align on the launch timeline.",
    }
    assert asr_final == {
        "type": "asr_final",
        "sequence": 1,
        "start_ms": 0,
        "end_ms": 3200,
        "text": "We need to align on the launch timeline before Friday.",
        "confidence": 0.91,
    }
    assert repository.transcript_segments == []
    assert stt_provider.closed is True


def test_stt_final_triggers_final_translation_and_archives_segment() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttFinalEvent(
                sequence=1,
                start_ms=0,
                end_ms=3200,
                text="We need to align on the launch timeline before Friday.",
                confidence=0.91,
            ),
        ],
    )
    final_translation_provider = FakeFinalTranslationProvider(
        outcomes=["我们需要在周五前对齐上线时间线。"],
    )

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        final_translation_provider=final_translation_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            audio_status = websocket.receive_json()
            asr_final = receive_until_message_type(websocket, "asr_final")
            segment_final = receive_until_message_type(websocket, "segment_final")
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            remaining_messages = []
            while True:
                message = websocket.receive_json()
                remaining_messages.append(message)
                if message["type"] == "session_closed":
                    break

    assert audio_status == {"type": "audio_status", "has_audio": True, "level": None}
    assert asr_final == {
        "type": "asr_final",
        "sequence": 1,
        "start_ms": 0,
        "end_ms": 3200,
        "text": "We need to align on the launch timeline before Friday.",
        "confidence": 0.91,
    }
    assert segment_final["type"] == "segment_final"
    assert segment_final["sequence"] == 1
    assert segment_final["english_text_final"] == (
        "We need to align on the launch timeline before Friday."
    )
    assert segment_final["chinese_text_final"] == "我们需要在周五前对齐上线时间线。"
    assert [
        message
        for message in remaining_messages
        if message["type"] == "key_sentence_update"
    ] == [
        {
            "type": "key_sentence_update",
            "text": "我们需要在周五前对齐上线时间线。",
        },
    ]
    timeline_updates = [
        message
        for message in remaining_messages
        if message["type"] == "timeline_update"
    ]
    assert len(timeline_updates) == 1
    assert timeline_items_of_type(timeline_updates[0], "segment_final") == [
        {
            "id": f"segment-final-{segment_final['segment_id']}",
            "item_type": "segment_final",
            "timestamp_ms": 3200,
            "text": "我们需要在周五前对齐上线时间线。",
            "segment_id": segment_final["segment_id"],
        },
    ]
    assert timeline_items_of_type(timeline_updates[0], "key_sentence") == [
        {
            "id": f"key-sentence-{segment_final['segment_id']}",
            "item_type": "key_sentence",
            "timestamp_ms": 3200,
            "text": "我们需要在周五前对齐上线时间线。",
            "segment_id": segment_final["segment_id"],
        },
    ]
    assert len(repository.transcript_segments) == 1
    stored_segment = repository.transcript_segments[0]
    assert stored_segment.segment_id == segment_final["segment_id"]
    assert stored_segment.translation_status is TranslationStatus.COMPLETED
    assert stored_segment.is_key_sentence is True
    assert stored_segment.asr_confidence == 0.91
    assert final_translation_provider.requested_translations == [
        FinalTranslationRequest(
            sequence=1,
            text="We need to align on the launch timeline before Friday.",
        ),
    ]
    assert final_translation_provider.closed is True


def test_final_translation_uses_recent_five_successful_segments_as_context() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttFinalEvent(
                sequence=sequence,
                start_ms=(sequence - 1) * 1000,
                end_ms=sequence * 1000,
                text=f"Final English segment {sequence}.",
                confidence=None,
            )
            for sequence in range(1, 8)
        ],
    )
    final_translation_provider = FakeFinalTranslationProvider(
        outcomes=[f"正式中文片段 {sequence}。" for sequence in range(1, 8)],
    )

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        final_translation_provider=final_translation_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "audio_status")
            segment_finals = [
                receive_until_message_type(websocket, "segment_final")
                for _ in range(7)
            ]
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            receive_until_message_type(websocket, "session_closed")

    assert [segment["sequence"] for segment in segment_finals] == list(range(1, 8))
    assert len(repository.transcript_segments) == 7
    requests = final_translation_provider.requested_translations
    assert len(requests) == 7
    assert [segment.sequence for segment in requests[5].context] == [1, 2, 3, 4, 5]
    assert [segment.sequence for segment in requests[6].context] == [2, 3, 4, 5, 6]
    assert requests[6].context[-1].chinese_text_final == "正式中文片段 6。"


def test_final_translation_failure_archives_failed_segment_and_continues() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttFinalEvent(
                sequence=1,
                start_ms=0,
                end_ms=1200,
                text="We need to align.",
                confidence=None,
            ),
            SttFinalEvent(
                sequence=2,
                start_ms=1200,
                end_ms=2400,
                text="The budget review moved to Friday.",
                confidence=None,
            ),
        ],
    )
    final_translation_provider = FakeFinalTranslationProvider(
        outcomes=[
            RuntimeError("qwen final unavailable"),
            "预算审查调整到周五。",
        ],
    )
    translation_retry_queue = InMemoryTranslationRetryQueue()

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        final_translation_provider=final_translation_provider,
        translation_retry_queue=translation_retry_queue,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "audio_status")
            warning = receive_until_message_type(websocket, "warning")
            warning_timeline = receive_until_message_type(websocket, "timeline_update")
            segment_final = receive_until_message_type(websocket, "segment_final")
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            closed = receive_until_message_type(websocket, "session_closed")

    assert warning["code"] == "qwen_final_translation_failed"
    assert timeline_items_of_type(warning_timeline, "exception") == [
        {
            "id": "exception-qwen_final_translation_failed-0",
            "item_type": "exception",
            "timestamp_ms": 1200,
            "text": "中文正式翻译失败，已进入后台补译",
            "segment_id": repository.transcript_segments[0].segment_id,
        },
    ]
    assert segment_final["sequence"] == 2
    assert segment_final["chinese_text_final"] == "预算审查调整到周五。"
    assert closed == {"type": "session_closed", "reason": "user_stopped"}
    assert len(repository.transcript_segments) == 2
    assert repository.transcript_segments[0].sequence == 1
    assert repository.transcript_segments[0].chinese_text_final == ""
    assert (
        repository.transcript_segments[0].translation_status
        is TranslationStatus.FAILED
    )
    assert repository.transcript_segments[1].sequence == 2
    assert (
        repository.transcript_segments[1].translation_status
        is TranslationStatus.COMPLETED
    )
    queued_jobs = asyncio.run(
        translation_retry_queue.pop_due(now=FIXED_NOW, limit=10),
    )
    assert len(queued_jobs) == 1
    assert queued_jobs[0].session_id == uuid.UUID(str(session_id))
    assert queued_jobs[0].segment_id == uuid.UUID(
        repository.transcript_segments[0].segment_id,
    )


def test_stopping_session_cancels_in_flight_final_translation_as_failed() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttFinalEvent(
                sequence=1,
                start_ms=0,
                end_ms=1200,
                text="We need to align.",
                confidence=None,
            ),
        ],
    )
    final_translation_provider = FakeFinalTranslationProvider(delay_seconds=10)

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        final_translation_provider=final_translation_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "audio_status")
            receive_until_message_type(websocket, "asr_final")
            assert final_translation_provider.started.wait(timeout=1)
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            receive_until_message_type(websocket, "session_closed")

    assert final_translation_provider.closed is True
    assert len(repository.transcript_segments) == 1
    assert repository.transcript_segments[0].sequence == 1
    assert repository.transcript_segments[0].chinese_text_final == ""
    assert (
        repository.transcript_segments[0].translation_status
        is TranslationStatus.FAILED
    )


def test_stt_interim_triggers_translation_interim_without_archiving() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttInterimEvent(text="We need to align on the launch timeline."),
        ],
    )
    translation_provider = FakeInterimTranslationProvider(
        translations=["我们需要对齐上线时间线。"],
    )

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        translation_provider=translation_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            audio_status = websocket.receive_json()
            asr_interim = websocket.receive_json()
            translation_interim = websocket.receive_json()
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            receive_until_message_type(websocket, "session_closed")

    assert audio_status == {"type": "audio_status", "has_audio": True, "level": None}
    assert asr_interim == {
        "type": "asr_interim",
        "text": "We need to align on the launch timeline.",
    }
    assert translation_interim == {
        "type": "translation_interim",
        "text": "我们需要对齐上线时间线。",
    }
    assert translation_provider.requested_texts == [
        "We need to align on the launch timeline.",
    ]
    assert repository.transcript_segments == []
    assert translation_provider.closed is True


def test_interim_translation_keeps_latest_text_while_request_is_in_flight() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttInterimEvent(text="We should align."),
            SttInterimEvent(text="We should align."),
            SttInterimEvent(text="The budget moved."),
        ],
    )
    translation_provider = FakeInterimTranslationProvider(
        delay_seconds=0.01,
        translations=["我们应该对齐。", "预算调整了。"],
    )

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        translation_provider=translation_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "audio_status")
            assert receive_until_message_type(websocket, "asr_interim")["text"] == (
                "We should align."
            )
            assert receive_until_message_type(websocket, "asr_interim")["text"] == (
                "We should align."
            )
            assert receive_until_message_type(websocket, "asr_interim")["text"] == (
                "The budget moved."
            )
            first_translation = receive_until_message_type(
                websocket,
                "translation_interim",
            )
            second_translation = receive_until_message_type(
                websocket,
                "translation_interim",
            )
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            receive_until_message_type(websocket, "session_closed")

    assert first_translation["text"] == "我们应该对齐。"
    assert second_translation["text"] == "预算调整了。"
    assert translation_provider.requested_texts == [
        "We should align.",
        "The budget moved.",
    ]
    assert repository.transcript_segments == []


def test_interim_translation_failure_does_not_block_asr_final() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttInterimEvent(text="We need to align."),
            SttFinalEvent(
                sequence=1,
                start_ms=0,
                end_ms=1200,
                text="We need to align.",
                confidence=None,
            ),
        ],
    )
    translation_provider = FakeInterimTranslationProvider(
        error=RuntimeError("qwen text unavailable"),
    )

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        translation_provider=translation_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "audio_status")
            asr_interim = receive_until_message_type(websocket, "asr_interim")
            asr_final = receive_until_message_type(websocket, "asr_final")
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            closed = receive_until_message_type(websocket, "session_closed")

    assert asr_interim["text"] == "We need to align."
    assert asr_final == {
        "type": "asr_final",
        "sequence": 1,
        "start_ms": 0,
        "end_ms": 1200,
        "text": "We need to align.",
        "confidence": None,
    }
    assert closed == {"type": "session_closed", "reason": "user_stopped"}
    assert translation_provider.requested_texts == ["We need to align."]
    assert translation_provider.closed is True
    assert repository.transcript_segments == []


def test_interim_translation_failure_sends_recoverable_warning() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttInterimEvent(text="We need to align."),
        ],
    )
    translation_provider = FakeInterimTranslationProvider(
        error=RuntimeError("qwen text unavailable"),
    )

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        translation_provider=translation_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "audio_status")
            asr_interim = receive_until_message_type(websocket, "asr_interim")
            warning = receive_until_message_type(websocket, "warning")
            warning_timeline = receive_until_message_type(websocket, "timeline_update")
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            closed = receive_until_message_type(websocket, "session_closed")

    assert asr_interim["text"] == "We need to align."
    assert warning == {
        "type": "warning",
        "code": "qwen_interim_translation_failed",
        "message": "中文临时理解暂时不可用，英文转写会继续。",
    }
    assert timeline_items_of_type(warning_timeline, "exception") == [
        {
            "id": "exception-qwen_interim_translation_failed-0",
            "item_type": "exception",
            "timestamp_ms": 0,
            "text": "中文临时理解暂时不可用",
            "segment_id": None,
        },
    ]
    assert closed == {"type": "session_closed", "reason": "user_stopped"}
    assert repository.transcript_segments == []


def test_stopping_session_cancels_in_flight_interim_translation() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(
        events=[
            SttInterimEvent(text="We need to align."),
        ],
    )
    translation_provider = FakeInterimTranslationProvider(delay_seconds=10)

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        translation_provider=translation_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "audio_status")
            receive_until_message_type(websocket, "asr_interim")
            assert translation_provider.started.wait(timeout=1)
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            receive_until_message_type(websocket, "session_closed")

    assert translation_provider.closed is True


def test_qwen_asr_error_closes_session_and_releases_quota() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider(error=RuntimeError("qwen unavailable"))

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]
            websocket.send_bytes(b"\x00\x01")
            websocket.receive_json()
            error = websocket.receive_json()
            timeline_update = websocket.receive_json()
            closed = websocket.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "qwen_asr_error"
    assert timeline_items_of_type(timeline_update, "exception") == [
        {
            "id": "exception-qwen_asr_error-0",
            "item_type": "exception",
            "timestamp_ms": 0,
            "text": "英文转写服务异常",
            "segment_id": None,
        },
    ]
    assert closed == {"type": "session_closed", "reason": "qwen_asr_error"}
    assert repository.sessions[session_id].status is MeetingSessionStatus.ERROR
    assert quota_service.released_session_ids == [session_id]
    assert stt_provider.closed is True


def test_usage_events_record_provider_error_without_error_message() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    usage_events = FakeUsageEventRecorder()
    stt_provider = FakeSttProvider(error=RuntimeError("qwen unavailable"))

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
        usage_event_recorder=usage_events,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            websocket.send_bytes(b"\x00\x01")
            receive_until_message_type(websocket, "error")
            receive_until_message_type(websocket, "session_closed")

    provider_errors = [
        record
        for record in usage_events.records
        if record.event_type is UsageEventType.PROVIDER_ERROR
    ]
    assert len(provider_errors) == 1
    assert provider_errors[0].session_id == uuid.UUID(str(started["session_id"]))
    assert provider_errors[0].payload == {
        "code": "qwen_asr_error",
        "error_type": "RuntimeError",
        "provider": "qwen_realtime_asr",
    }
    assert "qwen unavailable" not in json.dumps(provider_errors[0].payload)


def test_stopping_stt_session_closes_provider() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    stt_provider = FakeSttProvider()

    with make_client(
        repository=repository,
        quota_service=quota_service,
        stt_provider=stt_provider,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            websocket.send_bytes(b"\x00\x01")
            websocket.receive_json()
            websocket.send_json(
                {"type": "session_stop", "session_id": started["session_id"]},
            )
            receive_until_message_type(websocket, "session_closed")

    assert stt_provider.closed is True


def test_stopping_session_cancels_mock_provider_after_preserving_segments() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            segment_final = receive_until_message_type(websocket, "segment_final")
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            while True:
                message = websocket.receive_json()
                if message["type"] == "session_closed":
                    break

    assert segment_final["type"] == "segment_final"
    assert len(repository.transcript_segments) == 1
    assert repository.transcript_segments[0].segment_id == segment_final["segment_id"]
    assert repository.sessions[session_id].status is MeetingSessionStatus.ENDED


def test_browser_disconnect_can_resume_same_session_before_user_stop() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    resume_registry = InMemorySessionResumeRegistry()

    with make_client(
        repository=repository,
        quota_service=quota_service,
        resume_registry=resume_registry,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = str(started["session_id"])
            archive_token = str(started["archive_token"])
            websocket.send_bytes(b"\x00\x01")
            assert websocket.receive_json()["type"] == "audio_status"

        assert quota_service.released_session_ids == []
        assert repository.sessions[session_id].status is MeetingSessionStatus.ACTIVE

        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(
                session_resume_payload(
                    archive_token=archive_token,
                    client_id=client_id,
                    session_id=session_id,
                ),
            )
            resumed = websocket.receive_json()
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            closed = receive_until_message_type(websocket, "session_closed")

    assert resumed == {
        "type": "session_resumed",
        "session_id": session_id,
        "archive_url": started["archive_url"],
        "remaining_seconds_today": 2400,
    }
    assert closed == {"type": "session_closed", "reason": "user_stopped"}
    assert quota_service.released_session_ids == [session_id]
    assert repository.sessions[session_id].status is MeetingSessionStatus.ENDED


def test_rejects_session_resume_with_invalid_archive_token() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    resume_registry = InMemorySessionResumeRegistry()

    with make_client(
        repository=repository,
        quota_service=quota_service,
        resume_registry=resume_registry,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = str(started["session_id"])

        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(
                session_resume_payload(
                    archive_token="wrong-token",
                    client_id=client_id,
                    session_id=session_id,
                ),
            )
            error = websocket.receive_json()
            closed = websocket.receive_json()

    assert error == {
        "type": "error",
        "code": "session_resume_failed",
        "message": "Session cannot be resumed",
    }
    assert closed == {"type": "session_closed", "reason": "session_resume_failed"}


def test_rejects_duplicate_active_session() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService(
        denial_reason=QuotaDenialReason.ACTIVE_SESSION_LIMIT_REACHED,
    )

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            error = websocket.receive_json()
            closed = websocket.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "active_session_limit_reached"
    assert closed == {
        "type": "session_closed",
        "reason": "active_session_limit_reached",
    }
    assert repository.sessions == {}


@pytest.mark.parametrize(
    ("denial_reason", "remaining_seconds_today"),
    [
        (QuotaDenialReason.DAILY_QUOTA_EXHAUSTED, 0),
        (QuotaDenialReason.BUDGET_FUSE_TRIGGERED, 1200),
    ],
)
def test_rejects_quota_and_budget_denials_with_error_and_closed(
    denial_reason: QuotaDenialReason,
    remaining_seconds_today: int,
) -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService(
        denial_reason=denial_reason,
        remaining_seconds_today=remaining_seconds_today,
    )

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            error = websocket.receive_json()
            closed = websocket.receive_json()

    assert error["type"] == "error"
    assert error["code"] == denial_reason.value
    assert closed == {
        "type": "session_closed",
        "reason": denial_reason.value,
    }
    assert repository.sessions == {}


@pytest.mark.parametrize(
    ("denial_reason", "expected_event_type"),
    [
        (QuotaDenialReason.DAILY_QUOTA_EXHAUSTED, UsageEventType.QUOTA_EXHAUSTED),
        (QuotaDenialReason.BUDGET_FUSE_TRIGGERED, UsageEventType.BUDGET_FUSE_TRIGGERED),
    ],
)
def test_usage_events_record_quota_and_budget_denials(
    denial_reason: QuotaDenialReason,
    expected_event_type: UsageEventType,
) -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService(
        denial_reason=denial_reason,
        remaining_seconds_today=0,
    )
    usage_events = FakeUsageEventRecorder()

    with make_client(
        repository=repository,
        quota_service=quota_service,
        usage_event_recorder=usage_events,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            receive_until_message_type(websocket, "session_closed")

    assert usage_event_types(usage_events) == [
        UsageEventType.CAPTURE_STARTED,
        UsageEventType.QUOTA_CHECKED,
        expected_event_type,
    ]
    assert usage_events.records[1].payload == {
        "allowed": False,
        "remaining_seconds_today": 0,
        "reason": denial_reason.value,
    }
    assert usage_events.records[2].session_id is None


def test_rejects_uninitialized_client() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository()
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            error = websocket.receive_json()
            closed = websocket.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "client_not_initialized"
    assert closed == {
        "type": "session_closed",
        "reason": "client_not_initialized",
    }
    assert quota_service.reserved_session_ids == []


def test_invalid_message_closes_with_invalid_message_error() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("{not-json")
            error = websocket.receive_json()
            closed = websocket.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "invalid_message"
    assert closed == {"type": "session_closed", "reason": "invalid_message"}


def test_session_id_mismatch_closes_and_cleans_up() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            websocket.send_json(
                {"type": "session_stop", "session_id": str(uuid.uuid4())},
            )
            error = websocket.receive_json()
            closed = websocket.receive_json()

    session_id = started["session_id"]
    assert error["type"] == "error"
    assert error["code"] == "session_mismatch"
    assert closed == {"type": "session_closed", "reason": "session_mismatch"}
    assert quota_service.released_session_ids == [session_id]
