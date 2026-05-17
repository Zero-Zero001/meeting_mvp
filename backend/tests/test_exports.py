from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from meeting_mvp_backend.archive_tokens import hash_archive_token
from meeting_mvp_backend.archives import (
    ArchiveAccessDenied,
    ArchiveRepository,
    ArchiveSessionRecord,
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
from meeting_mvp_backend.exports import (
    ArchiveExportEmpty,
    ArchiveExportRequest,
    ArchiveExportResponse,
    ArchiveExportService,
    ArchiveExportUnavailable,
    ExportFileRecord,
    render_archive_json,
    render_archive_markdown,
)
from meeting_mvp_backend.main import app, get_archive_export_service
from meeting_mvp_backend.usage_events import UsageEventRecord, UsageEventType

FIXED_NOW = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)


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

    async def set_segment_key_sentence(
        self,
        *,
        session_id: uuid.UUID,
        segment_id: uuid.UUID,
        is_key_sentence: bool,
    ) -> ArchiveTranscriptSegmentRecord | None:
        for segment in self.segments:
            if segment.session_id == session_id and segment.segment_id == segment_id:
                return ArchiveTranscriptSegmentRecord(
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
        return None

    async def latest_session_closed_reason(
        self,
        session_id: uuid.UUID,
    ) -> str | None:
        return self.latest_close_reason


@dataclass
class UploadedObject:
    object_key: str
    content: bytes
    content_type: str


class FakeArchiveObjectStorage:
    def __init__(
        self,
        *,
        upload_error: Exception | None = None,
        sign_error: Exception | None = None,
    ) -> None:
        self.uploads: list[UploadedObject] = []
        self.upload_error = upload_error
        self.sign_error = sign_error

    async def upload_bytes(
        self,
        *,
        content: bytes,
        content_type: str,
        object_key: str,
    ) -> None:
        if self.upload_error is not None:
            raise self.upload_error
        self.uploads.append(
            UploadedObject(
                content=content,
                content_type=content_type,
                object_key=object_key,
            ),
        )

    async def create_signed_download_url(
        self,
        *,
        expires_in_seconds: int,
        object_key: str,
    ) -> str:
        if self.sign_error is not None:
            raise self.sign_error
        return (
            "https://cos.example.test/private-download?"
            f"key={object_key}&expires={expires_in_seconds}"
        )


class FakeExportFileRepository:
    def __init__(self) -> None:
        self.records: list[ExportFileRecord] = []

    async def create_export_file(
        self,
        *,
        cos_object_key: str,
        cos_url: str,
        created_at: datetime,
        export_id: uuid.UUID,
        export_format: ExportFormat,
        retention_expires_at: datetime,
        session_id: uuid.UUID,
    ) -> ExportFileRecord:
        record = ExportFileRecord(
            cos_object_key=cos_object_key,
            cos_url=cos_url,
            created_at=created_at,
            export_id=export_id,
            export_format=export_format,
            retention_expires_at=retention_expires_at,
            session_id=session_id,
        )
        self.records.append(record)
        return record


class FakeUsageEventRecorder:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.records: list[UsageEventRecord] = []

    async def record_event(
        self,
        *,
        client_id: str,
        event_type: UsageEventType | str,
        payload: dict[str, object] | None = None,
        session_id: uuid.UUID | str | None = None,
    ) -> UsageEventRecord:
        if self.fail:
            raise RuntimeError("usage event unavailable")
        record = UsageEventRecord(
            client_id=client_id,
            created_at=FIXED_NOW,
            event_type=UsageEventType(event_type),
            payload=payload or {},
            session_id=uuid.UUID(str(session_id)) if session_id is not None else None,
        )
        self.records.append(record)
        return record


class FakeArchiveExportService:
    def __init__(
        self,
        response: ArchiveExportResponse | None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[uuid.UUID, str, ArchiveExportRequest]] = []

    async def create_export(
        self,
        *,
        request: ArchiveExportRequest,
        session_id: uuid.UUID,
        token: str,
    ) -> ArchiveExportResponse:
        self.calls.append((session_id, token, request))
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
        status=MeetingSessionStatus.ENDED,
    )


