from __future__ import annotations

import asyncio
import json
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from meeting_mvp_backend.archive_tokens import (
    build_archive_url as build_archive_url,
)
from meeting_mvp_backend.archive_tokens import (
    hash_archive_token as hash_archive_token,
)
from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.db.models import (
    AnonymousClient,
    CaptureMode,
    MeetingSession,
    MeetingSessionStatus,
    SourcePlatform,
    TranscriptSegment,
    TranslationStatus,
)
from meeting_mvp_backend.mock_providers import (
    DEFAULT_MOCK_PROVIDER_SCRIPT,
    MockProviderScript,
)
from meeting_mvp_backend.quota import QuotaDecision, QuotaDenialReason
from meeting_mvp_backend.stt_providers import (
    StreamingSttProvider,
    SttFinalEvent,
    SttInterimEvent,
)
from meeting_mvp_backend.translation_providers import (
    FinalTranslationContextSegment,
    FinalTranslationProvider,
    FinalTranslationRequest,
    InterimTranslationProvider,
)
from meeting_mvp_backend.translation_retries import (
    TranslationRetryJob,
    TranslationRetryQueue,
)
from meeting_mvp_backend.usage_events import (
    UsageEventRecorder,
    UsageEventType,
    record_usage_event_best_effort,
)
from meeting_mvp_backend.ws_messages import (
    AsrFinalMessage,
    AsrInterimMessage,
    AudioStatusMessage,
    ErrorMessage,
    HeartbeatMessage,
    KeySentenceUpdateMessage,
    QuotaUpdateMessage,
    SegmentFinalMessage,
    ServerMessage,
    SessionClosedMessage,
    SessionResumedMessage,
    SessionResumeMessage,
    SessionStartedMessage,
    SessionStartMessage,
    SessionStopMessage,
    TimelineItem,
    TimelineUpdateMessage,
    TranslationInterimMessage,
    WarningMessage,
    parse_client_message,
)

logger = structlog.get_logger(__name__)

Clock = Callable[[], datetime]
SttProviderFactory = Callable[[], StreamingSttProvider]
TranslationProviderFactory = Callable[[], InterimTranslationProvider]
FinalTranslationProviderFactory = Callable[[], FinalTranslationProvider]
USER_STOPPED_REASON = "user_stopped"
BROWSER_DISCONNECTED_REASON = "browser_disconnected"
INVALID_MESSAGE_REASON = "invalid_message"
SESSION_MISMATCH_REASON = "session_mismatch"
CLIENT_NOT_INITIALIZED_REASON = "client_not_initialized"
CONFIGURATION_ERROR_REASON = "configuration_error"
INTERNAL_ERROR_REASON = "internal_error"
QWEN_ASR_ERROR_REASON = "qwen_asr_error"
SESSION_RESUME_FAILED_REASON = "session_resume_failed"
QWEN_INTERIM_TRANSLATION_FAILED_CODE = "qwen_interim_translation_failed"
QWEN_FINAL_TRANSLATION_FAILED_CODE = "qwen_final_translation_failed"
MOCK_PROVIDER_STEP_DELAY_SECONDS = 0.001
INTERIM_TRANSLATION_MIN_INTERVAL_SECONDS = 1.5
FINAL_TRANSLATION_CONTEXT_SEGMENT_LIMIT = 5


class MeetingSessionRepository(Protocol):
    async def client_exists(self, client_id: str) -> bool: ...

    async def create_pending_session(
        self,
        *,
        session_id: uuid.UUID,
        client_id: str,
        archive_token_hash: str,
        source_platform: SourcePlatform,
        capture_mode: CaptureMode,
        retention_expires_at: datetime,
    ) -> None: ...

    async def mark_session_active(
        self,
        *,
        session_id: uuid.UUID,
        started_at: datetime,
    ) -> None: ...

    async def close_session(
        self,
        *,
        session_id: uuid.UUID,
        ended_at: datetime,
        duration_seconds: int,
        quota_seconds_consumed: int,
        status: MeetingSessionStatus,
    ) -> None: ...

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
    ) -> uuid.UUID: ...


class SessionQuotaService(Protocol):
    async def reserve_active_session(
        self,
        client_id: str,
        session_id: str,
    ) -> QuotaDecision: ...

    async def release_active_session(self, client_id: str, session_id: str) -> None: ...

    async def record_consumed_seconds(
        self,
        client_id: str,
        session_id: str,
        seconds: int,
    ) -> QuotaDecision: ...


@dataclass(slots=True)
class WebSocketSessionState:
    session_id: uuid.UUID
    client_id: str
    archive_token_hash: str
    archive_url: str
    remaining_seconds_today: int
    capture_mode: CaptureMode
    source_platform: SourcePlatform
    active_started_at: datetime | None = None
    has_audio: bool = False
    closed: bool = False
    mock_provider_task: asyncio.Task[None] | None = None
    stt_provider: StreamingSttProvider | None = None
    stt_provider_task: asyncio.Task[None] | None = None
    last_translation_request_at: datetime | None = None
    last_translated_interim_text: str | None = None
    pending_translation_text: str | None = None
    translation_provider: InterimTranslationProvider | None = None
    translation_task: asyncio.Task[None] | None = None
    final_translation_context: list[FinalTranslationContextSegment] = field(
        default_factory=list,
    )
    final_translation_provider: FinalTranslationProvider | None = None
    final_translation_task: asyncio.Task[None] | None = None
    pending_final_translations: list[SttFinalEvent] = field(default_factory=list)
    current_final_translation: SttFinalEvent | None = None
    archived_final_sequences: set[int] = field(default_factory=set)


