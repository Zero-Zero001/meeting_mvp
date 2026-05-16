from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from meeting_mvp_backend.archive_tokens import hash_archive_token
from meeting_mvp_backend.archives import (
    ArchiveAccessDenied,
    ArchiveResponse,
    ArchiveSegmentResponse,
    ArchiveService,
    ArchiveSessionRecord,
    ArchiveTranscriptSegmentRecord,
)
from meeting_mvp_backend.config import get_settings
from meeting_mvp_backend.db.models import (
    CaptureMode,
    MeetingSessionStatus,
    SourcePlatform,
    TranslationStatus,
)
from meeting_mvp_backend.main import app, get_archive_service
from meeting_mvp_backend.usage_events import UsageEventRecord, UsageEventType

FIXED_NOW = datetime(2026, 5, 16, 10, 0, tzinfo=UTC)


@dataclass
class FakeArchiveRepository:
    session: ArchiveSessionRecord | None
    segments: list[ArchiveTranscriptSegmentRecord]
    latest_close_reason: str | None = None

    async def get_session(
        self,
        session_id: uuid.UUID,
    ) -> ArchiveSessionRecord | None:
        if self.session is None or self.session.session_id != session_id:
            return None
        return self.session

    async def list_segments(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveTranscriptSegmentRecord]:
        return [
            segment for segment in self.segments if segment.session_id == session_id
        ]

    async def latest_session_closed_reason(
        self,
        session_id: uuid.UUID,
    ) -> str | None:
        return self.latest_close_reason


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
            created_at=FIXED_NOW,
            event_type=UsageEventType(event_type),
            payload=payload or {},
            session_id=uuid.UUID(str(session_id)) if session_id is not None else None,
        )
        self.records.append(record)
        return record


class FakeArchiveService:
    def __init__(
        self,
        response: ArchiveResponse | None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[uuid.UUID, str]] = []

    async def view_archive(
        self,
        *,
        session_id: uuid.UUID,
        token: str,
    ) -> ArchiveResponse:
        self.calls.append((session_id, token))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


@pytest.fixture(autouse=True)
async def reset_dependency_overrides() -> AsyncIterator[None]:
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def make_archive_session(
    *,
    archive_token: str = "archive-token",
    session_id: uuid.UUID | None = None,
    status: MeetingSessionStatus = MeetingSessionStatus.ENDED,
    retention_expires_at: datetime | None = None,
) -> ArchiveSessionRecord:
    return ArchiveSessionRecord(
        session_id=session_id or uuid.uuid4(),
        archive_token_hash=hash_archive_token(archive_token),
        capture_mode=CaptureMode.TAB_AUDIO,
        client_id="11111111-1111-4111-8111-111111111111",
        duration_seconds=420,
        ended_at=FIXED_NOW,
        quota_seconds_consumed=420,
        retention_expires_at=retention_expires_at
        or FIXED_NOW
        + timedelta(days=30),
        source_platform=SourcePlatform.GOOGLE_MEET,
        started_at=FIXED_NOW - timedelta(minutes=7),
        status=status,
    )


def make_segment(
    *,
    session_id: uuid.UUID,
    sequence: int,
    translation_status: TranslationStatus = TranslationStatus.COMPLETED,
) -> ArchiveTranscriptSegmentRecord:
    return ArchiveTranscriptSegmentRecord(
        segment_id=uuid.uuid4(),
        session_id=session_id,
        chinese_text_final=f"中文 final {sequence}",
        end_ms=sequence * 2000,
        english_text_final=f"English final {sequence}",
        is_key_sentence=sequence == 1,
        sequence=sequence,
        speaker_label=None,
        start_ms=(sequence - 1) * 2000,
        translation_status=translation_status,
    )


@pytest.mark.asyncio
async def test_archive_service_returns_ordered_segments_and_view_event() -> None:
    archive_token = "archive-token"
    session = make_archive_session(archive_token=archive_token)
    repository = FakeArchiveRepository(
        session=session,
        segments=[
            make_segment(session_id=session.session_id, sequence=2),
            make_segment(session_id=session.session_id, sequence=1),
            make_segment(
                session_id=session.session_id,
                sequence=3,
                translation_status=TranslationStatus.FAILED,
            ),
        ],
        latest_close_reason="user_stopped",
    )
    usage_events = FakeUsageEventRecorder()
    service = ArchiveService(
        clock=lambda: FIXED_NOW,
        repository=repository,
        usage_event_recorder=usage_events,
    )

    archive = await service.view_archive(
        session_id=session.session_id,
        token=archive_token,
    )

    assert archive.session_id == session.session_id
    assert archive.end_reason == "user_stopped"
    assert archive.status == MeetingSessionStatus.ENDED
    assert [segment.sequence for segment in archive.segments] == [1, 2, 3]
    assert archive.segments[0].english_text_final == "English final 1"
    assert archive.segments[2].translation_status == TranslationStatus.FAILED
    assert usage_events.records == [
        UsageEventRecord(
            client_id=session.client_id,
            created_at=FIXED_NOW,
            event_type=UsageEventType.ARCHIVE_VIEWED,
            payload={
                "end_reason": "user_stopped",
                "segment_count": 3,
                "session_status": "ended",
                "translation_failed_count": 1,
            },
            session_id=session.session_id,
        ),
    ]