def make_segment(
    *,
    chinese_text_final: str | None = None,
    session_id: uuid.UUID,
    sequence: int,
    translation_status: TranslationStatus = TranslationStatus.COMPLETED,
) -> ArchiveTranscriptSegmentRecord:
    return ArchiveTranscriptSegmentRecord(
        segment_id=uuid.uuid4(),
        session_id=session_id,
        chinese_text_final=(
            chinese_text_final
            if chinese_text_final is not None
            else f"中文 final {sequence}"
        ),
        end_ms=sequence * 2000,
        english_text_final=f"English final {sequence}",
        is_key_sentence=sequence == 1,
        sequence=sequence,
        speaker_label=None,
        start_ms=(sequence - 1) * 2000,
        translation_status=translation_status,
    )


def make_export_service(
    *,
    archive_repository: ArchiveRepository,
    export_repository: FakeExportFileRepository | None = None,
    storage: FakeArchiveObjectStorage | None = None,
    usage_event_recorder: FakeUsageEventRecorder | None = None,
) -> ArchiveExportService:
    return ArchiveExportService(
        archive_repository=archive_repository,
        clock=lambda: FIXED_NOW,
        export_prefix="exports/",
        export_repository=export_repository or FakeExportFileRepository(),
        signed_url_ttl_seconds=3600,
        storage=storage or FakeArchiveObjectStorage(),
        usage_event_recorder=usage_event_recorder,
    )


def test_render_archive_markdown_contains_session_and_ordered_bilingual_segments() -> (
    None
):
    session = make_archive_session()
    segments = [
        make_segment(session_id=session.session_id, sequence=2),
        make_segment(
            chinese_text_final="",
            session_id=session.session_id,
            sequence=1,
            translation_status=TranslationStatus.FAILED,
        ),
    ]

    markdown = render_archive_markdown(
        end_reason="user_stopped",
        exported_at=FIXED_NOW,
        segments=segments,
        session=session,
    )

    assert "# 会议归档" in markdown
    assert f"会话 ID：{session.session_id}" in markdown
    assert "结束原因：user_stopped" in markdown
    assert markdown.index("English final 1") < markdown.index("English final 2")
    assert "中文 final 暂不可用" in markdown
    assert "0:00 - 0:02" in markdown


def test_render_archive_json_contains_session_and_ordered_segments() -> None:
    session = make_archive_session()
    segments = [
        make_segment(session_id=session.session_id, sequence=2),
        make_segment(session_id=session.session_id, sequence=1),
    ]

    payload = json.loads(
        render_archive_json(
            end_reason="user_stopped",
            exported_at=FIXED_NOW,
            segments=segments,
            session=session,
        ),
    )

    assert payload["session"]["session_id"] == str(session.session_id)
    assert payload["session"]["end_reason"] == "user_stopped"
    assert payload["exported_at"] == "2026-05-16T12:00:00+00:00"
    assert [segment["sequence"] for segment in payload["segments"]] == [1, 2]
    assert payload["segments"][0]["english_text_final"] == "English final 1"