@dataclass(slots=True)
class ResumableSessionRecord:
    state: WebSocketSessionState
    expires_at: datetime
    cleanup_task: asyncio.Task[None] | None = None


class InMemorySessionResumeRegistry:
    def __init__(self) -> None:
        self._records: dict[str, ResumableSessionRecord] = {}

    def put(self, record: ResumableSessionRecord) -> None:
        self._records[str(record.state.session_id)] = record

    def pop(
        self,
        *,
        archive_token_hash: str,
        client_id: str,
        now: datetime,
        session_id: str,
    ) -> ResumableSessionRecord | None:
        record = self._records.get(session_id)
        if record is None:
            return None
        if record.expires_at < now:
            self._records.pop(session_id, None)
            return None
        state = record.state
        if state.client_id != client_id:
            return None
        if state.archive_token_hash != archive_token_hash:
            return None
        self._records.pop(session_id, None)
        if record.cleanup_task is not None:
            record.cleanup_task.cancel()
        return record

    def expire(self, session_id: str, record: ResumableSessionRecord) -> bool:
        if self._records.get(session_id) is not record:
            return False
        self._records.pop(session_id, None)
        return True


DEFAULT_SESSION_RESUME_REGISTRY = InMemorySessionResumeRegistry()


class SQLAlchemyMeetingSessionRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def client_exists(self, client_id: str) -> bool:
        async with self._session_factory() as session:
            found_client_id = await session.scalar(
                select(AnonymousClient.client_id).where(
                    AnonymousClient.client_id == client_id,
                ),
            )
            return found_client_id is not None

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
        async with self._session_factory() as session:
            session.add(
                MeetingSession(
                    id=session_id,
                    client_id=client_id,
                    source_platform=source_platform,
                    capture_mode=capture_mode,
                    status=MeetingSessionStatus.PENDING_AUDIO,
                    archive_token_hash=archive_token_hash,
                    retention_expires_at=retention_expires_at,
                ),
            )
            await session.commit()

    async def mark_session_active(
        self,
        *,
        session_id: uuid.UUID,
        started_at: datetime,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(MeetingSession)
                .where(MeetingSession.id == session_id)
                .values(
                    started_at=started_at,
                    status=MeetingSessionStatus.ACTIVE,
                ),
            )
            await session.commit()

    async def close_session(
        self,
        *,
        session_id: uuid.UUID,
        ended_at: datetime,
        duration_seconds: int,
        quota_seconds_consumed: int,
        status: MeetingSessionStatus,
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(MeetingSession)
                .where(MeetingSession.id == session_id)
                .values(
                    ended_at=ended_at,
                    duration_seconds=duration_seconds,
                    quota_seconds_consumed=quota_seconds_consumed,
                    status=status,
                ),
            )
            await session.commit()

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
        async with self._session_factory() as session:
            session.add(
                TranscriptSegment(
                    id=segment_id,
                    session_id=session_id,
                    sequence=sequence,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    english_text_final=english_text_final,
                    chinese_text_final=chinese_text_final,
                    is_key_sentence=is_key_sentence,
                    asr_confidence=_decimal_confidence(asr_confidence),
                    translation_status=translation_status,
                ),
            )
            await session.commit()
        return segment_id


