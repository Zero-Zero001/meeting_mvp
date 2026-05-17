from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from meeting_mvp_backend.archive_tokens import hash_archive_token
from meeting_mvp_backend.db.models import (
    CaptureMode,
    ExportFile,
    ExportFormat,
    MeetingSession,
    MeetingSessionStatus,
    SourcePlatform,
    TranscriptSegment,
    TranslationStatus,
    UsageEvent,
)
from meeting_mvp_backend.timeline import (
    TimelineItemType,
    build_archive_exception_timeline_item,
    build_export_created_timeline_item,
    build_key_sentence_timeline_item,
    build_segment_final_timeline_item,
    relative_timestamp_ms,
    sort_timeline_items,
)
from meeting_mvp_backend.usage_events import (
    UsageEventRecorder,
    UsageEventType,
    record_usage_event_best_effort,
)

Clock = Callable[[], datetime]


class ArchiveAccessDenied(Exception):
    """Raised when an archive cannot be safely returned to the requester."""


@dataclass(frozen=True, slots=True)
class ArchiveSessionRecord:
    session_id: uuid.UUID
    client_id: str
    archive_token_hash: str
    source_platform: SourcePlatform
    capture_mode: CaptureMode
    status: MeetingSessionStatus
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int
    quota_seconds_consumed: int
    retention_expires_at: datetime


@dataclass(frozen=True, slots=True)
class ArchiveTranscriptSegmentRecord:
    segment_id: uuid.UUID
    session_id: uuid.UUID
    sequence: int
    start_ms: int
    end_ms: int
    speaker_label: str | None
    english_text_final: str
    chinese_text_final: str
    translation_status: TranslationStatus
    is_key_sentence: bool
    translation_retry_attempts: int = 0
    translation_retry_exhausted: bool = False


@dataclass(frozen=True, slots=True)
class ArchiveExportTimelineRecord:
    export_id: uuid.UUID
    session_id: uuid.UUID
    export_format: ExportFormat
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ArchiveExceptionTimelineRecord:
    event_id: uuid.UUID
    session_id: uuid.UUID
    code: str
    created_at: datetime
    segment_id: uuid.UUID | None = None


class ArchiveSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    segment_id: uuid.UUID
    sequence: int
    start_ms: int
    end_ms: int
    speaker_label: str | None
    english_text_final: str
    chinese_text_final: str
    translation_status: TranslationStatus
    is_key_sentence: bool
    translation_retry_attempts: int = 0
    translation_retry_exhausted: bool = False


class ArchiveTimelineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_type: TimelineItemType
    timestamp_ms: int = Field(ge=0)
    text: str
    segment_id: uuid.UUID | None = None


class ArchiveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    source_platform: SourcePlatform
    capture_mode: CaptureMode
    status: MeetingSessionStatus
    end_reason: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int
    quota_seconds_consumed: int
    retention_expires_at: datetime
    segments: list[ArchiveSegmentResponse]
    timeline_items: list[ArchiveTimelineItemResponse] = Field(default_factory=list)


class ArchiveSearchEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: Literal["archive_searched"]
    query_length: int = Field(ge=1)
    matched_segment_count: int = Field(ge=0)
    total_segment_count: int = Field(ge=0)


class ArchiveSegmentCopiedEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: Literal["segment_copied"]
    segment_id: uuid.UUID


class ArchiveKeySentenceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_key_sentence: bool


type ArchiveEventRequest = Annotated[
    ArchiveSearchEventRequest | ArchiveSegmentCopiedEventRequest,
    Field(discriminator="event_type"),
]


class ArchiveRepository(Protocol):
    async def get_session(
        self,
        session_id: uuid.UUID,
    ) -> ArchiveSessionRecord | None: ...

    async def list_segments(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveTranscriptSegmentRecord]: ...

    async def list_export_timeline_records(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveExportTimelineRecord]: ...

    async def list_exception_timeline_records(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveExceptionTimelineRecord]: ...

    async def set_segment_key_sentence(
        self,
        *,
        session_id: uuid.UUID,
        segment_id: uuid.UUID,
        is_key_sentence: bool,
    ) -> ArchiveTranscriptSegmentRecord | None: ...

    async def latest_session_closed_reason(
        self,
        session_id: uuid.UUID,
    ) -> str | None: ...


class SQLAlchemyArchiveRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_session(
        self,
        session_id: uuid.UUID,
    ) -> ArchiveSessionRecord | None:
        async with self._session_factory() as session:
            model = await session.scalar(
                select(MeetingSession).where(MeetingSession.id == session_id),
            )
        if model is None:
            return None
        return ArchiveSessionRecord(
            archive_token_hash=model.archive_token_hash,
            capture_mode=model.capture_mode,
            client_id=model.client_id,
            duration_seconds=model.duration_seconds,
            ended_at=model.ended_at,
            quota_seconds_consumed=model.quota_seconds_consumed,
            retention_expires_at=model.retention_expires_at,
            session_id=model.id,
            source_platform=model.source_platform,
            started_at=model.started_at,
            status=model.status,
        )

    async def list_segments(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveTranscriptSegmentRecord]:
        async with self._session_factory() as session:
            result = await session.scalars(
                select(TranscriptSegment)
                .where(TranscriptSegment.session_id == session_id)
                .order_by(TranscriptSegment.sequence),
            )
            models = list(result)
            retry_metadata = await _translation_retry_metadata_by_segment_id(
                session=session,
                session_id=session_id,
            )
        return [
            _archive_segment_record_from_model(
                model,
                retry_metadata=retry_metadata.get(model.id, (0, False)),
            )
            for model in models
        ]

    async def list_export_timeline_records(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveExportTimelineRecord]:
        async with self._session_factory() as session:
            result = await session.scalars(
                select(ExportFile)
                .where(ExportFile.session_id == session_id)
                .order_by(ExportFile.created_at),
            )
            models = list(result)
        return [
            ArchiveExportTimelineRecord(
                created_at=model.created_at,
                export_format=model.format,
                export_id=model.id,
                session_id=model.session_id,
            )
            for model in models
        ]

    async def list_exception_timeline_records(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveExceptionTimelineRecord]:
        async with self._session_factory() as session:
            result = await session.scalars(
                select(UsageEvent)
                .where(
                    UsageEvent.session_id == session_id,
                    UsageEvent.event_type.in_(
                        [
                            UsageEventType.BUDGET_FUSE_TRIGGERED.value,
                            UsageEventType.EXPORT_FAILED.value,
                            UsageEventType.PROVIDER_ERROR.value,
                            UsageEventType.QUOTA_EXHAUSTED.value,
                        ],
                    ),
                )
                .order_by(UsageEvent.created_at),
            )
            models = list(result)
        return [
            record
            for model in models
            if (
                record := _archive_exception_timeline_record_from_usage_event(model)
            )
            is not None
        ]

    async def set_segment_key_sentence(
        self,
        *,
        session_id: uuid.UUID,
        segment_id: uuid.UUID,
        is_key_sentence: bool,
    ) -> ArchiveTranscriptSegmentRecord | None:
        async with self._session_factory() as session:
            model = await session.scalar(
                select(TranscriptSegment).where(
                    TranscriptSegment.id == segment_id,
                    TranscriptSegment.session_id == session_id,
                ),
            )
            if model is None:
                return None
            model.is_key_sentence = is_key_sentence
            retry_metadata = await _translation_retry_metadata_by_segment_id(
                session=session,
                session_id=session_id,
            )
            record = _archive_segment_record_from_model(
                model,
                retry_metadata=retry_metadata.get(model.id, (0, False)),
            )
            await session.commit()
            return record

    async def latest_session_closed_reason(
        self,
        session_id: uuid.UUID,
    ) -> str | None:
        async with self._session_factory() as session:
            payload = await session.scalar(
                select(UsageEvent.payload)
                .where(
                    UsageEvent.session_id == session_id,
                    UsageEvent.event_type == UsageEventType.SESSION_CLOSED.value,
                )
                .order_by(desc(UsageEvent.created_at))
                .limit(1),
            )
        if not isinstance(payload, dict):
            return None
        reason = cast(object, payload.get("reason"))
        if isinstance(reason, str) and reason.strip() != "":
            return reason
        return None


