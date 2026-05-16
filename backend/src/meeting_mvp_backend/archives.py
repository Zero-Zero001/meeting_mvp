from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast

from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from meeting_mvp_backend.archive_tokens import hash_archive_token
from meeting_mvp_backend.db.models import (
    CaptureMode,
    MeetingSession,
    MeetingSessionStatus,
    SourcePlatform,
    TranscriptSegment,
    TranslationStatus,
    UsageEvent,
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


class ArchiveRepository(Protocol):
    async def get_session(
        self,
        session_id: uuid.UUID,
    ) -> ArchiveSessionRecord | None: ...

    async def list_segments(
        self,
        session_id: uuid.UUID,
    ) -> list[ArchiveTranscriptSegmentRecord]: ...

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
        return [
            ArchiveTranscriptSegmentRecord(
                chinese_text_final=model.chinese_text_final,
                end_ms=model.end_ms,
                english_text_final=model.english_text_final,
                is_key_sentence=model.is_key_sentence,
                segment_id=model.id,
                sequence=model.sequence,
                session_id=model.session_id,
                speaker_label=model.speaker_label,
                start_ms=model.start_ms,
                translation_status=model.translation_status,
            )
            for model in models
        ]

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

        segments = sorted(
            await self._repository.list_segments(session_id),
            key=lambda segment: segment.sequence,
        )
        end_reason = (
            await self._repository.latest_session_closed_reason(session_id)
        ) or session.status.value
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
                    translation_status=segment.translation_status,
                )
                for segment in segments
            ],
            session_id=session.session_id,
            source_platform=session.source_platform,
            started_at=session.started_at,
            status=session.status,
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


def _now_utc() -> datetime:
    return datetime.now(UTC)
