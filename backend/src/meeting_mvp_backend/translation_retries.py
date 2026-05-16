from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Protocol, Self

import structlog
from redis.asyncio import Redis
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.db.models import (
    MeetingSession,
    TranscriptSegment,
    TranslationStatus,
    UsageEvent,
)
from meeting_mvp_backend.translation_providers import (
    FinalTranslationContextSegment,
    FinalTranslationError,
    FinalTranslationProvider,
    FinalTranslationRequest,
)
from meeting_mvp_backend.usage_events import (
    UsageEventRecorder,
    UsageEventType,
    record_usage_event_best_effort,
)

logger = structlog.get_logger(__name__)

Clock = Callable[[], datetime]
FinalTranslationProviderFactory = Callable[[], FinalTranslationProvider]

MAX_TRANSLATION_RETRY_ATTEMPTS = 3
DEFAULT_TRANSLATION_RETRY_BACKOFF_SECONDS = (30, 300, 900)
TRANSLATION_RETRY_CONTEXT_SEGMENT_LIMIT = 5
TRANSLATION_RETRY_QUEUE_KEY = "meeting_mvp:translation_retry:scheduled"
TRANSLATION_RETRY_LOCK_KEY_PREFIX = "meeting_mvp:translation_retry:lock"
TRANSLATION_RETRY_LOCK_TTL_SECONDS = 120
TRANSLATION_RETRY_WORKER_POLL_INTERVAL_SECONDS = 2.0
TRANSLATION_RETRY_WORKER_BATCH_SIZE = 10


@dataclass(frozen=True, slots=True)
class TranslationRetryJob:
    session_id: uuid.UUID
    segment_id: uuid.UUID
    due_at: datetime

    def to_safe_payload(self) -> dict[str, str]:
        return {
            "due_at": self.due_at.isoformat(),
            "segment_id": str(self.segment_id),
            "session_id": str(self.session_id),
        }

    def to_redis_member(self) -> str:
        return f"{self.session_id}:{self.segment_id}"

    @classmethod
    def from_redis_member(cls, member: object, *, due_at: datetime) -> Self | None:
        decoded = _decode_redis_member(member)
        if decoded is None:
            return None
        parts = decoded.split(":")
        if len(parts) != 2:
            return None
        try:
            session_id = uuid.UUID(parts[0])
            segment_id = uuid.UUID(parts[1])
        except ValueError:
            return None
        return cls(session_id=session_id, segment_id=segment_id, due_at=due_at)


@dataclass(frozen=True, slots=True)
class TranslationRetrySegmentRecord:
    segment_id: uuid.UUID
    session_id: uuid.UUID
    client_id: str
    sequence: int
    start_ms: int
    end_ms: int
    speaker_label: str | None
    english_text_final: str
    chinese_text_final: str
    translation_status: TranslationStatus
    is_key_sentence: bool
    retention_expires_at: datetime

    def with_translation_status(
        self,
        translation_status: TranslationStatus,
    ) -> TranslationRetrySegmentRecord:
        return replace(self, translation_status=translation_status)

    def with_translation_result(
        self,
        *,
        chinese_text_final: str,
        translation_status: TranslationStatus,
    ) -> TranslationRetrySegmentRecord:
        return replace(
            self,
            chinese_text_final=chinese_text_final,
            translation_status=translation_status,
        )

    def with_retention_expires_at(
        self,
        retention_expires_at: datetime,
    ) -> TranslationRetrySegmentRecord:
        return replace(self, retention_expires_at=retention_expires_at)


class TranslationRetryQueue(Protocol):
    async def enqueue(self, job: TranslationRetryJob) -> None: ...

    async def pop_due(
        self,
        *,
        limit: int,
        now: datetime,
    ) -> list[TranslationRetryJob]: ...

    async def acquire_segment_lock(
        self,
        segment_id: uuid.UUID,
        *,
        ttl_seconds: int,
    ) -> bool: ...

    async def release_segment_lock(self, segment_id: uuid.UUID) -> None: ...

    async def close(self) -> None: ...


