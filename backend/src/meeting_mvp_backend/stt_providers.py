from __future__ import annotations

import asyncio
import base64
import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from websockets.asyncio.client import connect

from meeting_mvp_backend.config import Settings

QWEN_ASR_SAMPLE_RATE_HZ = 16000
QWEN_ASR_CHANNELS = 1
QWEN_ASR_BYTES_PER_SAMPLE = 2
QWEN_ASR_DEFAULT_AUDIO_FORMAT = "pcm"
QWEN_ASR_DEFAULT_MODEL = "qwen3-asr-flash-realtime"
QWEN_ASR_CLOSE_TIMEOUT_SECONDS = 8.0
QWEN_ASR_SILENCE_FLUSH_DELAY_SECONDS = 0.6
QWEN_ASR_SILENCE_FLUSH_DURATION_MS = 800
QWEN_ASR_FRAME_DURATION_MS = 100


@dataclass(frozen=True, slots=True)
class SttInterimEvent:
    text: str


@dataclass(frozen=True, slots=True)
class SttFinalEvent:
    sequence: int
    start_ms: int
    end_ms: int
    text: str
    confidence: float | None


type SttEvent = SttInterimEvent | SttFinalEvent


class StreamingSttProvider(Protocol):
    async def send_audio(self, payload: bytes) -> None: ...

    def events(self) -> AsyncIterator[SttEvent]: ...

    async def close(self) -> None: ...


class QwenRealtimeWebSocket(Protocol):
    async def send(self, message: str) -> None: ...

    def __aiter__(self) -> AsyncIterator[str | bytes]: ...

    async def close(self) -> None: ...


QwenRealtimeWebSocketFactory = Callable[
    [str, dict[str, str]],
    Awaitable[QwenRealtimeWebSocket],
]


class QwenRealtimeAsrProvider:
    def __init__(
        self,
        *,
        settings: Settings,
        websocket_factory: QwenRealtimeWebSocketFactory | None = None,
        close_timeout_seconds: float = QWEN_ASR_CLOSE_TIMEOUT_SECONDS,
        silence_flush_delay_seconds: float = QWEN_ASR_SILENCE_FLUSH_DELAY_SECONDS,
        silence_flush_duration_ms: int = QWEN_ASR_SILENCE_FLUSH_DURATION_MS,
    ) -> None:
        self._settings = settings
        self._websocket_factory = websocket_factory or _connect_qwen_websocket
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._closed = False
        self._websocket: QwenRealtimeWebSocket | None = None
        self._finished_event = asyncio.Event()
        self._last_final_end_ms = 0
        self._sequence = 0
        self._queued_audio_bytes = 0
        self._close_timeout_seconds = close_timeout_seconds
        self._silence_flush_delay_seconds = silence_flush_delay_seconds
        self._silence_flush_duration_ms = silence_flush_duration_ms
        self._silence_flush_task: asyncio.Task[None] | None = None

    async def send_audio(self, payload: bytes) -> None:
        if self._closed or payload == b"":
            return
        await self._enqueue_audio(payload)
        self._schedule_silence_flush()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._cancel_silence_flush()
        await self._audio_queue.put(None)
        websocket = self._websocket
        if websocket is not None:
            try:
                await websocket.send(_json_message({"type": "session.finish"}))
                await asyncio.wait_for(
                    self._finished_event.wait(),
                    timeout=self._close_timeout_seconds,
                )
            except (TimeoutError, Exception):
                pass
            try:
                await websocket.close()
            except Exception:
                pass

    async def events(self) -> AsyncIterator[SttEvent]:
        websocket = await self._websocket_factory(
            _qwen_realtime_url(self._settings),
            _qwen_realtime_headers(self._settings),
        )
        self._websocket = websocket
        await websocket.send(_json_message(_qwen_session_update(self._settings)))
        sender = asyncio.create_task(self._send_audio_loop(websocket))
        try:
            async for raw_message in websocket:
                if _is_session_finished(raw_message):
                    self._finished_event.set()
                    break
                event = self._event_from_message(raw_message)
                if event is not None:
                    yield event
        finally:
            sender.cancel()
            try:
                await sender
            except asyncio.CancelledError:
                pass
            self._finished_event.set()
            await websocket.close()

    async def _enqueue_audio(self, payload: bytes) -> None:
        self._queued_audio_bytes += len(payload)
        await self._audio_queue.put(payload)

    def _schedule_silence_flush(self) -> None:
        task = self._silence_flush_task
        if task is not None and not task.done():
            task.cancel()
        self._silence_flush_task = asyncio.create_task(self._flush_silence_after_gap())

    async def _flush_silence_after_gap(self) -> None:
        try:
            await asyncio.sleep(self._silence_flush_delay_seconds)
            if self._closed:
                return
            silence_frame = b"\x00" * (
                self._settings.qwen_asr_sample_rate_hz
                * QWEN_ASR_CHANNELS
                * QWEN_ASR_BYTES_PER_SAMPLE
                * QWEN_ASR_FRAME_DURATION_MS
                // 1000
            )
            frame_count = max(
                self._silence_flush_duration_ms // QWEN_ASR_FRAME_DURATION_MS,
                1,
            )
            for _ in range(frame_count):
                if self._closed:
                    return
                await self._enqueue_audio(silence_frame)
        except asyncio.CancelledError:
            return

    async def _cancel_silence_flush(self) -> None:
        task = self._silence_flush_task
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            return

    async def _send_audio_loop(self, websocket: QwenRealtimeWebSocket) -> None:
        while True:
            payload = await self._audio_queue.get()
            if payload is None:
                return
            await websocket.send(
                _json_message(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(payload).decode("ascii"),
                    },
                ),
            )

    def _event_from_message(self, raw_message: str | bytes) -> SttEvent | None:
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8")
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            return None
        if not isinstance(message, dict):
            return None

        message_type = str(message.get("type", ""))
        if message_type == "error":
            raise RuntimeError(_qwen_error_message(message))

        if message_type == "conversation.item.input_audio_transcription.text":
            text = _transcript_text(message, include_stash=True)
            return SttInterimEvent(text=text) if text else None

        if message_type == "conversation.item.input_audio_transcription.completed":
            text = _transcript_text(message, include_stash=False)
            if not text:
                return None
            self._sequence += 1
            start_ms = self._last_final_end_ms
            end_ms = max(start_ms, self._queued_audio_duration_ms())
            self._last_final_end_ms = end_ms
            return SttFinalEvent(
                sequence=self._sequence,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                confidence=None,
            )

        return None

    def _queued_audio_duration_ms(self) -> int:
        bytes_per_ms = (
            self._settings.qwen_asr_sample_rate_hz
            * QWEN_ASR_CHANNELS
            * QWEN_ASR_BYTES_PER_SAMPLE
            / 1000
        )
        return int(self._queued_audio_bytes / bytes_per_ms)