class WebSocketSessionOrchestrator:
    def __init__(
        self,
        *,
        repository: MeetingSessionRepository | None,
        quota_service: SessionQuotaService | None,
        settings: Settings,
        clock: Clock | None = None,
        configuration_error: str | None = None,
        resume_registry: InMemorySessionResumeRegistry | None = None,
        stt_provider_factory: SttProviderFactory | None = None,
        translation_min_interval_seconds: float = (
            INTERIM_TRANSLATION_MIN_INTERVAL_SECONDS
        ),
        translation_provider_factory: TranslationProviderFactory | None = None,
        final_translation_provider_factory: (
            FinalTranslationProviderFactory | None
        ) = None,
        translation_retry_queue: TranslationRetryQueue | None = None,
        usage_event_recorder: UsageEventRecorder | None = None,
    ) -> None:
        self._repository = repository
        self._quota_service = quota_service
        self._settings = settings
        self._clock = clock or _now_utc
        self._configuration_error = configuration_error
        self._resume_registry = resume_registry or DEFAULT_SESSION_RESUME_REGISTRY
        self._stt_provider_factory = stt_provider_factory
        self._translation_min_interval_seconds = translation_min_interval_seconds
        self._translation_provider_factory = translation_provider_factory
        self._final_translation_provider_factory = final_translation_provider_factory
        self._translation_retry_queue = translation_retry_queue
        self._usage_event_recorder = usage_event_recorder

    async def _record_usage_event(
        self,
        event_type: UsageEventType,
        *,
        client_id: str,
        payload: dict[str, object] | None = None,
        session_id: uuid.UUID | str | None = None,
    ) -> None:
        await record_usage_event_best_effort(
            recorder=self._usage_event_recorder,
            client_id=client_id,
            session_id=session_id,
            event_type=event_type,
            payload=payload,
        )

    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        if self._configuration_error is not None:
            await self._close_with_error(
                websocket=websocket,
                state=None,
                reason=CONFIGURATION_ERROR_REASON,
                message=self._configuration_error,
            )
            return

        state: WebSocketSessionState | None = None
        try:
            while True:
                raw_message = await websocket.receive()
                if raw_message["type"] == "websocket.disconnect":
                    return

                text_payload = raw_message.get("text")
                bytes_payload = raw_message.get("bytes")
                if text_payload is not None:
                    state = await self._handle_text_message(
                        websocket,
                        state,
                        text_payload,
                    )
                    if state is not None and state.closed:
                        return
                elif bytes_payload is not None:
                    await self._handle_binary_frame(websocket, state, bytes_payload)
        except WebSocketDisconnect:
            return
        except Exception as exc:
            logger.exception("websocket_session_unhandled_error")
            await self._close_with_error(
                websocket=websocket,
                state=state,
                reason=INTERNAL_ERROR_REASON,
                message=exc.__class__.__name__,
            )
        finally:
            if state is not None and not state.closed:
                await asyncio.shield(
                    self._pause_session_for_resume(state),
                )

    async def _handle_text_message(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState | None,
        text_payload: str,
    ) -> WebSocketSessionState | None:
        try:
            decoded_payload = json.loads(text_payload)
            message = parse_client_message(decoded_payload)
        except (json.JSONDecodeError, TypeError, ValidationError):
            await self._close_with_error(
                websocket=websocket,
                state=state,
                reason=INVALID_MESSAGE_REASON,
            )
            return _mark_closed(state)

        if isinstance(message, SessionStartMessage):
            if state is not None:
                await self._close_with_error(
                    websocket=websocket,
                    state=state,
                    reason=INVALID_MESSAGE_REASON,
                )
                return _mark_closed(state)
            return await self._start_session(websocket, message)

        if isinstance(message, SessionResumeMessage):
            if state is not None:
                await self._close_with_error(
                    websocket=websocket,
                    state=state,
                    reason=INVALID_MESSAGE_REASON,
                )
                return _mark_closed(state)
            return await self._resume_session(websocket, message)

        if state is None:
            await self._close_with_error(
                websocket=websocket,
                state=None,
                reason=INVALID_MESSAGE_REASON,
            )
            return None

        if isinstance(message, HeartbeatMessage):
            if not _matches_session(state, message.session_id):
                await self._close_with_error(
                    websocket=websocket,
                    state=state,
                    reason=SESSION_MISMATCH_REASON,
                )
                return _mark_closed(state)
            return state

        if isinstance(message, SessionStopMessage):
            if not _matches_session(state, message.session_id):
                await self._close_with_error(
                    websocket=websocket,
                    state=state,
                    reason=SESSION_MISMATCH_REASON,
                )
                return _mark_closed(state)
            await self._finalize_session(
                state,
                reason=USER_STOPPED_REASON,
                send_messages=True,
                websocket=websocket,
            )
            await _safe_close(websocket)
            state.closed = True
            return state

        await self._close_with_error(
            websocket=websocket,
            state=state,
            reason=INVALID_MESSAGE_REASON,
        )
        return _mark_closed(state)

    async def _start_session(
        self,
        websocket: WebSocket,
        message: SessionStartMessage,
    ) -> WebSocketSessionState | None:
        repository = _require_repository(self._repository)
        quota_service = _require_quota_service(self._quota_service)

        if not await repository.client_exists(message.client_id):
            await self._close_with_error(
                websocket=websocket,
                state=None,
                reason=CLIENT_NOT_INITIALIZED_REASON,
            )
            return None

        await self._record_usage_event(
            UsageEventType.CAPTURE_STARTED,
            client_id=message.client_id,
            payload={
                "capture_mode": message.capture_mode,
                "source_platform": message.source_platform,
            },
        )
        session_id = uuid.uuid4()
        quota_decision = await quota_service.reserve_active_session(
            message.client_id,
            str(session_id),
        )
        quota_reason = (
            quota_decision.reason.value
            if quota_decision.reason is not None
            else None
        )
        await self._record_usage_event(
            UsageEventType.QUOTA_CHECKED,
            client_id=message.client_id,
            payload={
                "allowed": quota_decision.allowed,
                "remaining_seconds_today": quota_decision.remaining_seconds_today,
                "reason": quota_reason,
            },
        )
        if not quota_decision.allowed:
            reason = (
                quota_decision.reason.value
                if quota_decision.reason is not None
                else INVALID_MESSAGE_REASON
            )
            denial_event_type = _usage_event_type_for_quota_denial(
                quota_decision.reason,
            )
            if denial_event_type is not None:
                await self._record_usage_event(
                    denial_event_type,
                    client_id=message.client_id,
                    payload={
                        "remaining_seconds_today": (
                            quota_decision.remaining_seconds_today
                        ),
                        "reason": reason,
                    },
                )
            await self._close_with_error(
                websocket=websocket,
                state=None,
                reason=reason,
            )
            return None

        archive_token = secrets.token_urlsafe(32)
        now = self._clock()
        try:
            await repository.create_pending_session(
                session_id=session_id,
                client_id=message.client_id,
                archive_token_hash=hash_archive_token(archive_token),
                source_platform=SourcePlatform(message.source_platform),
                capture_mode=CaptureMode(message.capture_mode),
                retention_expires_at=now
                + timedelta(days=self._settings.archive_retention_days),
            )
        except Exception:
            await quota_service.release_active_session(
                message.client_id,
                str(session_id),
            )
            raise

        await _send_server_message(
            websocket,
            SessionStartedMessage(
                type="session_started",
                session_id=str(session_id),
                archive_token=archive_token,
                archive_url=build_archive_url(
                    self._settings.public_base_url,
                    session_id,
                    archive_token,
                ),
                remaining_seconds_today=quota_decision.remaining_seconds_today,
            ),
        )
        archive_url = build_archive_url(
            self._settings.public_base_url,
            session_id,
            archive_token,
        )
        source_platform = SourcePlatform(message.source_platform)
        capture_mode = CaptureMode(message.capture_mode)
        await self._record_usage_event(
            UsageEventType.SESSION_STARTED,
            client_id=message.client_id,
            session_id=session_id,
            payload={
                "capture_mode": capture_mode.value,
                "remaining_seconds_today": quota_decision.remaining_seconds_today,
                "source_platform": source_platform.value,
            },
        )
        return WebSocketSessionState(
            session_id=session_id,
            client_id=message.client_id,
            archive_token_hash=hash_archive_token(archive_token),
            archive_url=archive_url,
            remaining_seconds_today=quota_decision.remaining_seconds_today,
            capture_mode=capture_mode,
            source_platform=source_platform,
        )

    async def _resume_session(
        self,
        websocket: WebSocket,
        message: SessionResumeMessage,
    ) -> WebSocketSessionState | None:
        record = self._resume_registry.pop(
            archive_token_hash=hash_archive_token(message.archive_token),
            client_id=message.client_id,
            now=self._clock(),
            session_id=message.session_id,
        )
        if record is None:
            await self._close_with_error(
                websocket=websocket,
                state=None,
                reason=SESSION_RESUME_FAILED_REASON,
                message="Session cannot be resumed",
            )
            return None

        state = record.state
        state.closed = False
        state.mock_provider_task = None
        state.stt_provider = None
        state.stt_provider_task = None
        state.pending_translation_text = None
        state.translation_provider = None
        state.translation_task = None
        state.pending_final_translations.clear()
        state.current_final_translation = None
        state.final_translation_provider = None
        state.final_translation_task = None
        await _send_server_message(
            websocket,
            SessionResumedMessage(
                type="session_resumed",
                session_id=str(state.session_id),
                archive_url=state.archive_url,
                remaining_seconds_today=state.remaining_seconds_today,
            ),
        )
        return state

    async def _handle_binary_frame(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState | None,
        payload: bytes,
    ) -> None:
        if state is None:
            await self._close_with_error(
                websocket=websocket,
                state=None,
                reason=INVALID_MESSAGE_REASON,
            )
            return

        if payload == b"":
            return

        if state.has_audio:
            if (
                state.stt_provider is None
                and self._stt_provider_factory is not None
            ):
                self._start_stt_provider(websocket, state)
            if state.stt_provider is not None:
                await state.stt_provider.send_audio(payload)
            return

        await self._activate_session_for_audio(websocket, state)
        if state.stt_provider is not None:
            await state.stt_provider.send_audio(payload)

    async def _activate_session_for_audio(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState,
    ) -> None:
        repository = _require_repository(self._repository)
        active_at = self._clock()
        await repository.mark_session_active(
            session_id=state.session_id,
            started_at=active_at,
        )
        state.has_audio = True
        state.active_started_at = active_at
        await self._record_usage_event(
            UsageEventType.AUDIO_DETECTED,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={
                "capture_mode": state.capture_mode.value,
                "source_platform": state.source_platform.value,
            },
        )
        await _send_server_message(
            websocket,
            AudioStatusMessage(type="audio_status", has_audio=True, level=None),
        )
        if self._stt_provider_factory is None:
            state.mock_provider_task = asyncio.create_task(
                self._run_mock_provider_pipeline(websocket, state),
            )
            return

        self._start_stt_provider(websocket, state)

    def _start_stt_provider(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState,
    ) -> None:
        stt_provider_factory = self._stt_provider_factory
        if stt_provider_factory is None:
            return
        state.stt_provider = stt_provider_factory()
        state.stt_provider_task = asyncio.create_task(
            self._run_stt_provider_pipeline(websocket, state),
        )

    async def _run_stt_provider_pipeline(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState,
    ) -> None:
        provider = state.stt_provider
        if provider is None:
            return
        try:
            async for event in provider.events():
                if isinstance(event, SttInterimEvent):
                    await self._record_usage_event(
                        UsageEventType.ASR_INTERIM_RECEIVED,
                        client_id=state.client_id,
                        session_id=state.session_id,
                        payload={"text_length": len(event.text)},
                    )
                    await _send_server_message(
                        websocket,
                        AsrInterimMessage(type="asr_interim", text=event.text),
                    )
                    self._schedule_interim_translation(websocket, state, event.text)
                elif isinstance(event, SttFinalEvent):
                    await self._record_usage_event(
                        UsageEventType.ASR_FINAL_RECEIVED,
                        client_id=state.client_id,
                        session_id=state.session_id,
                        payload={
                            "confidence_present": event.confidence is not None,
                            "end_ms": event.end_ms,
                            "sequence": event.sequence,
                            "start_ms": event.start_ms,
                            "text_length": len(event.text),
                        },
                    )
                    await _send_server_message(
                        websocket,
                        AsrFinalMessage(
                            type="asr_final",
                            sequence=event.sequence,
                            start_ms=event.start_ms,
                            end_ms=event.end_ms,
                            text=event.text,
                            confidence=event.confidence,
                        ),
                    )
                    self._schedule_final_translation(websocket, state, event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "qwen_asr_stream_failed",
                error_type=exc.__class__.__name__,
            )
            await self._record_usage_event(
                UsageEventType.PROVIDER_ERROR,
                client_id=state.client_id,
                session_id=state.session_id,
                payload={
                    "code": QWEN_ASR_ERROR_REASON,
                    "error_type": exc.__class__.__name__,
                    "provider": "qwen_realtime_asr",
                },
            )
            await self._close_with_error(
                websocket=websocket,
                state=state,
                reason=QWEN_ASR_ERROR_REASON,
                message=exc.__class__.__name__,
            )

    def _schedule_final_translation(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState,
        event: SttFinalEvent,
    ) -> None:
        if self._final_translation_provider_factory is None:
            return
        if " ".join(event.text.split()) == "":
            return

        state.pending_final_translations.append(event)
        task = state.final_translation_task
        if task is None or task.done():
            state.final_translation_task = asyncio.create_task(
                self._run_final_translation_loop(websocket, state),
            )

    async def _run_final_translation_loop(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState,
    ) -> None:
        while state.pending_final_translations and not state.closed:
            event = state.pending_final_translations.pop(0)
            if event.sequence in state.archived_final_sequences:
                continue

            state.current_final_translation = event
            try:
                provider = state.final_translation_provider
                if provider is None:
                    provider_factory = self._final_translation_provider_factory
                    if provider_factory is None:
                        return
                    provider = provider_factory()
                    state.final_translation_provider = provider

                translated_text = await provider.translate_final(
                    FinalTranslationRequest(
                        sequence=event.sequence,
                        text=event.text,
                        context=tuple(
                            state.final_translation_context[
                                -FINAL_TRANSLATION_CONTEXT_SEGMENT_LIMIT:
                            ],
                        ),
                    ),
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "qwen_final_translation_failed",
                    error_type=exc.__class__.__name__,
                    session_id=str(state.session_id),
                    sequence=event.sequence,
                )
                await self._record_usage_event(
                    UsageEventType.PROVIDER_ERROR,
                    client_id=state.client_id,
                    session_id=state.session_id,
                    payload={
                        "code": QWEN_FINAL_TRANSLATION_FAILED_CODE,
                        "error_type": exc.__class__.__name__,
                        "provider": "qwen_final_translation",
                        "sequence": event.sequence,
                    },
                )
                await self._archive_failed_final_translation(
                    websocket=websocket,
                    state=state,
                    event=event,
                    send_warning=True,
                )
                state.current_final_translation = None
                continue

            translated_text = translated_text.strip()
            if translated_text == "":
                await self._record_usage_event(
                    UsageEventType.PROVIDER_ERROR,
                    client_id=state.client_id,
                    session_id=state.session_id,
                    payload={
                        "code": QWEN_FINAL_TRANSLATION_FAILED_CODE,
                        "error_type": "EmptyTranslation",
                        "provider": "qwen_final_translation",
                        "sequence": event.sequence,
                    },
                )
                await self._archive_failed_final_translation(
                    websocket=websocket,
                    state=state,
                    event=event,
                    send_warning=True,
                )
                state.current_final_translation = None
                continue

            await self._record_usage_event(
                UsageEventType.TRANSLATION_FINAL_COMPLETED,
                client_id=state.client_id,
                session_id=state.session_id,
                payload={
                    "chinese_text_length": len(translated_text),
                    "english_text_length": len(event.text),
                    "sequence": event.sequence,
                },
            )
            await self._archive_completed_final_translation(
                websocket=websocket,
                state=state,
                event=event,
                translated_text=translated_text,
            )
            state.current_final_translation = None

    async def _archive_completed_final_translation(
        self,
        *,
        websocket: WebSocket | None,
        state: WebSocketSessionState,
        event: SttFinalEvent,
        translated_text: str,
    ) -> None:
        if event.sequence in state.archived_final_sequences:
            return

        repository = _require_repository(self._repository)
        segment_id = await repository.create_transcript_segment(
            session_id=state.session_id,
            sequence=event.sequence,
            start_ms=event.start_ms,
            end_ms=event.end_ms,
            english_text_final=event.text,
            chinese_text_final=translated_text,
            is_key_sentence=False,
            translation_status=TranslationStatus.COMPLETED,
            asr_confidence=event.confidence,
        )
        state.archived_final_sequences.add(event.sequence)
        await self._record_usage_event(
            UsageEventType.SEGMENT_ARCHIVED,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={
                "chinese_text_length": len(translated_text),
                "end_ms": event.end_ms,
                "english_text_length": len(event.text),
                "segment_id": str(segment_id),
                "sequence": event.sequence,
                "start_ms": event.start_ms,
                "translation_status": TranslationStatus.COMPLETED.value,
            },
        )
        state.final_translation_context.append(
            FinalTranslationContextSegment(
                sequence=event.sequence,
                english_text_final=event.text,
                chinese_text_final=translated_text,
            ),
        )
        await _send_server_message(
            websocket,
            SegmentFinalMessage(
                type="segment_final",
                segment_id=str(segment_id),
                sequence=event.sequence,
                start_ms=event.start_ms,
                end_ms=event.end_ms,
                english_text_final=event.text,
                chinese_text_final=translated_text,
            ),
        )

    async def _archive_failed_final_translation(
        self,
        *,
        websocket: WebSocket | None,
        state: WebSocketSessionState,
        event: SttFinalEvent,
        send_warning: bool,
    ) -> None:
        if event.sequence in state.archived_final_sequences:
            return

        repository = _require_repository(self._repository)
        segment_id = await repository.create_transcript_segment(
            session_id=state.session_id,
            sequence=event.sequence,
            start_ms=event.start_ms,
            end_ms=event.end_ms,
            english_text_final=event.text,
            chinese_text_final="",
            is_key_sentence=False,
            translation_status=TranslationStatus.FAILED,
            asr_confidence=event.confidence,
        )
        state.archived_final_sequences.add(event.sequence)
        await self._record_usage_event(
            UsageEventType.SEGMENT_ARCHIVED,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={
                "chinese_text_length": 0,
                "end_ms": event.end_ms,
                "english_text_length": len(event.text),
                "segment_id": str(segment_id),
                "sequence": event.sequence,
                "start_ms": event.start_ms,
                "translation_status": TranslationStatus.FAILED.value,
            },
        )
        await self._enqueue_failed_final_translation_retry(
            segment_id=segment_id,
            state=state,
        )
        if send_warning:
            await _send_server_message(
                websocket,
                WarningMessage(
                    type="warning",
                    code=QWEN_FINAL_TRANSLATION_FAILED_CODE,
                    message="中文正式翻译失败，英文 final 已归档待重试。",
                ),
            )

    async def _enqueue_failed_final_translation_retry(
        self,
        *,
        segment_id: uuid.UUID,
        state: WebSocketSessionState,
    ) -> None:
        if self._translation_retry_queue is None:
            return
        try:
            await self._translation_retry_queue.enqueue(
                TranslationRetryJob(
                    due_at=self._clock(),
                    segment_id=segment_id,
                    session_id=state.session_id,
                ),
            )
        except Exception as exc:
            logger.warning(
                "translation_retry_enqueue_failed",
                error_type=exc.__class__.__name__,
                segment_id=str(segment_id),
                session_id=str(state.session_id),
            )

    def _schedule_interim_translation(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState,
        text: str,
    ) -> None:
        if self._translation_provider_factory is None:
            return

        normalized_text = " ".join(text.split())
        if normalized_text == "":
            return
        if normalized_text == state.last_translated_interim_text:
            return
        if normalized_text == state.pending_translation_text:
            return

        state.pending_translation_text = normalized_text
        task = state.translation_task
        if task is None or task.done():
            state.translation_task = asyncio.create_task(
                self._run_interim_translation_loop(websocket, state),
            )

    async def _run_interim_translation_loop(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState,
    ) -> None:
        while state.pending_translation_text is not None and not state.closed:
            text = state.pending_translation_text
            state.pending_translation_text = None
            if text == state.last_translated_interim_text:
                continue

            await self._wait_for_interim_translation_slot(state)
            if state.closed:
                return

            provider = state.translation_provider
            if provider is None:
                provider_factory = self._translation_provider_factory
                if provider_factory is None:
                    return
                provider = provider_factory()
                state.translation_provider = provider

            state.last_translation_request_at = self._clock()
            await self._record_usage_event(
                UsageEventType.TRANSLATION_INTERIM_REQUESTED,
                client_id=state.client_id,
                session_id=state.session_id,
                payload={
                    "min_interval_seconds": self._translation_min_interval_seconds,
                    "text_length": len(text),
                },
            )
            try:
                translated_text = await provider.translate_interim(text)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "qwen_interim_translation_failed",
                    error_type=exc.__class__.__name__,
                    session_id=str(state.session_id),
                )
                await self._record_usage_event(
                    UsageEventType.PROVIDER_ERROR,
                    client_id=state.client_id,
                    session_id=state.session_id,
                    payload={
                        "code": QWEN_INTERIM_TRANSLATION_FAILED_CODE,
                        "error_type": exc.__class__.__name__,
                        "provider": "qwen_interim_translation",
                    },
                )
                await _send_server_message(
                    websocket,
                    WarningMessage(
                        type="warning",
                        code=QWEN_INTERIM_TRANSLATION_FAILED_CODE,
                        message="中文临时理解暂时不可用，英文转写会继续。",
                    ),
                )
                continue

            translated_text = translated_text.strip()
            if translated_text == "":
                continue
            state.last_translated_interim_text = text
            await _send_server_message(
                websocket,
                TranslationInterimMessage(
                    type="translation_interim",
                    text=translated_text,
                ),
            )

    async def _wait_for_interim_translation_slot(
        self,
        state: WebSocketSessionState,
    ) -> None:
        last_request_at = state.last_translation_request_at
        if last_request_at is None:
            return
        elapsed_seconds = (self._clock() - last_request_at).total_seconds()
        remaining_seconds = self._translation_min_interval_seconds - elapsed_seconds
        if remaining_seconds > 0:
            await asyncio.sleep(remaining_seconds)

    async def _run_mock_provider_pipeline(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState,
        script: MockProviderScript = DEFAULT_MOCK_PROVIDER_SCRIPT,
    ) -> None:
        await asyncio.sleep(MOCK_PROVIDER_STEP_DELAY_SECONDS)
        await self._record_usage_event(
            UsageEventType.ASR_INTERIM_RECEIVED,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={"text_length": len(script.english_interim)},
        )
        await _send_server_message(
            websocket,
            AsrInterimMessage(type="asr_interim", text=script.english_interim),
        )
        await asyncio.sleep(MOCK_PROVIDER_STEP_DELAY_SECONDS)
        await self._record_usage_event(
            UsageEventType.PROVIDER_ERROR,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={
                "code": script.warning_code,
                "error_type": "MockProviderWarning",
                "provider": "mock_provider",
            },
        )
        await _send_server_message(
            websocket,
            WarningMessage(
                type="warning",
                code=script.warning_code,
                message=script.warning_message,
            ),
        )
        await asyncio.sleep(MOCK_PROVIDER_STEP_DELAY_SECONDS)
        await self._record_usage_event(
            UsageEventType.TRANSLATION_INTERIM_REQUESTED,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={
                "min_interval_seconds": 0,
                "text_length": len(script.english_interim),
            },
        )
        await _send_server_message(
            websocket,
            TranslationInterimMessage(
                type="translation_interim",
                text=script.chinese_interim,
            ),
        )
        await asyncio.sleep(MOCK_PROVIDER_STEP_DELAY_SECONDS)

        repository = _require_repository(self._repository)
        final_segment = script.final_segment
        await self._record_usage_event(
            UsageEventType.ASR_FINAL_RECEIVED,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={
                "confidence_present": False,
                "end_ms": final_segment.end_ms,
                "sequence": final_segment.sequence,
                "start_ms": final_segment.start_ms,
                "text_length": len(final_segment.english_text_final),
            },
        )
        await self._record_usage_event(
            UsageEventType.TRANSLATION_FINAL_COMPLETED,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={
                "chinese_text_length": len(final_segment.chinese_text_final),
                "english_text_length": len(final_segment.english_text_final),
                "sequence": final_segment.sequence,
            },
        )
        segment_id = await repository.create_transcript_segment(
            session_id=state.session_id,
            sequence=final_segment.sequence,
            start_ms=final_segment.start_ms,
            end_ms=final_segment.end_ms,
            english_text_final=final_segment.english_text_final,
            chinese_text_final=final_segment.chinese_text_final,
            is_key_sentence=final_segment.is_key_sentence,
        )
        await self._record_usage_event(
            UsageEventType.SEGMENT_ARCHIVED,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={
                "chinese_text_length": len(final_segment.chinese_text_final),
                "end_ms": final_segment.end_ms,
                "english_text_length": len(final_segment.english_text_final),
                "segment_id": str(segment_id),
                "sequence": final_segment.sequence,
                "start_ms": final_segment.start_ms,
                "translation_status": TranslationStatus.COMPLETED.value,
            },
        )
        await _send_server_message(
            websocket,
            SegmentFinalMessage(
                type="segment_final",
                segment_id=str(segment_id),
                sequence=final_segment.sequence,
                start_ms=final_segment.start_ms,
                end_ms=final_segment.end_ms,
                english_text_final=final_segment.english_text_final,
                chinese_text_final=final_segment.chinese_text_final,
            ),
        )
        await asyncio.sleep(MOCK_PROVIDER_STEP_DELAY_SECONDS)
        await _send_server_message(
            websocket,
            KeySentenceUpdateMessage(
                type="key_sentence_update",
                text=final_segment.chinese_text_final,
            ),
        )
        await asyncio.sleep(MOCK_PROVIDER_STEP_DELAY_SECONDS)
        await _send_server_message(
            websocket,
            TimelineUpdateMessage(
                type="timeline_update",
                items=[
                    TimelineItem(
                        id=f"segment-{segment_id}",
                        item_type="segment_final",
                        timestamp_ms=final_segment.end_ms,
                        text=final_segment.chinese_text_final,
                        segment_id=str(segment_id),
                    ),
                ],
            ),
        )

    async def _finalize_session(
        self,
        state: WebSocketSessionState | None,
        *,
        reason: str,
        send_messages: bool,
        websocket: WebSocket | None,
    ) -> None:
        if state is None or state.closed:
            return

        await _cancel_mock_provider_task(state)
        await _cancel_translation_task(state)
        await _close_translation_provider(state)
        await _close_stt_provider(state)
        await _cancel_stt_provider_task(state)
        await self._cancel_final_translation_task(
            state,
            archive_pending_as_failed=True,
        )
        await _close_final_translation_provider(state)
        repository = _require_repository(self._repository)
        quota_service = _require_quota_service(self._quota_service)
        ended_at = self._clock()
        duration_seconds = _elapsed_seconds(state.active_started_at, ended_at)
        remaining_seconds_today = state.remaining_seconds_today
        if duration_seconds > 0:
            quota_decision = await quota_service.record_consumed_seconds(
                client_id=state.client_id,
                session_id=str(state.session_id),
                seconds=duration_seconds,
            )
            remaining_seconds_today = quota_decision.remaining_seconds_today
            state.remaining_seconds_today = remaining_seconds_today

        await repository.close_session(
            session_id=state.session_id,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            quota_seconds_consumed=duration_seconds,
            status=_status_for_close_reason(reason),
        )
        await quota_service.release_active_session(
            state.client_id,
            str(state.session_id),
        )
        await self._record_usage_event(
            UsageEventType.SESSION_CLOSED,
            client_id=state.client_id,
            session_id=state.session_id,
            payload={
                "duration_seconds": duration_seconds,
                "quota_seconds_consumed": duration_seconds,
                "reason": reason,
                "remaining_seconds_today": remaining_seconds_today,
            },
        )

        if send_messages:
            await _send_server_message(
                websocket,
                QuotaUpdateMessage(
                    type="quota_update",
                    remaining_seconds_today=remaining_seconds_today,
                ),
            )
            await _send_server_message(
                websocket,
                SessionClosedMessage(type="session_closed", reason=reason),
            )
        state.closed = True

    async def _close_with_error(
        self,
        *,
        websocket: WebSocket,
        state: WebSocketSessionState | None,
        reason: str,
        message: str | None = None,
    ) -> None:
        await _send_server_message(
            websocket,
            ErrorMessage(type="error", code=reason, message=message),
        )
        await self._finalize_session(
            state,
            reason=reason,
            send_messages=False,
            websocket=None,
        )
        await _send_server_message(
            websocket,
            SessionClosedMessage(type="session_closed", reason=reason),
        )
        await _safe_close(websocket)
        _mark_closed(state)

    async def _pause_session_for_resume(
        self,
        state: WebSocketSessionState,
    ) -> None:
        await self._cancel_final_translation_task(
            state,
            archive_pending_as_failed=True,
        )
        await _close_final_translation_provider(state)
        mock_provider_task = state.mock_provider_task
        stt_provider_task = state.stt_provider_task
        stt_provider = state.stt_provider
        translation_provider = state.translation_provider
        translation_task = state.translation_task
        state.mock_provider_task = None
        state.stt_provider = None
        state.stt_provider_task = None
        state.pending_translation_text = None
        state.translation_provider = None
        state.translation_task = None
        state.final_translation_provider = None
        state.final_translation_task = None
        state.current_final_translation = None
        state.pending_final_translations.clear()
        state.closed = True
        expires_at = self._clock() + timedelta(
            seconds=self._settings.session_resume_grace_seconds,
        )
        record = ResumableSessionRecord(state=state, expires_at=expires_at)
        record.cleanup_task = asyncio.create_task(
            self._expire_resumable_session(record),
        )
        self._resume_registry.put(record)
        await _cancel_task(mock_provider_task)
        await _cancel_task(translation_task)
        await _close_provider(translation_provider)
        await _cancel_task(stt_provider_task)
        await _close_provider(stt_provider)

    async def _cancel_final_translation_task(
        self,
        state: WebSocketSessionState,
        *,
        archive_pending_as_failed: bool,
    ) -> None:
        pending_events: list[SttFinalEvent] = []
        if archive_pending_as_failed and state.current_final_translation is not None:
            pending_events.append(state.current_final_translation)
        if archive_pending_as_failed:
            pending_events.extend(state.pending_final_translations)
        state.pending_final_translations.clear()

        await _cancel_task(state.final_translation_task)
        state.final_translation_task = None
        state.current_final_translation = None

        for event in pending_events:
            await self._archive_failed_final_translation(
                websocket=None,
                state=state,
                event=event,
                send_warning=False,
            )

    async def _expire_resumable_session(
        self,
        record: ResumableSessionRecord,
    ) -> None:
        delay_seconds = max(
            (record.expires_at - self._clock()).total_seconds(),
            0,
        )
        try:
            await asyncio.sleep(delay_seconds)
        except asyncio.CancelledError:
            return
        session_id = str(record.state.session_id)
        if not self._resume_registry.expire(session_id, record):
            return
        record.state.closed = False
        await self._finalize_session(
            record.state,
            reason=BROWSER_DISCONNECTED_REASON,
            send_messages=False,
            websocket=None,
        )


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _elapsed_seconds(started_at: datetime | None, ended_at: datetime) -> int:
    if started_at is None:
        return 0
    return max(int((ended_at - started_at).total_seconds()), 0)