class TranslationRetryRepository(Protocol):
    async def get_segment_for_retry(
        self,
        *,
        now: datetime,
        segment_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None: ...

    async def list_context_segments(
        self,
        *,
        before_sequence: int,
        limit: int,
        session_id: uuid.UUID,
    ) -> list[FinalTranslationContextSegment]: ...

    async def mark_segment_retrying(
        self,
        *,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None: ...

    async def mark_segment_completed(
        self,
        *,
        chinese_text_final: str,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None: ...

    async def mark_segment_failed(
        self,
        *,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None: ...

    async def count_retry_attempts(
        self,
        *,
        segment_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> int: ...

    async def list_retryable_segments(
        self,
        *,
        now: datetime,
    ) -> list[TranslationRetrySegmentRecord]: ...


class InMemoryTranslationRetryQueue:
    def __init__(self) -> None:
        self._jobs: dict[tuple[uuid.UUID, uuid.UUID], TranslationRetryJob] = {}
        self._locks: set[uuid.UUID] = set()

    async def enqueue(self, job: TranslationRetryJob) -> None:
        self._jobs[(job.session_id, job.segment_id)] = job

    async def pop_due(
        self,
        *,
        limit: int,
        now: datetime,
    ) -> list[TranslationRetryJob]:
        due_jobs = [
            job
            for job in self._jobs.values()
            if _ensure_aware(job.due_at) <= _ensure_aware(now)
        ]
        due_jobs = sorted(due_jobs, key=lambda job: job.due_at)[:limit]
        for job in due_jobs:
            self._jobs.pop((job.session_id, job.segment_id), None)
        return due_jobs

    async def acquire_segment_lock(
        self,
        segment_id: uuid.UUID,
        *,
        ttl_seconds: int,
    ) -> bool:
        del ttl_seconds
        if segment_id in self._locks:
            return False
        self._locks.add(segment_id)
        return True

    async def release_segment_lock(self, segment_id: uuid.UUID) -> None:
        self._locks.discard(segment_id)

    async def close(self) -> None:
        return None


class RedisTranslationRetryQueue:
    def __init__(
        self,
        redis_client: Redis,
        *,
        queue_key: str = TRANSLATION_RETRY_QUEUE_KEY,
    ) -> None:
        self._queue_key = queue_key
        self._redis = redis_client

    async def enqueue(self, job: TranslationRetryJob) -> None:
        await self._redis.zadd(
            self._queue_key,
            {job.to_redis_member(): _ensure_aware(job.due_at).timestamp()},
        )

    async def pop_due(
        self,
        *,
        limit: int,
        now: datetime,
    ) -> list[TranslationRetryJob]:
        raw_jobs = await self._redis.zrangebyscore(
            self._queue_key,
            "-inf",
            _ensure_aware(now).timestamp(),
            start=0,
            num=limit,
            withscores=True,
        )
        jobs: list[TranslationRetryJob] = []
        members: list[str] = []
        for raw_member, score in raw_jobs:
            due_at = datetime.fromtimestamp(float(score), tz=UTC)
            job = TranslationRetryJob.from_redis_member(raw_member, due_at=due_at)
            if job is not None:
                jobs.append(job)
                members.append(job.to_redis_member())
        if members:
            await self._redis.zrem(self._queue_key, *members)
        return jobs

    async def acquire_segment_lock(
        self,
        segment_id: uuid.UUID,
        *,
        ttl_seconds: int,
    ) -> bool:
        result = await self._redis.set(
            _translation_retry_lock_key(segment_id),
            "1",
            ex=ttl_seconds,
            nx=True,
        )
        return bool(result)

    async def release_segment_lock(self, segment_id: uuid.UUID) -> None:
        await self._redis.delete(_translation_retry_lock_key(segment_id))

    async def close(self) -> None:
        await self._redis.aclose()


class SQLAlchemyTranslationRetryRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def get_segment_for_retry(
        self,
        *,
        now: datetime,
        segment_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    select(TranscriptSegment, MeetingSession)
                    .join(
                        MeetingSession,
                        TranscriptSegment.session_id == MeetingSession.id,
                    )
                    .where(
                        TranscriptSegment.id == segment_id,
                        TranscriptSegment.session_id == session_id,
                        MeetingSession.retention_expires_at > now,
                    ),
                )
            ).one_or_none()
        if row is None:
            return None
        segment, meeting_session = row
        return _segment_record_from_models(segment, meeting_session)

    async def list_context_segments(
        self,
        *,
        before_sequence: int,
        limit: int,
        session_id: uuid.UUID,
    ) -> list[FinalTranslationContextSegment]:
        async with self._session_factory() as session:
            result = await session.scalars(
                select(TranscriptSegment)
                .where(
                    TranscriptSegment.session_id == session_id,
                    TranscriptSegment.sequence < before_sequence,
                    TranscriptSegment.translation_status == TranslationStatus.COMPLETED,
                )
                .order_by(desc(TranscriptSegment.sequence))
                .limit(limit),
            )
            segments = list(result)
        return [
            FinalTranslationContextSegment(
                chinese_text_final=segment.chinese_text_final,
                english_text_final=segment.english_text_final,
                sequence=segment.sequence,
            )
            for segment in reversed(segments)
        ]

    async def mark_segment_retrying(
        self,
        *,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None:
        return await self._set_segment_status(
            segment_id=segment_id,
            required_status=TranslationStatus.FAILED,
            translation_status=TranslationStatus.RETRYING,
        )

    async def mark_segment_completed(
        self,
        *,
        chinese_text_final: str,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None:
        async with self._session_factory() as session:
            await session.execute(
                update(TranscriptSegment)
                .where(TranscriptSegment.id == segment_id)
                .values(
                    chinese_text_final=chinese_text_final,
                    translation_status=TranslationStatus.COMPLETED,
                ),
            )
            await session.commit()
        return await self._get_segment_by_id(segment_id)

    async def mark_segment_failed(
        self,
        *,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None:
        return await self._set_segment_status(
            segment_id=segment_id,
            required_status=None,
            translation_status=TranslationStatus.FAILED,
        )

    async def count_retry_attempts(
        self,
        *,
        segment_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> int:
        async with self._session_factory() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(UsageEvent)
                .where(
                    UsageEvent.session_id == session_id,
                    UsageEvent.event_type
                    == UsageEventType.TRANSLATION_FINAL_RETRY_REQUESTED.value,
                    UsageEvent.payload["segment_id"].as_string() == str(segment_id),
                ),
            )
        return int(count or 0)

    async def list_retryable_segments(
        self,
        *,
        now: datetime,
    ) -> list[TranslationRetrySegmentRecord]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TranscriptSegment, MeetingSession)
                .join(
                    MeetingSession,
                    TranscriptSegment.session_id == MeetingSession.id,
                )
                .where(
                    MeetingSession.retention_expires_at > now,
                    TranscriptSegment.translation_status.in_(
                        [TranslationStatus.FAILED, TranslationStatus.RETRYING],
                    ),
                )
                .order_by(TranscriptSegment.created_at, TranscriptSegment.sequence),
            )
            rows = list(result)
        return [
            _segment_record_from_models(segment, meeting_session)
            for segment, meeting_session in rows
        ]

    async def _set_segment_status(
        self,
        *,
        required_status: TranslationStatus | None,
        segment_id: uuid.UUID,
        translation_status: TranslationStatus,
    ) -> TranslationRetrySegmentRecord | None:
        where_clauses = [TranscriptSegment.id == segment_id]
        if required_status is not None:
            where_clauses.append(
                TranscriptSegment.translation_status == required_status,
            )
        async with self._session_factory() as session:
            await session.execute(
                update(TranscriptSegment)
                .where(*where_clauses)
                .values(translation_status=translation_status),
            )
            await session.commit()
        return await self._get_segment_by_id(segment_id)

    async def _get_segment_by_id(
        self,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    select(TranscriptSegment, MeetingSession)
                    .join(
                        MeetingSession,
                        TranscriptSegment.session_id == MeetingSession.id,
                    )
                    .where(TranscriptSegment.id == segment_id),
                )
            ).one_or_none()
        if row is None:
            return None
        segment, meeting_session = row
        return _segment_record_from_models(segment, meeting_session)


class TranslationRetryProcessor:
    def __init__(
        self,
        *,
        final_translation_provider_factory: FinalTranslationProviderFactory,
        queue: TranslationRetryQueue,
        repository: TranslationRetryRepository,
        backoff_seconds: Sequence[int] = DEFAULT_TRANSLATION_RETRY_BACKOFF_SECONDS,
        clock: Clock | None = None,
        max_attempts: int = MAX_TRANSLATION_RETRY_ATTEMPTS,
        usage_event_recorder: UsageEventRecorder | None = None,
    ) -> None:
        self._backoff_seconds = tuple(backoff_seconds)
        self._clock = clock or _now_utc
        self._final_translation_provider_factory = final_translation_provider_factory
        self._max_attempts = max_attempts
        self._queue = queue
        self._repository = repository
        self._usage_event_recorder = usage_event_recorder

    async def enqueue_existing_retryable_segments(self) -> None:
        now = self._clock()
        for segment in await self._repository.list_retryable_segments(now=now):
            await self._queue.enqueue(
                TranslationRetryJob(
                    due_at=now,
                    segment_id=segment.segment_id,
                    session_id=segment.session_id,
                ),
            )

    async def process_job(self, job: TranslationRetryJob) -> None:
        lock_acquired = await self._queue.acquire_segment_lock(
            job.segment_id,
            ttl_seconds=TRANSLATION_RETRY_LOCK_TTL_SECONDS,
        )
        if not lock_acquired:
            return
        try:
            await self._process_locked_job(job)
        finally:
            await self._queue.release_segment_lock(job.segment_id)

    async def _process_locked_job(self, job: TranslationRetryJob) -> None:
        now = self._clock()
        segment = await self._repository.get_segment_for_retry(
            now=now,
            segment_id=job.segment_id,
            session_id=job.session_id,
        )
        if segment is None:
            return
        if segment.translation_status is TranslationStatus.COMPLETED:
            return

        attempts_before = await self._repository.count_retry_attempts(
            segment_id=segment.segment_id,
            session_id=segment.session_id,
        )
        if attempts_before >= self._max_attempts:
            return

        if segment.translation_status is TranslationStatus.FAILED:
            retrying_segment = await self._repository.mark_segment_retrying(
                segment_id=segment.segment_id,
            )
            if retrying_segment is None:
                return
            segment = retrying_segment
        elif segment.translation_status is not TranslationStatus.RETRYING:
            return

        attempt_number = attempts_before + 1
        context = await self._repository.list_context_segments(
            before_sequence=segment.sequence,
            limit=TRANSLATION_RETRY_CONTEXT_SEGMENT_LIMIT,
            session_id=segment.session_id,
        )
        await self._record_retry_requested(
            attempt_number=attempt_number,
            context_segment_count=len(context),
            segment=segment,
        )

        provider = self._final_translation_provider_factory()
        try:
            translated_text = (
                await provider.translate_final(
                    FinalTranslationRequest(
                        context=tuple(context),
                        sequence=segment.sequence,
                        text=segment.english_text_final,
                    ),
                )
            ).strip()
            if translated_text == "":
                raise FinalTranslationError("Qwen final retry returned empty text")
        except Exception as exc:
            await self._handle_retry_failure(
                attempt_number=attempt_number,
                error_type=exc.__class__.__name__,
                segment=segment,
            )
            return
        finally:
            await provider.close()

        completed_segment = await self._repository.mark_segment_completed(
            chinese_text_final=translated_text,
            segment_id=segment.segment_id,
        )
        if completed_segment is None:
            return
        await record_usage_event_best_effort(
            recorder=self._usage_event_recorder,
            client_id=completed_segment.client_id,
            session_id=completed_segment.session_id,
            event_type=UsageEventType.TRANSLATION_FINAL_COMPLETED,
            payload={
                "attempt_number": attempt_number,
                "chinese_length": len(translated_text),
                "context_segment_count": len(context),
                "english_length": len(completed_segment.english_text_final),
                "retry": True,
                "segment_id": str(completed_segment.segment_id),
                "sequence": completed_segment.sequence,
            },
        )

    async def _handle_retry_failure(
        self,
        *,
        attempt_number: int,
        error_type: str,
        segment: TranslationRetrySegmentRecord,
    ) -> None:
        failed_segment = await self._repository.mark_segment_failed(
            segment_id=segment.segment_id,
        )
        segment_for_event = failed_segment or segment.with_translation_status(
            TranslationStatus.FAILED,
        )
        will_retry = attempt_number < self._max_attempts
        await record_usage_event_best_effort(
            recorder=self._usage_event_recorder,
            client_id=segment_for_event.client_id,
            session_id=segment_for_event.session_id,
            event_type=UsageEventType.TRANSLATION_FINAL_RETRY_FAILED,
            payload={
                "attempt_number": attempt_number,
                "error_type": error_type,
                "max_attempts": self._max_attempts,
                "segment_id": str(segment_for_event.segment_id),
                "sequence": segment_for_event.sequence,
                "stage": "provider",
                "will_retry": will_retry,
            },
        )
        if not will_retry:
            return
        await self._queue.enqueue(
            TranslationRetryJob(
                due_at=self._clock()
                + timedelta(
                    seconds=self._backoff_seconds[
                        min(attempt_number - 1, len(self._backoff_seconds) - 1)
                    ],
                ),
                segment_id=segment_for_event.segment_id,
                session_id=segment_for_event.session_id,
            ),
        )

    async def _record_retry_requested(
        self,
        *,
        attempt_number: int,
        context_segment_count: int,
        segment: TranslationRetrySegmentRecord,
    ) -> None:
        await record_usage_event_best_effort(
            recorder=self._usage_event_recorder,
            client_id=segment.client_id,
            session_id=segment.session_id,
            event_type=UsageEventType.TRANSLATION_FINAL_RETRY_REQUESTED,
            payload={
                "attempt_number": attempt_number,
                "context_segment_count": context_segment_count,
                "english_length": len(segment.english_text_final),
                "max_attempts": self._max_attempts,
                "segment_id": str(segment.segment_id),
                "sequence": segment.sequence,
            },
        )


class TranslationRetryWorker:
    def __init__(
        self,
        *,
        batch_size: int = TRANSLATION_RETRY_WORKER_BATCH_SIZE,
        clock: Clock | None = None,
        poll_interval_seconds: float = TRANSLATION_RETRY_WORKER_POLL_INTERVAL_SECONDS,
        processor: TranslationRetryProcessor,
        queue: TranslationRetryQueue,
    ) -> None:
        self._batch_size = batch_size
        self._clock = clock or _now_utc
        self._poll_interval_seconds = poll_interval_seconds
        self._processor = processor
        self._queue = queue

    async def run_once(self) -> None:
        jobs = await self._queue.pop_due(now=self._clock(), limit=self._batch_size)
        for job in jobs:
            await self._processor.process_job(job)

    async def run_forever(self) -> None:
        await self._processor.enqueue_existing_retryable_segments()
        while True:
            await self.run_once()
            await asyncio.sleep(self._poll_interval_seconds)


def create_redis_translation_retry_queue_from_settings(
    settings: Settings,
) -> RedisTranslationRetryQueue:
    if settings.redis_url is None:
        msg = "REDIS_URL is required for translation retry queue"
        raise RuntimeError(msg)
    return RedisTranslationRetryQueue(Redis.from_url(settings.redis_url))


def _decode_redis_member(member: object) -> str | None:
    if isinstance(member, bytes):
        return member.decode("utf-8")
    if isinstance(member, str):
        return member
    return None


def _translation_retry_lock_key(segment_id: uuid.UUID) -> str:
    return f"{TRANSLATION_RETRY_LOCK_KEY_PREFIX}:{segment_id}"


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _segment_record_from_models(
    segment: TranscriptSegment,
    meeting_session: MeetingSession,
) -> TranslationRetrySegmentRecord:
    return TranslationRetrySegmentRecord(
        chinese_text_final=segment.chinese_text_final,
        client_id=meeting_session.client_id,
        end_ms=segment.end_ms,
        english_text_final=segment.english_text_final,
        is_key_sentence=segment.is_key_sentence,
        retention_expires_at=meeting_session.retention_expires_at,
        segment_id=segment.id,
        sequence=segment.sequence,
        session_id=segment.session_id,
        speaker_label=segment.speaker_label,
        start_ms=segment.start_ms,
        translation_status=segment.translation_status,
    )


def _now_utc() -> datetime:
    return datetime.now(UTC)
