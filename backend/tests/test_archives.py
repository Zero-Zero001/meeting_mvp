from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from meeting_mvp_backend.archive_tokens import hash_archive_token
from meeting_mvp_backend.archives import (
    ArchiveAccessDenied,
    ArchiveExceptionTimelineRecord,
    ArchiveExportTimelineRecord,
    ArchiveKeySentenceUpdateRequest,
    ArchiveResponse,
    ArchiveSearchEventRequest,
    ArchiveSegmentCopiedEventRequest,
    ArchiveSegmentResponse,
    ArchiveService,
    ArchiveSessionRecord,
    ArchiveTimelineItemResponse,
    ArchiveTranscriptSegmentRecord,
)
from meeting_mvp_backend.config import get_settings
from meeting_mvp_backend.db.models import (
    CaptureMode,
    ExportFormat,
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
    export_timeline_records: list[ArchiveExportTimelineRecord] = field(
        default_factory=list,
    )
    exception_timeline_records: list[ArchiveExceptionTimelineRecord] = field(
        default_factory=list,
    )
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

    async def list_export_timeline_records(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveExportTimelineRecord]:
        return [
            record
            for record in self.export_timeline_records
            if record.session_id == session_id
        ]

    async def list_exception_timeline_records(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveExceptionTimelineRecord]:
        return [
            record
            for record in self.exception_timeline_records
            if record.session_id == session_id
        ]

    async def set_segment_key_sentence(
        self,
        *,
        session_id: uuid.UUID,
        segment_id: uuid.UUID,
        is_key_sentence: bool,
    ) -> ArchiveTranscriptSegmentRecord | None:
        for index, segment in enumerate(self.segments):
            if segment.session_id == session_id and segment.segment_id == segment_id:
                updated_segment = ArchiveTranscriptSegmentRecord(
                    chinese_text_final=segment.chinese_text_final,
                    end_ms=segment.end_ms,
                    english_text_final=segment.english_text_final,
                    is_key_sentence=is_key_sentence,
                    segment_id=segment.segment_id,
                    sequence=segment.sequence,
                    session_id=segment.session_id,
                    speaker_label=segment.speaker_label,
                    start_ms=segment.start_ms,
                    translation_retry_attempts=segment.translation_retry_attempts,
                    translation_retry_exhausted=segment.translation_retry_exhausted,
                    translation_status=segment.translation_status,
                )
                self.segments[index] = updated_segment
                return updated_segment
        return None


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
        self.event_calls: list[tuple[uuid.UUID, str, object]] = []
        self.key_sentence_calls: list[tuple[uuid.UUID, uuid.UUID, str, bool]] = []

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

    async def set_segment_key_sentence(
        self,
        *,
        session_id: uuid.UUID,
        segment_id: uuid.UUID,
        token: str,
        request: ArchiveKeySentenceUpdateRequest,
    ) -> ArchiveSegmentResponse:
        self.key_sentence_calls.append(
            (session_id, segment_id, token, request.is_key_sentence),
        )
        if self.error is not None:
            raise self.error
        return ArchiveSegmentResponse(
            chinese_text_final="中文 final 1",
            end_ms=3200,
            english_text_final="English final 1",
            is_key_sentence=request.is_key_sentence,
            segment_id=segment_id,
            sequence=1,
            speaker_label=None,
            start_ms=0,
            translation_status=TranslationStatus.COMPLETED,
        )

    async def record_archive_event(
        self,
        *,
        session_id: uuid.UUID,
        token: str,
        event: object,
    ) -> None:
        self.event_calls.append((session_id, token, event))
        if self.error is not None:
            raise self.error


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
    is_key_sentence: bool | None = None,
    translation_status: TranslationStatus = TranslationStatus.COMPLETED,
    translation_retry_attempts: int = 0,
    translation_retry_exhausted: bool = False,
) -> ArchiveTranscriptSegmentRecord:
    return ArchiveTranscriptSegmentRecord(
        segment_id=uuid.uuid4(),
        session_id=session_id,
        chinese_text_final=f"中文 final {sequence}",
        end_ms=sequence * 2000,
        english_text_final=f"English final {sequence}",
        is_key_sentence=sequence == 1 if is_key_sentence is None else is_key_sentence,
        sequence=sequence,
        speaker_label=None,
        start_ms=(sequence - 1) * 2000,
        translation_retry_attempts=translation_retry_attempts,
        translation_retry_exhausted=translation_retry_exhausted,
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
                translation_retry_attempts=3,
                translation_retry_exhausted=True,
                translation_status=TranslationStatus.FAILED,
            ),
        ],
        export_timeline_records=[
            ArchiveExportTimelineRecord(
                created_at=(session.started_at or FIXED_NOW) + timedelta(minutes=8),
                export_format=ExportFormat.MARKDOWN,
                export_id=uuid.UUID("44444444-4444-4444-8444-444444444444"),
                session_id=session.session_id,
            ),
        ],
        exception_timeline_records=[
            ArchiveExceptionTimelineRecord(
                code="qwen_final_translation_failed",
                created_at=(session.started_at or FIXED_NOW)
                + timedelta(seconds=20),
                event_id=uuid.UUID("99999999-9999-4999-8999-999999999999"),
                segment_id=None,
                session_id=session.session_id,
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
    assert archive.segments[2].translation_retry_attempts == 3
    assert archive.segments[2].translation_retry_exhausted is True
    assert [item.item_type for item in archive.timeline_items] == [
        "segment_final",
        "key_sentence",
        "segment_final",
        "segment_final",
        "exception",
        "export_created",
    ]
    assert archive.timeline_items[0].segment_id == archive.segments[0].segment_id
    assert archive.timeline_items[1].segment_id == archive.segments[0].segment_id
    assert archive.timeline_items[4].text == "中文正式翻译失败，已进入后台补译"
    assert archive.timeline_items[5].id == (
        "export-created-44444444-4444-4444-8444-444444444444"
    )
    assert archive.timeline_items[5].text == "已生成 Markdown 导出"
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
async def test_archive_service_records_search_event_with_safe_payload() -> None:
    session = make_archive_session()
    repository = FakeArchiveRepository(
        session=session,
        segments=[make_segment(session_id=session.session_id, sequence=1)],
    )
    usage_events = FakeUsageEventRecorder()
    service = ArchiveService(
        clock=lambda: FIXED_NOW,
        repository=repository,
        usage_event_recorder=usage_events,
    )

    await service.record_archive_event(
        session_id=session.session_id,
        token="archive-token",
        event=ArchiveSearchEventRequest(
            event_type="archive_searched",
            matched_segment_count=1,
            query_length=15,
            total_segment_count=2,
        ),
    )

    assert usage_events.records == [
        UsageEventRecord(
            client_id=session.client_id,
            created_at=FIXED_NOW,
            event_type=UsageEventType.ARCHIVE_SEARCHED,
            payload={
                "matched_segment_count": 1,
                "query_length": 15,
                "total_segment_count": 2,
            },
            session_id=session.session_id,
        ),
    ]
    assert "query" not in usage_events.records[0].payload
    assert "token" not in usage_events.records[0].payload


@pytest.mark.asyncio
async def test_archive_service_records_copy_event_with_metadata() -> None:
    session = make_archive_session()
    segment = make_segment(session_id=session.session_id, sequence=2)
    usage_events = FakeUsageEventRecorder()
    service = ArchiveService(
        clock=lambda: FIXED_NOW,
        repository=FakeArchiveRepository(session=session, segments=[segment]),
        usage_event_recorder=usage_events,
    )

    await service.record_archive_event(
        session_id=session.session_id,
        token="archive-token",
        event=ArchiveSegmentCopiedEventRequest(
            event_type="segment_copied",
            segment_id=segment.segment_id,
        ),
    )

    records = usage_events.records
    assert records == [
        UsageEventRecord(
            client_id=session.client_id,
            created_at=FIXED_NOW,
            event_type=UsageEventType.SEGMENT_COPIED,
            payload={
                "chinese_text_length": len(segment.chinese_text_final),
                "english_text_length": len(segment.english_text_final),
                "is_key_sentence": False,
                "segment_id": str(segment.segment_id),
                "sequence": 2,
                "translation_status": "completed",
            },
            session_id=session.session_id,
        ),
    ]
    assert "english_text_final" not in records[0].payload
    assert "chinese_text_final" not in records[0].payload
    assert "token" not in records[0].payload


@pytest.mark.asyncio
async def test_archive_service_updates_key_sentence_and_records_safe_event() -> None:
    session = make_archive_session()
    segment = make_segment(
        session_id=session.session_id,
        sequence=2,
        is_key_sentence=False,
    )
    usage_events = FakeUsageEventRecorder()
    service = ArchiveService(
        clock=lambda: FIXED_NOW,
        repository=FakeArchiveRepository(session=session, segments=[segment]),
        usage_event_recorder=usage_events,
    )

    updated_segment = await service.set_segment_key_sentence(
        session_id=session.session_id,
        segment_id=segment.segment_id,
        token="archive-token",
        request=ArchiveKeySentenceUpdateRequest(is_key_sentence=True),
    )

    assert updated_segment.is_key_sentence is True
    assert usage_events.records == [
        UsageEventRecord(
            client_id=session.client_id,
            created_at=FIXED_NOW,
            event_type=UsageEventType.KEY_SENTENCE_MARKED,
            payload={
                "chinese_text_length": len(segment.chinese_text_final),
                "english_text_length": len(segment.english_text_final),
                "is_key_sentence": True,
                "segment_id": str(segment.segment_id),
                "sequence": 2,
                "source": "archive_manual",
                "translation_status": "completed",
            },
            session_id=session.session_id,
        ),
    ]
    assert "english_text_final" not in usage_events.records[0].payload
    assert "chinese_text_final" not in usage_events.records[0].payload
    assert "token" not in usage_events.records[0].payload


@pytest.mark.asyncio
async def test_archive_service_rejects_key_sentence_update_outside_session() -> None:
    session = make_archive_session()
    usage_events = FakeUsageEventRecorder()
    service = ArchiveService(
        clock=lambda: FIXED_NOW,
        repository=FakeArchiveRepository(
            session=session,
            segments=[make_segment(session_id=uuid.uuid4(), sequence=1)],
        ),
        usage_event_recorder=usage_events,
    )

    with pytest.raises(ArchiveAccessDenied):
        await service.set_segment_key_sentence(
            session_id=session.session_id,
            segment_id=uuid.uuid4(),
            token="archive-token",
            request=ArchiveKeySentenceUpdateRequest(is_key_sentence=True),
        )

    assert usage_events.records == []


@pytest.mark.asyncio
async def test_archive_service_rejects_copy_event_for_segment_outside_session() -> None:
    session = make_archive_session()
    service = ArchiveService(
        clock=lambda: FIXED_NOW,
        repository=FakeArchiveRepository(
            session=session,
            segments=[make_segment(session_id=uuid.uuid4(), sequence=1)],
        ),
        usage_event_recorder=FakeUsageEventRecorder(),
    )

    with pytest.raises(ArchiveAccessDenied):
        await service.record_archive_event(
            session_id=session.session_id,
            token="archive-token",
            event=ArchiveSegmentCopiedEventRequest(
                event_type="segment_copied",
                segment_id=uuid.uuid4(),
            ),
        )


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
        timeline_items=[
            ArchiveTimelineItemResponse(
                id="segment-final-22222222-2222-4222-8222-222222222222",
                item_type="segment_final",
                segment_id=uuid.UUID("22222222-2222-4222-8222-222222222222"),
                text="中文 final 1",
                timestamp_ms=3200,
            ),
        ],
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
    assert http_response.json()["segments"][0]["translation_retry_attempts"] == 0
    assert (
        http_response.json()["segments"][0]["translation_retry_exhausted"] is False
    )
    assert http_response.json()["timeline_items"] == [
        {
            "id": "segment-final-22222222-2222-4222-8222-222222222222",
            "item_type": "segment_final",
            "timestamp_ms": 3200,
            "text": "中文 final 1",
            "segment_id": "22222222-2222-4222-8222-222222222222",
        },
    ]
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


@pytest.mark.asyncio
async def test_archive_event_endpoint_accepts_search_and_copy_events() -> None:
    service = FakeArchiveService(response=None)
    app.dependency_overrides[get_archive_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        search_response = await client.post(
            f"/api/archives/{session_id}/events?token=archive-token",
            json={
                "event_type": "archive_searched",
                "matched_segment_count": 1,
                "query_length": 15,
                "total_segment_count": 2,
            },
        )
        copy_response = await client.post(
            f"/api/archives/{session_id}/events?token=archive-token",
            json={
                "event_type": "segment_copied",
                "segment_id": str(uuid.UUID("22222222-2222-4222-8222-222222222222")),
            },
        )

    assert search_response.status_code == 204
    assert copy_response.status_code == 204
    assert service.event_calls[0][0:2] == (session_id, "archive-token")
    assert service.event_calls[1][0:2] == (session_id, "archive-token")


@pytest.mark.asyncio
async def test_archive_event_endpoint_rejects_missing_or_empty_token() -> None:
    service = FakeArchiveService(response=None)
    app.dependency_overrides[get_archive_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        missing_response = await client.post(
            f"/api/archives/{session_id}/events",
            json={
                "event_type": "archive_searched",
                "matched_segment_count": 0,
                "query_length": 5,
                "total_segment_count": 2,
            },
        )
        empty_response = await client.post(
            f"/api/archives/{session_id}/events?token=",
            json={
                "event_type": "archive_searched",
                "matched_segment_count": 0,
                "query_length": 5,
                "total_segment_count": 2,
            },
        )

    assert missing_response.status_code == 401
    assert empty_response.status_code == 401
    assert service.event_calls == []


@pytest.mark.asyncio
async def test_archive_event_endpoint_hides_denied_archive_as_404() -> None:
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
        response = await client.post(
            f"/api/archives/{session_id}/events?token=wrong-token",
            json={
                "event_type": "archive_searched",
                "matched_segment_count": 0,
                "query_length": 5,
                "total_segment_count": 2,
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_archive_key_sentence_endpoint_updates_segment() -> None:
    service = FakeArchiveService(response=None)
    app.dependency_overrides[get_archive_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()
    segment_id = uuid.UUID("22222222-2222-4222-8222-222222222222")

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.patch(
            f"/api/archives/{session_id}/segments/{segment_id}/key-sentence?token=archive-token",
            json={"is_key_sentence": True},
        )

    assert response.status_code == 200
    assert response.json()["segment_id"] == str(segment_id)
    assert response.json()["is_key_sentence"] is True
    assert service.key_sentence_calls == [
        (session_id, segment_id, "archive-token", True),
    ]


@pytest.mark.asyncio
async def test_archive_key_sentence_endpoint_rejects_missing_or_empty_token() -> None:
    service = FakeArchiveService(response=None)
    app.dependency_overrides[get_archive_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()
    segment_id = uuid.uuid4()

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        missing_response = await client.patch(
            f"/api/archives/{session_id}/segments/{segment_id}/key-sentence",
            json={"is_key_sentence": True},
        )
        empty_response = await client.patch(
            f"/api/archives/{session_id}/segments/{segment_id}/key-sentence?token=",
            json={"is_key_sentence": True},
        )

    assert missing_response.status_code == 401
    assert empty_response.status_code == 401
    assert service.key_sentence_calls == []


@pytest.mark.asyncio
async def test_archive_key_sentence_endpoint_hides_denied_archive_as_404() -> None:
    service = FakeArchiveService(
        response=None,
        error=ArchiveAccessDenied("archive not found or expired"),
    )
    app.dependency_overrides[get_archive_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()
    segment_id = uuid.uuid4()

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.patch(
            f"/api/archives/{session_id}/segments/{segment_id}/key-sentence?token=wrong-token",
            json={"is_key_sentence": True},
        )

    assert response.status_code == 404