class ArchiveService:
    def __init__(
        self,
        *,
        repository: ArchiveRepository,
        clock: Clock | None = None,
        usage_event_recorder: UsageEventRecorder | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or _now_utc
        self._usage_event_recorder = usage_event_recorder

    async def view_archive(
        self,
        *,
        session_id: uuid.UUID,
        token: str,
    ) -> ArchiveResponse:
        session = await self._authorize_session(session_id=session_id, token=token)
        segments = sorted(
            await self._repository.list_segments(session_id),
            key=lambda segment: segment.sequence,
        )
        end_reason = (
            await self._repository.latest_session_closed_reason(session_id)
        ) or session.status.value
        export_timeline_records = (
            await self._repository.list_export_timeline_records(session_id)
        )
        exception_timeline_records = (
            await self._repository.list_exception_timeline_records(session_id)
        )
        archive = ArchiveResponse(
            capture_mode=session.capture_mode,
            duration_seconds=session.duration_seconds,
            end_reason=end_reason,
            ended_at=session.ended_at,
            quota_seconds_consumed=session.quota_seconds_consumed,
            retention_expires_at=session.retention_expires_at,
            segments=[
                ArchiveSegmentResponse(
                    chinese_text_final=segment.chinese_text_final,
                    end_ms=segment.end_ms,
                    english_text_final=segment.english_text_final,
                    is_key_sentence=segment.is_key_sentence,
                    segment_id=segment.segment_id,
                    sequence=segment.sequence,
                    speaker_label=segment.speaker_label,
                    start_ms=segment.start_ms,
                    translation_retry_attempts=segment.translation_retry_attempts,
                    translation_retry_exhausted=segment.translation_retry_exhausted,
                    translation_status=segment.translation_status,
                )
                for segment in segments
            ],
            session_id=session.session_id,
            source_platform=session.source_platform,
            started_at=session.started_at,
            status=session.status,
            timeline_items=_archive_timeline_items(
                exception_records=exception_timeline_records,
                export_records=export_timeline_records,
                segments=segments,
                session=session,
            ),
        )
        await record_usage_event_best_effort(
            recorder=self._usage_event_recorder,
            client_id=session.client_id,
            session_id=session.session_id,
            event_type=UsageEventType.ARCHIVE_VIEWED,
            payload={
                "end_reason": end_reason,
                "segment_count": len(segments),
                "session_status": session.status.value,
                "translation_failed_count": sum(
                    1
                    for segment in segments
                    if segment.translation_status is TranslationStatus.FAILED
                ),
            },
        )
        return archive

    async def record_archive_event(
        self,
        *,
        session_id: uuid.UUID,
        token: str,
        event: ArchiveEventRequest,
    ) -> None:
        session = await self._authorize_session(session_id=session_id, token=token)
        if isinstance(event, ArchiveSearchEventRequest):
            await record_usage_event_best_effort(
                recorder=self._usage_event_recorder,
                client_id=session.client_id,
                session_id=session.session_id,
                event_type=UsageEventType.ARCHIVE_SEARCHED,
                payload={
                    "matched_segment_count": event.matched_segment_count,
                    "query_length": event.query_length,
                    "total_segment_count": event.total_segment_count,
                },
            )
            return

        segment = await self._find_segment(
            session_id=session.session_id,
            segment_id=event.segment_id,
        )
        if segment is None:
            raise ArchiveAccessDenied("archive not found or expired")
        await record_usage_event_best_effort(
            recorder=self._usage_event_recorder,
            client_id=session.client_id,
            session_id=session.session_id,
            event_type=UsageEventType.SEGMENT_COPIED,
            payload={
                "chinese_text_length": len(segment.chinese_text_final),
                "english_text_length": len(segment.english_text_final),
                "is_key_sentence": segment.is_key_sentence,
                "segment_id": str(segment.segment_id),
                "sequence": segment.sequence,
                "translation_status": segment.translation_status.value,
            },
        )

    async def set_segment_key_sentence(
        self,
        *,
        session_id: uuid.UUID,
        segment_id: uuid.UUID,
        token: str,
        request: ArchiveKeySentenceUpdateRequest,
    ) -> ArchiveSegmentResponse:
        session = await self._authorize_session(session_id=session_id, token=token)
        segment = await self._repository.set_segment_key_sentence(
            session_id=session.session_id,
            segment_id=segment_id,
            is_key_sentence=request.is_key_sentence,
        )
        if segment is None:
            raise ArchiveAccessDenied("archive not found or expired")

        await record_usage_event_best_effort(
            recorder=self._usage_event_recorder,
            client_id=session.client_id,
            session_id=session.session_id,
            event_type=UsageEventType.KEY_SENTENCE_MARKED,
            payload={
                "chinese_text_length": len(segment.chinese_text_final),
                "english_text_length": len(segment.english_text_final),
                "is_key_sentence": segment.is_key_sentence,
                "segment_id": str(segment.segment_id),
                "sequence": segment.sequence,
                "source": "archive_manual",
                "translation_status": segment.translation_status.value,
            },
        )
        return _archive_segment_response_from_record(segment)

    async def _authorize_session(
        self,
        *,
        session_id: uuid.UUID,
        token: str,
    ) -> ArchiveSessionRecord:
        if token.strip() == "":
            raise ArchiveAccessDenied("archive not found or expired")
        session = await self._repository.get_session(session_id)
        if session is None:
            raise ArchiveAccessDenied("archive not found or expired")
        if session.retention_expires_at <= self._clock():
            raise ArchiveAccessDenied("archive not found or expired")
        if not secrets.compare_digest(
            hash_archive_token(token),
            session.archive_token_hash,
        ):
            raise ArchiveAccessDenied("archive not found or expired")
        return session

    async def _find_segment(
        self,
        *,
        session_id: uuid.UUID,
        segment_id: uuid.UUID,
    ) -> ArchiveTranscriptSegmentRecord | None:
        segments = await self._repository.list_segments(session_id)
        return next(
            (
                segment
                for segment in segments
                if segment.segment_id == segment_id
                and segment.session_id == session_id
            ),
            None,
        )


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _archive_segment_response_from_record(
    segment: ArchiveTranscriptSegmentRecord,
) -> ArchiveSegmentResponse:
    return ArchiveSegmentResponse(
        chinese_text_final=segment.chinese_text_final,
        end_ms=segment.end_ms,
        english_text_final=segment.english_text_final,
        is_key_sentence=segment.is_key_sentence,
        segment_id=segment.segment_id,
        sequence=segment.sequence,
        speaker_label=segment.speaker_label,
        start_ms=segment.start_ms,
        translation_retry_attempts=segment.translation_retry_attempts,
        translation_retry_exhausted=segment.translation_retry_exhausted,
        translation_status=segment.translation_status,
    )


def _archive_timeline_items(
    *,
    exception_records: list[ArchiveExceptionTimelineRecord],
    export_records: list[ArchiveExportTimelineRecord],
    segments: list[ArchiveTranscriptSegmentRecord],
    session: ArchiveSessionRecord,
) -> list[ArchiveTimelineItemResponse]:
    timeline_records = []
    for segment in segments:
        timeline_records.append(
            build_segment_final_timeline_item(
                chinese_text_final=segment.chinese_text_final,
                english_text_final=segment.english_text_final,
                end_ms=segment.end_ms,
                segment_id=segment.segment_id,
            ),
        )
        if segment.is_key_sentence:
            timeline_records.append(
                build_key_sentence_timeline_item(
                    chinese_text_final=segment.chinese_text_final,
                    english_text_final=segment.english_text_final,
                    end_ms=segment.end_ms,
                    segment_id=segment.segment_id,
                ),
            )

    for exception_record in exception_records:
        timeline_records.append(
            build_archive_exception_timeline_item(
                code=exception_record.code,
                event_id=exception_record.event_id,
                segment_id=exception_record.segment_id,
                timestamp_ms=relative_timestamp_ms(
                    created_at=exception_record.created_at,
                    session_duration_seconds=session.duration_seconds,
                    session_started_at=session.started_at,
                ),
            ),
        )

    for export_record in export_records:
        timeline_records.append(
            build_export_created_timeline_item(
                export_format=export_record.export_format,
                export_id=export_record.export_id,
                timestamp_ms=relative_timestamp_ms(
                    created_at=export_record.created_at,
                    session_duration_seconds=session.duration_seconds,
                    session_started_at=session.started_at,
                ),
            ),
        )

    return [
        ArchiveTimelineItemResponse(
            id=timeline_record.id,
            item_type=timeline_record.item_type,
            segment_id=timeline_record.segment_id,
            text=timeline_record.text,
            timestamp_ms=timeline_record.timestamp_ms,
        )
        for timeline_record in sort_timeline_items(timeline_records)
    ]


def _archive_segment_record_from_model(
    model: TranscriptSegment,
    *,
    retry_metadata: tuple[int, bool],
) -> ArchiveTranscriptSegmentRecord:
    return ArchiveTranscriptSegmentRecord(
        chinese_text_final=model.chinese_text_final,
        end_ms=model.end_ms,
        english_text_final=model.english_text_final,
        is_key_sentence=model.is_key_sentence,
        segment_id=model.id,
        sequence=model.sequence,
        session_id=model.session_id,
        speaker_label=model.speaker_label,
        start_ms=model.start_ms,
        translation_retry_attempts=retry_metadata[0],
        translation_retry_exhausted=retry_metadata[1],
        translation_status=model.translation_status,
    )


def _archive_exception_timeline_record_from_usage_event(
    event: UsageEvent,
) -> ArchiveExceptionTimelineRecord | None:
    if event.session_id is None or not isinstance(event.payload, dict):
        return None
    code = _exception_code_from_usage_event(event)
    if code is None:
        return None
    return ArchiveExceptionTimelineRecord(
        code=code,
        created_at=event.created_at,
        event_id=event.id,
        segment_id=_segment_id_from_payload(event.payload),
        session_id=event.session_id,
    )


def _exception_code_from_usage_event(event: UsageEvent) -> str | None:
    payload = event.payload
    raw_code = payload.get("code")
    if isinstance(raw_code, str) and raw_code.strip() != "":
        return raw_code
    if event.event_type == UsageEventType.EXPORT_FAILED.value:
        return "archive_export_failed"
    if event.event_type == UsageEventType.QUOTA_EXHAUSTED.value:
        return "daily_quota_exhausted"
    if event.event_type == UsageEventType.BUDGET_FUSE_TRIGGERED.value:
        return "budget_fuse_triggered"
    return None


def _segment_id_from_payload(payload: dict[str, object]) -> uuid.UUID | None:
    raw_segment_id = payload.get("segment_id")
    if not isinstance(raw_segment_id, str):
        return None
    try:
        return uuid.UUID(raw_segment_id)
    except ValueError:
        return None


async def _translation_retry_metadata_by_segment_id(
    *,
    session: AsyncSession,
    session_id: uuid.UUID,
) -> dict[uuid.UUID, tuple[int, bool]]:
    result = await session.scalars(
        select(UsageEvent).where(
            UsageEvent.session_id == session_id,
            UsageEvent.event_type.in_(
                [
                    UsageEventType.TRANSLATION_FINAL_RETRY_REQUESTED.value,
                    UsageEventType.TRANSLATION_FINAL_RETRY_FAILED.value,
                ],
            ),
        ),
    )
    metadata: dict[uuid.UUID, tuple[int, bool]] = {}
    for event in result:
        if not isinstance(event.payload, dict):
            continue
        raw_segment_id = event.payload.get("segment_id")
        if not isinstance(raw_segment_id, str):
            continue
        try:
            segment_id = uuid.UUID(raw_segment_id)
        except ValueError:
            continue
        raw_attempt_number = event.payload.get("attempt_number")
        attempt_number = (
            raw_attempt_number
            if isinstance(raw_attempt_number, int) and raw_attempt_number >= 0
            else 0
        )
        current_attempts, current_exhausted = metadata.get(segment_id, (0, False))
        exhausted = current_exhausted or (
            event.event_type == UsageEventType.TRANSLATION_FINAL_RETRY_FAILED.value
            and event.payload.get("will_retry") is False
        )
        metadata[segment_id] = (max(current_attempts, attempt_number), exhausted)
    return metadata