@pytest.mark.asyncio
async def test_export_service_uploads_markdown_writes_record_and_event() -> None:
    session = make_archive_session()
    segments = [make_segment(session_id=session.session_id, sequence=1)]
    export_repository = FakeExportFileRepository()
    storage = FakeArchiveObjectStorage()
    usage_events = FakeUsageEventRecorder()
    service = make_export_service(
        archive_repository=FakeArchiveRepository(session=session, segments=segments),
        export_repository=export_repository,
        storage=storage,
        usage_event_recorder=usage_events,
    )

    response = await service.create_export(
        request=ArchiveExportRequest(format=ExportFormat.MARKDOWN),
        session_id=session.session_id,
        token="archive-token",
    )

    expected_key = f"exports/{session.session_id}/{response.export_id}.md"
    assert response.session_id == session.session_id
    assert response.format is ExportFormat.MARKDOWN
    assert response.download_url.startswith("https://cos.example.test/")
    assert response.download_url_expires_at == FIXED_NOW + timedelta(seconds=3600)
    assert response.retention_expires_at == session.retention_expires_at
    assert storage.uploads[0].object_key == expected_key
    assert storage.uploads[0].content_type == "text/markdown; charset=utf-8"
    assert b"English final 1" in storage.uploads[0].content
    assert export_repository.records == [
        ExportFileRecord(
            cos_object_key=expected_key,
            cos_url=response.download_url,
            created_at=FIXED_NOW,
            export_id=response.export_id,
            export_format=ExportFormat.MARKDOWN,
            retention_expires_at=session.retention_expires_at,
            session_id=session.session_id,
        ),
    ]
    assert usage_events.records == [
        UsageEventRecord(
            client_id=session.client_id,
            created_at=FIXED_NOW,
            event_type=UsageEventType.EXPORT_CREATED,
            payload={
                "file_size_bytes": len(storage.uploads[0].content),
                "format": "markdown",
                "segment_count": 1,
                "signed_url_ttl_seconds": 3600,
                "translation_failed_count": 0,
            },
            session_id=session.session_id,
        ),
    ]
    assert "download_url" not in usage_events.records[0].payload
    assert "object_key" not in usage_events.records[0].payload


@pytest.mark.asyncio
async def test_export_service_uploads_json_with_safe_shape() -> None:
    session = make_archive_session()
    storage = FakeArchiveObjectStorage()
    service = make_export_service(
        archive_repository=FakeArchiveRepository(
            session=session,
            segments=[make_segment(session_id=session.session_id, sequence=1)],
        ),
        storage=storage,
    )

    response = await service.create_export(
        request=ArchiveExportRequest(format=ExportFormat.JSON),
        session_id=session.session_id,
        token="archive-token",
    )

    assert response.format is ExportFormat.JSON
    assert storage.uploads[0].object_key.endswith(".json")
    assert storage.uploads[0].content_type == "application/json; charset=utf-8"
    payload = json.loads(storage.uploads[0].content)
    assert payload["segments"][0]["chinese_text_final"] == "中文 final 1"


@pytest.mark.asyncio
async def test_export_service_rejects_empty_archive_and_records_failed_event() -> None:
    session = make_archive_session()
    storage = FakeArchiveObjectStorage()
    export_repository = FakeExportFileRepository()
    usage_events = FakeUsageEventRecorder()
    service = make_export_service(
        archive_repository=FakeArchiveRepository(session=session, segments=[]),
        export_repository=export_repository,
        storage=storage,
        usage_event_recorder=usage_events,
    )

    with pytest.raises(ArchiveExportEmpty):
        await service.create_export(
            request=ArchiveExportRequest(format=ExportFormat.JSON),
            session_id=session.session_id,
            token="archive-token",
        )

    assert storage.uploads == []
    assert export_repository.records == []
    assert usage_events.records[0].event_type is UsageEventType.EXPORT_FAILED
    assert usage_events.records[0].payload == {
        "error_type": "ArchiveExportEmpty",
        "format": "json",
        "segment_count": 0,
        "stage": "empty_archive",
    }


@pytest.mark.asyncio
async def test_export_service_records_failed_event_when_cos_upload_fails() -> None:
    session = make_archive_session()
    export_repository = FakeExportFileRepository()
    usage_events = FakeUsageEventRecorder()
    service = make_export_service(
        archive_repository=FakeArchiveRepository(
            session=session,
            segments=[make_segment(session_id=session.session_id, sequence=1)],
        ),
        export_repository=export_repository,
        storage=FakeArchiveObjectStorage(upload_error=RuntimeError("cos down")),
        usage_event_recorder=usage_events,
    )

    with pytest.raises(ArchiveExportUnavailable):
        await service.create_export(
            request=ArchiveExportRequest(format=ExportFormat.MARKDOWN),
            session_id=session.session_id,
            token="archive-token",
        )

    assert export_repository.records == []
    assert usage_events.records[0].event_type is UsageEventType.EXPORT_FAILED
    assert usage_events.records[0].payload == {
        "error_type": "RuntimeError",
        "format": "markdown",
        "segment_count": 1,
        "stage": "cos_upload",
    }


