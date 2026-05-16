from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from meeting_mvp_backend.db.models import TranslationStatus
from meeting_mvp_backend.translation_providers import (
    FinalTranslationContextSegment,
    FinalTranslationRequest,
)
from meeting_mvp_backend.translation_retries import (
    DEFAULT_TRANSLATION_RETRY_BACKOFF_SECONDS,
    MAX_TRANSLATION_RETRY_ATTEMPTS,
    InMemoryTranslationRetryQueue,
    TranslationRetryJob,
    TranslationRetryProcessor,
    TranslationRetrySegmentRecord,
)
from meeting_mvp_backend.usage_events import UsageEventRecord, UsageEventType

FIXED_NOW = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)
CLIENT_ID = "11111111-1111-4111-8111-111111111111"


class FakeFinalTranslationProvider:
    def __init__(self, outcomes: list[str | Exception]) -> None:
        self.closed = False
        self.outcomes = outcomes
        self.requests: list[FinalTranslationRequest] = []

    async def translate_final(self, request: FinalTranslationRequest) -> str:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def close(self) -> None:
        self.closed = True


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


@dataclass
class FakeTranslationRetryRepository:
    segments: dict[uuid.UUID, TranslationRetrySegmentRecord]
    contexts: list[FinalTranslationContextSegment]
    attempt_counts: dict[uuid.UUID, int] | None = None

    def __post_init__(self) -> None:
        if self.attempt_counts is None:
            self.attempt_counts = {}
        self.retrying_segment_ids: list[uuid.UUID] = []
        self.failed_segment_ids: list[uuid.UUID] = []
        self.completed_segment_ids: list[uuid.UUID] = []

    async def get_segment_for_retry(
        self,
        *,
        now: datetime,
        segment_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None:
        segment = self.segments.get(segment_id)
        if segment is None or segment.session_id != session_id:
            return None
        if segment.retention_expires_at <= now:
            return None
        return segment

    async def list_context_segments(
        self,
        *,
        before_sequence: int,
        limit: int,
        session_id: uuid.UUID,
    ) -> list[FinalTranslationContextSegment]:
        candidates = [
            context
            for context in self.contexts
            if context.sequence < before_sequence
        ]
        return candidates[-limit:]

    async def mark_segment_retrying(
        self,
        *,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None:
        segment = self.segments.get(segment_id)
        if (
            segment is None
            or segment.translation_status is not TranslationStatus.FAILED
        ):
            return None
        updated = segment.with_translation_status(TranslationStatus.RETRYING)
        self.segments[segment_id] = updated
        self.retrying_segment_ids.append(segment_id)
        return updated

    async def mark_segment_completed(
        self,
        *,
        chinese_text_final: str,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None:
        segment = self.segments.get(segment_id)
        if segment is None:
            return None
        updated = segment.with_translation_result(
            chinese_text_final=chinese_text_final,
            translation_status=TranslationStatus.COMPLETED,
        )
        self.segments[segment_id] = updated
        self.completed_segment_ids.append(segment_id)
        return updated

    async def mark_segment_failed(
        self,
        *,
        segment_id: uuid.UUID,
    ) -> TranslationRetrySegmentRecord | None:
        segment = self.segments.get(segment_id)
        if segment is None:
            return None
        updated = segment.with_translation_status(TranslationStatus.FAILED)
        self.segments[segment_id] = updated
        self.failed_segment_ids.append(segment_id)
        return updated

    async def count_retry_attempts(
        self,
        *,
        segment_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> int:
        return self.attempt_counts.get(segment_id, 0) if self.attempt_counts else 0

    async def list_retryable_segments(
        self,
        *,
        now: datetime,
    ) -> list[TranslationRetrySegmentRecord]:
        return [
            segment
            for segment in self.segments.values()
            if segment.retention_expires_at > now
            and segment.translation_status
            in {TranslationStatus.FAILED, TranslationStatus.RETRYING}
        ]


def make_retry_segment(
    *,
    sequence: int = 6,
    session_id: uuid.UUID | None = None,
    status: TranslationStatus = TranslationStatus.FAILED,
) -> TranslationRetrySegmentRecord:
    return TranslationRetrySegmentRecord(
        chinese_text_final="",
        client_id=CLIENT_ID,
        end_ms=sequence * 1000,
        english_text_final=f"English final {sequence}",
        is_key_sentence=False,
        retention_expires_at=FIXED_NOW + timedelta(days=30),
        segment_id=uuid.uuid4(),
        sequence=sequence,
        session_id=session_id or uuid.uuid4(),
        speaker_label=None,
        start_ms=(sequence - 1) * 1000,
        translation_status=status,
    )


def make_context_segments(count: int = 5) -> list[FinalTranslationContextSegment]:
    return [
        FinalTranslationContextSegment(
            chinese_text_final=f"中文 final {sequence}",
            english_text_final=f"English final {sequence}",
            sequence=sequence,
        )
        for sequence in range(1, count + 1)
    ]


@pytest.mark.asyncio
async def test_in_memory_retry_queue_deduplicates_due_jobs_and_locks_segment() -> None:
    session_id = uuid.uuid4()
    segment_id = uuid.uuid4()
    job = TranslationRetryJob(
        due_at=FIXED_NOW,
        segment_id=segment_id,
        session_id=session_id,
    )
    queue = InMemoryTranslationRetryQueue()

    await queue.enqueue(job)
    await queue.enqueue(job)

    assert json.dumps(job.to_safe_payload()) == json.dumps(
        {
            "due_at": FIXED_NOW.isoformat(),
            "segment_id": str(segment_id),
            "session_id": str(session_id),
        },
    )
    assert "token" not in json.dumps(job.to_safe_payload())
    assert "english" not in json.dumps(job.to_safe_payload())
    assert await queue.pop_due(now=FIXED_NOW - timedelta(seconds=1), limit=10) == []
    assert await queue.pop_due(now=FIXED_NOW, limit=10) == [job]
    assert await queue.pop_due(now=FIXED_NOW, limit=10) == []

    assert await queue.acquire_segment_lock(segment_id, ttl_seconds=30) is True
    assert await queue.acquire_segment_lock(segment_id, ttl_seconds=30) is False
    await queue.release_segment_lock(segment_id)
    assert await queue.acquire_segment_lock(segment_id, ttl_seconds=30) is True


@pytest.mark.asyncio
async def test_processor_retries_failed_segment_successfully_with_context() -> None:
    segment = make_retry_segment()
    provider = FakeFinalTranslationProvider(["补译后的正式中文"])
    queue = InMemoryTranslationRetryQueue()
    usage_events = FakeUsageEventRecorder()
    repository = FakeTranslationRetryRepository(
        contexts=make_context_segments(),
        segments={segment.segment_id: segment},
    )
    processor = TranslationRetryProcessor(
        clock=lambda: FIXED_NOW,
        final_translation_provider_factory=lambda: provider,
        queue=queue,
        repository=repository,
        usage_event_recorder=usage_events,
    )

    await processor.process_job(
        TranslationRetryJob(
            due_at=FIXED_NOW,
            segment_id=segment.segment_id,
            session_id=segment.session_id,
        ),
    )

    updated_segment = repository.segments[segment.segment_id]
    assert updated_segment.sequence == segment.sequence
    assert updated_segment.translation_status is TranslationStatus.COMPLETED
    assert updated_segment.chinese_text_final == "补译后的正式中文"
    assert repository.retrying_segment_ids == [segment.segment_id]
    assert repository.completed_segment_ids == [segment.segment_id]
    assert provider.requests == [
        FinalTranslationRequest(
            context=tuple(make_context_segments()),
            sequence=segment.sequence,
            text=segment.english_text_final,
        ),
    ]
    assert [record.event_type for record in usage_events.records] == [
        UsageEventType.TRANSLATION_FINAL_RETRY_REQUESTED,
        UsageEventType.TRANSLATION_FINAL_COMPLETED,
    ]
    assert usage_events.records[0].payload["attempt_number"] == 1
    assert usage_events.records[0].payload["english_length"] == len(
        segment.english_text_final,
    )
    assert usage_events.records[1].payload["retry"] is True
    assert usage_events.records[1].payload["chinese_length"] == len(
        "补译后的正式中文",
    )
    assert usage_events.records[1].payload["english_length"] == len(
        segment.english_text_final,
    )
    payload_json = json.dumps(
        [record.payload for record in usage_events.records],
        ensure_ascii=False,
    )
    assert segment.english_text_final not in payload_json
    assert "补译后的正式中文" not in payload_json
    assert await queue.pop_due(now=FIXED_NOW + timedelta(days=1), limit=10) == []


@pytest.mark.asyncio
async def test_processor_requeues_failed_retry_until_max_attempts() -> None:
    segment = make_retry_segment()
    provider = FakeFinalTranslationProvider([RuntimeError("qwen unavailable")])
    queue = InMemoryTranslationRetryQueue()
    usage_events = FakeUsageEventRecorder()
    repository = FakeTranslationRetryRepository(
        contexts=[],
        segments={segment.segment_id: segment},
    )
    processor = TranslationRetryProcessor(
        clock=lambda: FIXED_NOW,
        final_translation_provider_factory=lambda: provider,
        queue=queue,
        repository=repository,
        usage_event_recorder=usage_events,
    )

    await processor.process_job(
        TranslationRetryJob(
            due_at=FIXED_NOW,
            segment_id=segment.segment_id,
            session_id=segment.session_id,
        ),
    )

    assert repository.segments[segment.segment_id].translation_status is (
        TranslationStatus.FAILED
    )
    retry_jobs = await queue.pop_due(
        now=FIXED_NOW
        + timedelta(seconds=DEFAULT_TRANSLATION_RETRY_BACKOFF_SECONDS[0]),
        limit=10,
    )
    assert retry_jobs == [
        TranslationRetryJob(
            due_at=FIXED_NOW
            + timedelta(seconds=DEFAULT_TRANSLATION_RETRY_BACKOFF_SECONDS[0]),
            segment_id=segment.segment_id,
            session_id=segment.session_id,
        ),
    ]
    failed_record = usage_events.records[-1]
    assert failed_record.event_type is UsageEventType.TRANSLATION_FINAL_RETRY_FAILED
    assert failed_record.payload["attempt_number"] == 1
    assert failed_record.payload["will_retry"] is True
    assert "qwen unavailable" not in json.dumps(failed_record.payload)


@pytest.mark.asyncio
async def test_processor_stops_requeueing_after_max_attempts() -> None:
    segment = make_retry_segment()
    provider = FakeFinalTranslationProvider([RuntimeError("qwen unavailable")])
    queue = InMemoryTranslationRetryQueue()
    usage_events = FakeUsageEventRecorder()
    repository = FakeTranslationRetryRepository(
        attempt_counts={segment.segment_id: MAX_TRANSLATION_RETRY_ATTEMPTS - 1},
        contexts=[],
        segments={segment.segment_id: segment},
    )
    processor = TranslationRetryProcessor(
        clock=lambda: FIXED_NOW,
        final_translation_provider_factory=lambda: provider,
        queue=queue,
        repository=repository,
        usage_event_recorder=usage_events,
    )

    await processor.process_job(
        TranslationRetryJob(
            due_at=FIXED_NOW,
            segment_id=segment.segment_id,
            session_id=segment.session_id,
        ),
    )

    assert await queue.pop_due(now=FIXED_NOW + timedelta(days=1), limit=10) == []
    failed_record = usage_events.records[-1]
    assert failed_record.payload["attempt_number"] == MAX_TRANSLATION_RETRY_ATTEMPTS
    assert failed_record.payload["max_attempts"] == MAX_TRANSLATION_RETRY_ATTEMPTS
    assert failed_record.payload["will_retry"] is False


@pytest.mark.asyncio
async def test_processor_skips_expired_missing_or_completed_segments() -> None:
    expired_segment = make_retry_segment()
    expired_segment = expired_segment.with_retention_expires_at(
        FIXED_NOW - timedelta(seconds=1),
    )
    completed_segment = make_retry_segment(status=TranslationStatus.COMPLETED)
    provider = FakeFinalTranslationProvider(["不应调用"])
    repository = FakeTranslationRetryRepository(
        contexts=[],
        segments={
            expired_segment.segment_id: expired_segment,
            completed_segment.segment_id: completed_segment,
        },
    )
    processor = TranslationRetryProcessor(
        clock=lambda: FIXED_NOW,
        final_translation_provider_factory=lambda: provider,
        queue=InMemoryTranslationRetryQueue(),
        repository=repository,
        usage_event_recorder=FakeUsageEventRecorder(),
    )

    await processor.process_job(
        TranslationRetryJob(
            due_at=FIXED_NOW,
            segment_id=expired_segment.segment_id,
            session_id=expired_segment.session_id,
        ),
    )
    await processor.process_job(
        TranslationRetryJob(
            due_at=FIXED_NOW,
            segment_id=completed_segment.segment_id,
            session_id=completed_segment.session_id,
        ),
    )
    await processor.process_job(
        TranslationRetryJob(
            due_at=FIXED_NOW,
            segment_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
        ),
    )

    assert provider.requests == []
    assert repository.retrying_segment_ids == []


@pytest.mark.asyncio
async def test_startup_scan_enqueues_existing_failed_and_retrying_segments() -> None:
    failed_segment = make_retry_segment()
    retrying_segment = make_retry_segment(status=TranslationStatus.RETRYING)
    completed_segment = make_retry_segment(status=TranslationStatus.COMPLETED)
    queue = InMemoryTranslationRetryQueue()
    processor = TranslationRetryProcessor(
        clock=lambda: FIXED_NOW,
        final_translation_provider_factory=lambda: FakeFinalTranslationProvider([]),
        queue=queue,
        repository=FakeTranslationRetryRepository(
            contexts=[],
            segments={
                failed_segment.segment_id: failed_segment,
                retrying_segment.segment_id: retrying_segment,
                completed_segment.segment_id: completed_segment,
            },
        ),
        usage_event_recorder=None,
    )

    await processor.enqueue_existing_retryable_segments()

    assert await queue.pop_due(now=FIXED_NOW, limit=10) == [
        TranslationRetryJob(
            due_at=FIXED_NOW,
            segment_id=failed_segment.segment_id,
            session_id=failed_segment.session_id,
        ),
        TranslationRetryJob(
            due_at=FIXED_NOW,
            segment_id=retrying_segment.segment_id,
            session_id=retrying_segment.session_id,
        ),
    ]


@pytest.mark.asyncio
async def test_usage_event_failure_does_not_block_successful_retry() -> None:
    segment = make_retry_segment()
    provider = FakeFinalTranslationProvider(["补译后的正式中文"])
    repository = FakeTranslationRetryRepository(
        contexts=[],
        segments={segment.segment_id: segment},
    )
    processor = TranslationRetryProcessor(
        clock=lambda: FIXED_NOW,
        final_translation_provider_factory=lambda: provider,
        queue=InMemoryTranslationRetryQueue(),
        repository=repository,
        usage_event_recorder=FakeUsageEventRecorder(fail=True),
    )

    await processor.process_job(
        TranslationRetryJob(
            due_at=FIXED_NOW,
            segment_id=segment.segment_id,
            session_id=segment.session_id,
        ),
    )

    assert repository.segments[segment.segment_id].translation_status is (
        TranslationStatus.COMPLETED
    )
    assert repository.segments[segment.segment_id].chinese_text_final == (
        "补译后的正式中文"
    )