def _decimal_confidence(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _matches_session(state: WebSocketSessionState, session_id: str) -> bool:
    return str(state.session_id) == session_id


def _mark_closed(
    state: WebSocketSessionState | None,
) -> WebSocketSessionState | None:
    if state is not None:
        state.closed = True
    return state


def _status_for_close_reason(reason: str) -> MeetingSessionStatus:
    if reason == USER_STOPPED_REASON:
        return MeetingSessionStatus.ENDED
    if reason == BROWSER_DISCONNECTED_REASON:
        return MeetingSessionStatus.ERROR
    return MeetingSessionStatus.ERROR


def _usage_event_type_for_quota_denial(
    reason: QuotaDenialReason | None,
) -> UsageEventType | None:
    if reason is QuotaDenialReason.DAILY_QUOTA_EXHAUSTED:
        return UsageEventType.QUOTA_EXHAUSTED
    if reason is QuotaDenialReason.BUDGET_FUSE_TRIGGERED:
        return UsageEventType.BUDGET_FUSE_TRIGGERED
    return None


def _require_repository(
    repository: MeetingSessionRepository | None,
) -> MeetingSessionRepository:
    if repository is None:
        msg = "meeting session repository is not configured"
        raise RuntimeError(msg)
    return repository


def _require_quota_service(
    quota_service: SessionQuotaService | None,
) -> SessionQuotaService:
    if quota_service is None:
        msg = "quota service is not configured"
        raise RuntimeError(msg)
    return quota_service


async def _send_server_message(
    websocket: WebSocket | None,
    message: ServerMessage,
) -> None:
    if websocket is None:
        return
    await websocket.send_json(message.model_dump(mode="json"))


async def _cancel_mock_provider_task(state: WebSocketSessionState) -> None:
    await _cancel_task(state.mock_provider_task)


async def _cancel_stt_provider_task(state: WebSocketSessionState) -> None:
    await _cancel_task(state.stt_provider_task)


async def _cancel_translation_task(state: WebSocketSessionState) -> None:
    await _cancel_task(state.translation_task)


async def _cancel_task(task: asyncio.Task[None] | None) -> None:
    if task is None or task.done() or task is asyncio.current_task():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return


async def _close_stt_provider(state: WebSocketSessionState) -> None:
    await _close_provider(state.stt_provider)


async def _close_translation_provider(state: WebSocketSessionState) -> None:
    await _close_provider(state.translation_provider)


async def _close_final_translation_provider(state: WebSocketSessionState) -> None:
    await _close_provider(state.final_translation_provider)


async def _close_provider(
    provider: (
        StreamingSttProvider
        | InterimTranslationProvider
        | FinalTranslationProvider
        | None
    ),
) -> None:
    if provider is None:
        return
    await provider.close()


async def _safe_close(websocket: WebSocket) -> None:
    try:
        await websocket.close(code=1000)
    except RuntimeError:
        return