@pytest.mark.asyncio
async def test_export_service_ignores_usage_event_write_failure_on_success() -> None:
    session = make_archive_session()
    service = make_export_service(
        archive_repository=FakeArchiveRepository(
            session=session,
            segments=[make_segment(session_id=session.session_id, sequence=1)],
        ),
        usage_event_recorder=FakeUsageEventRecorder(fail=True),
    )

    response = await service.create_export(
        request=ArchiveExportRequest(format=ExportFormat.MARKDOWN),
        session_id=session.session_id,
        token="archive-token",
    )

    assert response.session_id == session.session_id


@pytest.mark.asyncio
async def test_export_service_reuses_archive_authorization() -> None:
    session = make_archive_session(archive_token="correct-token")
    service = make_export_service(
        archive_repository=FakeArchiveRepository(
            session=session,
            segments=[make_segment(session_id=session.session_id, sequence=1)],
        ),
    )

    with pytest.raises(ArchiveAccessDenied):
        await service.create_export(
            request=ArchiveExportRequest(format=ExportFormat.MARKDOWN),
            session_id=session.session_id,
            token="wrong-token",
        )


@pytest.mark.asyncio
async def test_archive_export_endpoint_returns_created_response() -> None:
    session = make_archive_session()
    response = ArchiveExportResponse(
        created_at=FIXED_NOW,
        download_url="https://cos.example.test/private-download",
        download_url_expires_at=FIXED_NOW + timedelta(hours=1),
        export_id=uuid.uuid4(),
        format=ExportFormat.JSON,
        retention_expires_at=session.retention_expires_at,
        session_id=session.session_id,
    )
    service = FakeArchiveExportService(response=response)
    app.dependency_overrides[get_archive_export_service] = lambda: service
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        http_response = await client.post(
            f"/api/archives/{session.session_id}/exports?token=archive-token",
            json={"format": "json"},
        )

    assert http_response.status_code == 201
    assert http_response.json()["format"] == "json"
    assert http_response.json()["download_url"] == response.download_url
    assert "cos_object_key" not in http_response.json()
    assert service.calls[0][0:2] == (session.session_id, "archive-token")
    assert service.calls[0][2].format is ExportFormat.JSON


@pytest.mark.asyncio
async def test_archive_export_endpoint_rejects_missing_or_empty_token() -> None:
    service = FakeArchiveExportService(response=None)
    app.dependency_overrides[get_archive_export_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        missing_response = await client.post(
            f"/api/archives/{session_id}/exports",
            json={"format": "markdown"},
        )
        empty_response = await client.post(
            f"/api/archives/{session_id}/exports?token=",
            json={"format": "markdown"},
        )

    assert missing_response.status_code == 401
    assert empty_response.status_code == 401
    assert service.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ArchiveAccessDenied("archive not found or expired"), 404),
        (ArchiveExportEmpty("archive has no exportable final segments"), 409),
        (ArchiveExportUnavailable("export temporarily unavailable"), 503),
    ],
)
async def test_archive_export_endpoint_maps_export_errors(
    error: Exception,
    expected_status: int,
) -> None:
    service = FakeArchiveExportService(response=None, error=error)
    app.dependency_overrides[get_archive_export_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            f"/api/archives/{session_id}/exports?token=archive-token",
            json={"format": "markdown"},
        )

    assert response.status_code == expected_status


@pytest.mark.asyncio
async def test_archive_export_endpoint_rejects_unknown_format() -> None:
    service = FakeArchiveExportService(response=None)
    app.dependency_overrides[get_archive_export_service] = lambda: service
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4()

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            f"/api/archives/{session_id}/exports?token=archive-token",
            json={"format": "pdf"},
        )

    assert response.status_code == 422
    assert service.calls == []
