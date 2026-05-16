from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self, cast

import pytest

from meeting_mvp_backend.db.models import UsageEvent
from meeting_mvp_backend.usage_events import (
    STEP_21_USAGE_EVENT_TYPES,
    STEP_23_USAGE_EVENT_TYPES,
    SQLAlchemyUsageEventRecorder,
    UnsafeUsageEventPayload,
    UsageEventRecord,
    UsageEventType,
    build_usage_event_record,
    record_usage_event_best_effort,
    validate_usage_event_payload,
)

FIXED_NOW = datetime(2026, 5, 15, 8, 30, tzinfo=UTC)


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[UsageEvent] = []
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    def add(self, model: UsageEvent) -> None:
        self.added.append(model)

    async def commit(self) -> None:
        self.committed = True


class FakeSessionFactory:
    def __init__(self) -> None:
        self.last_session: FakeAsyncSession | None = None

    def __call__(self) -> FakeAsyncSession:
        self.last_session = FakeAsyncSession()
        return self.last_session


class FailingUsageEventRecorder:
    async def record_event(
        self,
        *,
        client_id: str,
        event_type: UsageEventType | str,
        payload: dict[str, object] | None = None,
        session_id: uuid.UUID | str | None = None,
    ) -> UsageEventRecord:
        raise RuntimeError("database temporarily unavailable")


def test_step_21_event_types_are_allowlisted() -> None:
    assert {event_type.value for event_type in STEP_21_USAGE_EVENT_TYPES} == {
        "client_created",
        "quota_checked",
        "capture_started",
        "capture_failed",
        "audio_detected",
        "session_started",
        "asr_interim_received",
        "asr_final_received",
        "translation_interim_requested",
        "translation_final_completed",
        "segment_archived",
        "archive_viewed",
        "provider_error",
        "quota_exhausted",
        "budget_fuse_triggered",
        "session_closed",
    }


def test_step_23_event_types_extend_usage_event_allowlist() -> None:
    assert {event_type.value for event_type in STEP_23_USAGE_EVENT_TYPES} == {
        *{event_type.value for event_type in STEP_21_USAGE_EVENT_TYPES},
        "archive_searched",
        "segment_copied",
    }


def test_build_usage_event_record_populates_required_fields_for_each_event() -> None:
    client_id = str(uuid.uuid4())
    session_id = uuid.uuid4()

    records = [
        build_usage_event_record(
            client_id=client_id,
            session_id=session_id,
            event_type=event_type,
            payload={"ok": True},
            created_at=FIXED_NOW,
        )
        for event_type in STEP_21_USAGE_EVENT_TYPES
    ]

    assert len(records) == len(STEP_21_USAGE_EVENT_TYPES)
    assert {record.client_id for record in records} == {client_id}
    assert {record.session_id for record in records} == {session_id}
    assert {record.payload["ok"] for record in records} == {True}
    assert {record.created_at for record in records} == {FIXED_NOW}
    assert {record.event_type for record in records} == set(STEP_21_USAGE_EVENT_TYPES)


@pytest.mark.parametrize(
    "payload",
    [
        {"raw_audio": [0, 1, 2]},
        {"api_key": "secret-value"},
        {"nested": {"archive_token": "secret-token"}},
        {"query": "launch timeline"},
        {"text": "raw meeting text"},
        {"english_text": "We need to align."},
        {"chinese_text": "我们需要对齐。"},
        {"frame": b"\x00\x01"},
        {"items": [{"private_key": "secret-value"}]},
    ],
)
def test_usage_event_payload_rejects_audio_and_secret_material(
    payload: dict[str, object],
) -> None:
    with pytest.raises(UnsafeUsageEventPayload):
        validate_usage_event_payload(payload)


def test_usage_event_payload_keeps_safe_observability_metadata() -> None:
    assert validate_usage_event_payload(
        {
            "remaining_seconds_today": 1800,
            "allowed": True,
            "provider": "qwen_final_translation",
            "nested": {"text_length": 42, "has_confidence": False},
        },
    ) == {
        "remaining_seconds_today": 1800,
        "allowed": True,
        "provider": "qwen_final_translation",
        "nested": {"text_length": 42, "has_confidence": False},
    }


@pytest.mark.asyncio
async def test_sqlalchemy_recorder_writes_usage_event_model() -> None:
    client_id = str(uuid.uuid4())
    session_id = uuid.uuid4()
    factory = FakeSessionFactory()
    recorder = SQLAlchemyUsageEventRecorder(
        session_factory=cast(Any, factory),
        clock=lambda: FIXED_NOW,
    )

    record = await recorder.record_event(
        client_id=client_id,
        session_id=session_id,
        event_type=UsageEventType.SESSION_STARTED,
        payload={"remaining_seconds_today": 2400},
    )

    assert factory.last_session is not None
    assert factory.last_session.committed is True
    assert len(factory.last_session.added) == 1
    saved_model = factory.last_session.added[0]
    assert saved_model.client_id == client_id
    assert saved_model.session_id == session_id
    assert saved_model.event_type == "session_started"
    assert saved_model.payload == {"remaining_seconds_today": 2400}
    assert saved_model.created_at == FIXED_NOW
    assert record.client_id == client_id
    assert record.session_id == session_id
    assert record.created_at == FIXED_NOW


@pytest.mark.asyncio
async def test_usage_event_best_effort_does_not_interrupt_callers() -> None:
    result = await record_usage_event_best_effort(
        recorder=FailingUsageEventRecorder(),
        client_id=str(uuid.uuid4()),
        event_type=UsageEventType.SESSION_STARTED,
        payload={"remaining_seconds_today": 2400},
    )

    assert result is None