def create_qwen_realtime_asr_provider_from_settings(
    settings: Settings,
) -> QwenRealtimeAsrProvider:
    return QwenRealtimeAsrProvider(settings=settings)


async def _connect_qwen_websocket(
    url: str,
    headers: dict[str, str],
) -> QwenRealtimeWebSocket:
    return await connect(url, additional_headers=headers)


def _qwen_realtime_url(settings: Settings) -> str:
    base_url = _required_setting(settings.qwen_asr_base_url, "QWEN_ASR_BASE_URL")
    model = _required_setting(settings.qwen_asr_model, "QWEN_ASR_MODEL")
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query))
    query["model"] = model
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        ),
    )


def _qwen_realtime_headers(settings: Settings) -> dict[str, str]:
    api_key = _required_setting(settings.qwen_api_key, "QWEN_API_KEY")
    return {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1",
    }


def _qwen_session_update(settings: Settings) -> dict[str, object]:
    if settings.qwen_asr_sample_rate_hz != QWEN_ASR_SAMPLE_RATE_HZ:
        raise RuntimeError("QWEN_ASR_SAMPLE_RATE_HZ must be 16000")
    audio_format = _qwen_audio_format(settings.qwen_asr_audio_format)
    transcription: dict[str, str] = {}
    language = settings.qwen_asr_language.strip()
    if language and language.lower() != "auto":
        transcription["language"] = language

    return {
        "type": "session.update",
        "session": {
            "modalities": ["text"],
            "input_audio_format": audio_format,
            "sample_rate": settings.qwen_asr_sample_rate_hz,
            "input_audio_transcription": transcription,
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.0,
                "silence_duration_ms": 400,
            },
        },
    }


def _json_message(payload: dict[str, object]) -> str:
    if "event_id" not in payload:
        payload = {"event_id": f"event_{uuid.uuid4().hex}", **payload}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _is_session_finished(raw_message: str | bytes) -> bool:
    if isinstance(raw_message, bytes):
        raw_message = raw_message.decode("utf-8")
    try:
        message = json.loads(raw_message)
    except json.JSONDecodeError:
        return False
    return isinstance(message, dict) and message.get("type") == "session.finished"


def _qwen_audio_format(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "pcm16":
        return "pcm"
    if normalized != "pcm":
        raise RuntimeError("QWEN_ASR_AUDIO_FORMAT must be pcm")
    return normalized


def _required_setting(value: str | None, env_name: str) -> str:
    if value is None or value.strip() == "":
        raise RuntimeError(f"{env_name} is required for Qwen realtime ASR")
    return value.strip()


def _transcript_text(message: dict[object, object], *, include_stash: bool) -> str:
    text = str(message.get("text") or message.get("transcript") or "").strip()
    if include_stash:
        stash = str(message.get("stash") or "").strip()
        if stash:
            text = f"{text} {stash}".strip()
    return " ".join(text.split())


def _qwen_error_message(message: dict[object, object]) -> str:
    error = message.get("error")
    if isinstance(error, dict):
        code = str(error.get("code") or "qwen_asr_error")
        detail = str(error.get("message") or "")
        return f"{code}: {detail}".strip()
    return "qwen_asr_error"