@pytest.mark.asyncio
async def test_archive_service_rejects_wrong_token_without_recording_event() -> None:
    session = make_archive_session(archive_token="correct-token")
    usage_events = FakeUsageEventRecorder()
    service = ArchiveService(
        clock=lambda: FIXED_NOW,
        repository=FakeArchiveRepository(session=session, segments=[]),
        usage_event_recorder=usage_events,
    )

    with pytest.raises(ArchiveAccessDenied):
        await service.view_archive(
            session_id=session.session_id,
            token="wrong-token",
        )

    assert usage_events.records == []


@pytest.mark.asyncio
async def test_archive_service_rejects_expired_archive() -> None:
    session = make_archive_session(
        retention_expires_at=FIXED_NOW - timedelta(seconds=1),
    )
    service = ArchiveService(
        clock=lambda: FIXED_NOW,
        repository=FakeArchiveRepository(session=session, segments=[]),
        usage_event_recorder=None,
    )

    with pytest.raises(ArchiveAccessDenied):
        await service.view_archive(
            session_id=session.session_id,
            token="archive-token",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "latest_close_reason", "expected_end_reason"),
    [
        (MeetingSessionStatus.ENDED, None, "ended"),
        (MeetingSessionStatus.QUOTA_STOPPED, None, "quota_stopped"),
        (MeetingSessionStatus.ERROR, "qwen_asr_error", "qwen_asr_error"),
        (MeetingSessionStatus.ERROR, "browser_disconnected", "browser_disconnected"),
    ],
)
async def test_archive_service_derives_end_reason(
    status: MeetingSessionStatus,
    latest_close_reason: str | None,
    expected_end_reason: str,
) -> None:
    session = make_archive_session(status=status)
    service = ArchiveService(
        clock=lambda: FIXED_NOW,
        repository=FakeArchiveRepository(
            session=session,
            segments=[],
            latest_close_reason=latest_close_reason,
        ),
        usage_event_recorder=None,
    )

    archive = await service.view_archive(
        session_id=session.session_id,
        token="archive-token",
    )

    assert archive.end_reason == expected_end_reason


@pytest.mark.asyncio
async def test_archive_endpoint_returns_archive_response() -> None:
    session = make_archive_session()
    response = ArchiveResponse(
        capture_mode=session.capture_mode,
        duration_seconds=session.duration_seconds,
        end_reason="user_stopped",
        ended_at=session.ended_at,
        quota_seconds_consumed=session.quota_seconds_consumed,
        retention_expires_at=session.retention_expires_at,
        segments=[
            ArchiveSegmentResponse.model_validate(
                make_segment(session_id=session.session_id, sequence=1),
            ),
        ],
        session_id=session.session_id,
        source_platform=session.source_platform,
        started_at=session.started_at,
        status=session.status,
    )
    service = FakeArchiveService(response=response)
    app.dependency_overrides[get_archive_service] = lambda: service
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        http_response = await client.get(
            f"/api/archives/{session.session_id}?token=archive-token",
        )

    assert http_response.status_code == 200
    assert http_response.json()["session_id"] == str(session.session_id)
    assert http_response.json()["segments"][0]["english_text_final"] == (
        "English final 1"
    )
    assert service.calls == [(session.session_id, "archive-token")]


@pytest.mark.asyncio
async def test_archive_endpoint_rejects_missing_or_empty_token() -> None:
    service = FakeArchiveService(response=None)
    app.dependency_overrides[get_archive_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        missing_response = await client.get(f"/api/archives/{session_id}")
        empty_response = await client.get(f"/api/archives/{session_id}?token=")

    assert missing_response.status_code == 401
    assert empty_response.status_code == 401
    assert service.calls == []


@pytest.mark.asyncio
async def test_archive_endpoint_hides_wrong_token_and_missing_session_as_404() -> None:
    service = FakeArchiveService(
        response=None,
        error=ArchiveAccessDenied("archive not found or expired"),
    )
    app.dependency_overrides[get_archive_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            f"/api/archives/{session_id}?token=wrong-token",
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Archive not found or expired"}
