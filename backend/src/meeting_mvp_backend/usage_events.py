from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from meeting_mvp_backend.db.models import UsageEvent

logger = structlog.get_logger(__name__)

Clock = Callable[[], datetime]
_BINARY_TYPES = bytes | bytearray | memoryview
_FORBIDDEN_PAYLOAD_KEY_PARTS = (
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "private_key",
    "credential",
    "raw_audio",
    "audio_bytes",
    "audio_frame",
    "pcm",
)


class UsageEventType(StrEnum):
    CLIENT_CREATED = "client_created"
    QUOTA_CHECKED = "quota_checked"
    CAPTURE_STARTED = "capture_started"
    CAPTURE_FAILED = "capture_failed"
    AUDIO_DETECTED = "audio_detected"
    SESSION_STARTED = "session_started"
    ASR_INTERIM_RECEIVED = "asr_interim_received"
    ASR_FINAL_RECEIVED = "asr_final_received"
    TRANSLATION_INTERIM_REQUESTED = "translation_interim_requested"
    TRANSLATION_FINAL_COMPLETED = "translation_final_completed"
    SEGMENT_ARCHIVED = "segment_archived"
    ARCHIVE_VIEWED = "archive_viewed"
    PROVIDER_ERROR = "provider_error"
    QUOTA_EXHAUSTED = "quota_exhausted"
    BUDGET_FUSE_TRIGGERED = "budget_fuse_triggered"
    SESSION_CLOSED = "session_closed"


STEP_21_USAGE_EVENT_TYPES: tuple[UsageEventType, ...] = tuple(UsageEventType)


class UnsafeUsageEventPayload(ValueError):
    """Raised when a usage event payload contains audio or secret material."""


@dataclass(frozen=True, slots=True)
class UsageEventRecord:
    client_id: str
    session_id: uuid.UUID | None
    event_type: UsageEventType
    payload: dict[str, object]
    created_at: datetime


class UsageEventRecorder(Protocol):
    async def record_event(
        self,
        *,
        client_id: str,
        event_type: UsageEventType | str,
        payload: dict[str, object] | None = None,
        session_id: uuid.UUID | str | None = None,
    ) -> UsageEventRecord: ...


def _now_utc() -> datetime:
    return datetime.now(UTC)


def validate_usage_event_payload(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        _validate_payload_key(key, path=key): _validate_payload_value(
            value,
            path=key,
        )
        for key, value in payload.items()
    }


def build_usage_event_record(
    *,
    client_id: str,
    event_type: UsageEventType | str,
    payload: dict[str, object] | None = None,
    created_at: datetime,
    session_id: uuid.UUID | str | None = None,
) -> UsageEventRecord:
    return UsageEventRecord(
        client_id=client_id,
        session_id=_normalize_session_id(session_id),
        event_type=UsageEventType(event_type),
        payload=validate_usage_event_payload(payload or {}),
        created_at=created_at,
    )


class SQLAlchemyUsageEventRecorder:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Clock | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock or _now_utc

    async def record_event(
        self,
        *,
        client_id: str,
        event_type: UsageEventType | str,
        payload: dict[str, object] | None = None,
        session_id: uuid.UUID | str | None = None,
    ) -> UsageEventRecord:
        record = build_usage_event_record(
            client_id=client_id,
            session_id=session_id,
            event_type=event_type,
            payload=payload,
            created_at=self._clock(),
        )
        async with self._session_factory() as session:
            session.add(
                UsageEvent(
                    client_id=record.client_id,
                    session_id=record.session_id,
                    event_type=record.event_type.value,
                    payload=record.payload,
                    created_at=record.created_at,
                ),
            )
            await session.commit()
        return record


async def record_usage_event_best_effort(
    *,
    recorder: UsageEventRecorder | None,
    client_id: str,
    event_type: UsageEventType | str,
    payload: dict[str, object] | None = None,
    session_id: uuid.UUID | str | None = None,
) -> UsageEventRecord | None:
    if recorder is None:
        return None
    try:
        return await recorder.record_event(
            client_id=client_id,
            session_id=session_id,
            event_type=event_type,
            payload=payload,
        )
    except Exception as exc:
        logger.warning(
            "usage_event_write_failed",
            event_type=str(event_type),
            error_type=exc.__class__.__name__,
        )
        return None


def _normalize_session_id(session_id: uuid.UUID | str | None) -> uuid.UUID | None:
    if session_id is None:
        return None
    if isinstance(session_id, uuid.UUID):
        return session_id
    return uuid.UUID(session_id)


def _validate_payload_key(key: object, *, path: str) -> str:
    if not isinstance(key, str):
        msg = f"Usage event payload key at {path} must be a string"
        raise UnsafeUsageEventPayload(msg)
    normalized_key = key.lower()
    if any(part in normalized_key for part in _FORBIDDEN_PAYLOAD_KEY_PARTS):
        msg = f"Usage event payload key {path} is not allowed"
        raise UnsafeUsageEventPayload(msg)
    return key


def _validate_payload_value(value: object, *, path: str) -> object:
    if isinstance(value, _BINARY_TYPES):
        msg = f"Usage event payload value at {path} cannot be binary"
        raise UnsafeUsageEventPayload(msg)
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            _validate_payload_key(key, path=f"{path}.{key}"): _validate_payload_value(
                nested_value,
                path=f"{path}.{key}",
            )
            for key, nested_value in value.items()
        }
    if isinstance(value, Sequence):
        return [
            _validate_payload_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    msg = f"Usage event payload value at {path} is not JSON-safe"
    raise UnsafeUsageEventPayload(msg)
