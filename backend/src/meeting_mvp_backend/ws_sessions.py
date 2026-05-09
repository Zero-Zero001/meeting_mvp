from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import quote

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from meeting_mvp_backend.quota import QuotaDecision
from meeting_mvp_backend.ws_messages import (
    AsrInterimMessage,
    AudioStatusMessage,
    ErrorMessage,
    HeartbeatMessage,
    KeySentenceUpdateMessage,
    QuotaUpdateMessage,
    SegmentFinalMessage,
    ServerMessage,
    SessionClosedMessage,
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
USER_STOPPED_REASON = "user_stopped"
BROWSER_DISCONNECTED_REASON = "browser_disconnected"
INVALID_MESSAGE_REASON = "invalid_message"
SESSION_MISMATCH_REASON = "session_mismatch"
CLIENT_NOT_INITIALIZED_REASON = "client_not_initialized"
CONFIGURATION_ERROR_REASON = "configuration_error"
INTERNAL_ERROR_REASON = "internal_error"
MOCK_PROVIDER_STEP_DELAY_SECONDS = 0.001


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
    remaining_seconds_today: int
    active_started_at: datetime | None = None
    has_audio: bool = False
    closed: bool = False
    mock_provider_task: asyncio.Task[None] | None = None


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
                    translation_status=TranslationStatus.COMPLETED,
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
    ) -> None:
        self._repository = repository
        self._quota_service = quota_service
        self._settings = settings
        self._clock = clock or _now_utc
        self._configuration_error = configuration_error

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
                    self._finalize_session(
                        state,
                        reason=BROWSER_DISCONNECTED_REASON,
                        send_messages=False,
                        websocket=None,
                    ),
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

        session_id = uuid.uuid4()
        quota_decision = await quota_service.reserve_active_session(
            message.client_id,
            str(session_id),
        )
        if not quota_decision.allowed:
            reason = (
                quota_decision.reason.value
                if quota_decision.reason is not None
                else INVALID_MESSAGE_REASON
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
        return WebSocketSessionState(
            session_id=session_id,
            client_id=message.client_id,
            remaining_seconds_today=quota_decision.remaining_seconds_today,
        )

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

        if payload == b"" or state.has_audio:
            return

        repository = _require_repository(self._repository)
        active_at = self._clock()
        await repository.mark_session_active(
            session_id=state.session_id,
            started_at=active_at,
        )
        state.has_audio = True
        state.active_started_at = active_at
        await _send_server_message(
            websocket,
            AudioStatusMessage(type="audio_status", has_audio=True, level=None),
        )
        state.mock_provider_task = asyncio.create_task(
            self._run_mock_provider_pipeline(websocket, state),
        )

    async def _run_mock_provider_pipeline(
        self,
        websocket: WebSocket,
        state: WebSocketSessionState,
        script: MockProviderScript = DEFAULT_MOCK_PROVIDER_SCRIPT,
    ) -> None:
        await asyncio.sleep(MOCK_PROVIDER_STEP_DELAY_SECONDS)
        await _send_server_message(
            websocket,
            AsrInterimMessage(type="asr_interim", text=script.english_interim),
        )
        await asyncio.sleep(MOCK_PROVIDER_STEP_DELAY_SECONDS)
        await _send_server_message(
            websocket,
            WarningMessage(
                type="warning",
                code=script.warning_code,
                message=script.warning_message,
            ),
        )
        await asyncio.sleep(MOCK_PROVIDER_STEP_DELAY_SECONDS)
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
        segment_id = await repository.create_transcript_segment(
            session_id=state.session_id,
            sequence=final_segment.sequence,
            start_ms=final_segment.start_ms,
            end_ms=final_segment.end_ms,
            english_text_final=final_segment.english_text_final,
            chinese_text_final=final_segment.chinese_text_final,
            is_key_sentence=final_segment.is_key_sentence,
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


def hash_archive_token(archive_token: str) -> str:
    return hashlib.sha256(archive_token.encode("utf-8")).hexdigest()


def build_archive_url(
    public_base_url: str | None,
    session_id: uuid.UUID,
    archive_token: str,
) -> str:
    archive_path = f"/archive/{session_id}?token={quote(archive_token, safe='')}"
    if public_base_url is None or public_base_url.strip() == "":
        return archive_path
    return f"{public_base_url.rstrip('/')}{archive_path}"


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _elapsed_seconds(started_at: datetime | None, ended_at: datetime) -> int:
    if started_at is None:
        return 0
    return max(int((ended_at - started_at).total_seconds()), 0)


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
    task = state.mock_provider_task
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        return


async def _safe_close(websocket: WebSocket) -> None:
    try:
        await websocket.close(code=1000)
    except RuntimeError:
        return
