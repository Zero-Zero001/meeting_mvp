from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator

import pytest

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.stt_providers import (
    QwenRealtimeAsrProvider,
    SttEvent,
    SttFinalEvent,
    SttInterimEvent,
)


class FakeQwenRealtimeWebSocket:
    def __init__(self, inbound_messages: list[dict[str, object]] | None = None) -> None:
        self.closed = False
        self.sent_messages: list[dict[str, object]] = []
        self._inbound_messages = inbound_messages or []

    async def send(self, message: str) -> None:
        sent_message = json.loads(message)
        self.sent_messages.append(sent_message)
        if sent_message["type"] == "session.finish":
            self.closed = True

    def __aiter__(self) -> AsyncIterator[str]:
        return self._messages()

    async def _messages(self) -> AsyncIterator[str]:
        for message in self._inbound_messages:
            yield json.dumps(message)
        while not self.closed:
            await asyncio.sleep(0.001)

    async def close(self) -> None:
        self.closed = True


class FakeQwenWebSocketFactory:
    def __init__(self, websocket: FakeQwenRealtimeWebSocket) -> None:
        self.websocket = websocket
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def __call__(
        self,
        url: str,
        headers: dict[str, str],
    ) -> FakeQwenRealtimeWebSocket:
        self.calls.append((url, headers))
        return self.websocket


def qwen_settings() -> Settings:
    settings = Settings()
    settings.qwen_api_key = "test-qwen-key"
    settings.qwen_asr_base_url = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
    settings.qwen_asr_model = "qwen3-asr-flash-realtime"
    settings.qwen_asr_language = "en"
    return settings


async def wait_for_sent_messages(
    websocket: FakeQwenRealtimeWebSocket,
    count: int,
) -> list[dict[str, object]]:
    for _ in range(100):
        if len(websocket.sent_messages) >= count:
            return websocket.sent_messages
        await asyncio.sleep(0.001)
    raise AssertionError(f"Timed out waiting for {count} sent messages")


async def read_next_event(provider: QwenRealtimeAsrProvider) -> SttEvent:
    return await provider.events().__anext__()


@pytest.mark.asyncio
async def test_qwen_provider_connects_with_realtime_headers_and_sends_config() -> None:
    websocket = FakeQwenRealtimeWebSocket()
    factory = FakeQwenWebSocketFactory(websocket)
    provider = QwenRealtimeAsrProvider(
        settings=qwen_settings(),
        websocket_factory=factory,
    )

    event_task: asyncio.Task[SttEvent] = asyncio.create_task(read_next_event(provider))
    await wait_for_sent_messages(websocket, 1)
    await provider.close()
    with pytest.raises(StopAsyncIteration):
        await event_task

    assert factory.calls == [
        (
            "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
            "?model=qwen3-asr-flash-realtime",
            {
                "Authorization": "Bearer test-qwen-key",
                "OpenAI-Beta": "realtime=v1",
            },
        ),
    ]
    session_update = websocket.sent_messages[0]
    assert session_update["type"] == "session.update"
    assert isinstance(session_update["event_id"], str)
    assert session_update["session"] == {
        "modalities": ["text"],
        "input_audio_format": "pcm",
        "sample_rate": 16000,
        "input_audio_transcription": {"language": "en"},
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.0,
            "silence_duration_ms": 400,
        },
    }


@pytest.mark.asyncio
async def test_qwen_provider_streams_pcm16_frames_as_base64_audio_append() -> None:
    websocket = FakeQwenRealtimeWebSocket()
    factory = FakeQwenWebSocketFactory(websocket)
    provider = QwenRealtimeAsrProvider(
        settings=qwen_settings(),
        websocket_factory=factory,
    )

    event_task: asyncio.Task[SttEvent] = asyncio.create_task(read_next_event(provider))
    await provider.send_audio(b"\x01\x02\x03\x04")
    await wait_for_sent_messages(websocket, 2)
    await provider.close()
    with pytest.raises(StopAsyncIteration):
        await event_task

    audio_append = websocket.sent_messages[1]
    assert audio_append["type"] == "input_audio_buffer.append"
    assert isinstance(audio_append["event_id"], str)
    assert audio_append["audio"] == base64.b64encode(b"\x01\x02\x03\x04").decode(
        "ascii",
    )


@pytest.mark.asyncio
async def test_qwen_provider_appends_short_silence_after_audio_gap() -> None:
    websocket = FakeQwenRealtimeWebSocket()
    provider = QwenRealtimeAsrProvider(
        settings=qwen_settings(),
        websocket_factory=FakeQwenWebSocketFactory(websocket),
        silence_flush_delay_seconds=0.001,
        silence_flush_duration_ms=200,
    )

    event_task: asyncio.Task[SttEvent] = asyncio.create_task(read_next_event(provider))
    await provider.send_audio(b"\x01\x02\x03\x04")
    await wait_for_sent_messages(websocket, 4)
    await provider.close()
    with pytest.raises(StopAsyncIteration):
        await event_task

    silence_messages = websocket.sent_messages[2:4]
    assert [message["type"] for message in silence_messages] == [
        "input_audio_buffer.append",
        "input_audio_buffer.append",
    ]
    for message in silence_messages:
        silence_payload = base64.b64decode(str(message["audio"]))
        assert len(silence_payload) == 3200
        assert set(silence_payload) == {0}


@pytest.mark.asyncio
async def test_qwen_provider_yields_interim_and_final_events() -> None:
    websocket = FakeQwenRealtimeWebSocket(
        [
            {
                "type": "conversation.item.input_audio_transcription.text",
                "text": "We need to",
                "stash": " align on the launch timeline",
            },
            {
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": "We need to align on the launch timeline.",
            },
        ],
    )
    provider = QwenRealtimeAsrProvider(
        settings=qwen_settings(),
        websocket_factory=FakeQwenWebSocketFactory(websocket),
    )

    events = provider.events()
    await provider.send_audio(b"\x00" * 6400)

    interim = await events.__anext__()
    final = await events.__anext__()
    await provider.close()

    assert interim == SttInterimEvent(
        text="We need to align on the launch timeline",
    )
    assert final == SttFinalEvent(
        sequence=1,
        start_ms=0,
        end_ms=200,
        text="We need to align on the launch timeline.",
        confidence=None,
    )


@pytest.mark.asyncio
async def test_qwen_provider_omits_language_when_language_is_auto() -> None:
    settings = qwen_settings()
    settings.qwen_asr_language = "auto"
    websocket = FakeQwenRealtimeWebSocket()
    provider = QwenRealtimeAsrProvider(
        settings=settings,
        websocket_factory=FakeQwenWebSocketFactory(websocket),
    )

    event_task: asyncio.Task[SttEvent] = asyncio.create_task(read_next_event(provider))
    await wait_for_sent_messages(websocket, 1)
    await provider.close()
    with pytest.raises(StopAsyncIteration):
        await event_task

    session_update = websocket.sent_messages[0]
    session = session_update["session"]
    assert isinstance(session, dict)
    assert session["input_audio_transcription"] == {}


@pytest.mark.asyncio
async def test_qwen_provider_propagates_server_errors() -> None:
    websocket = FakeQwenRealtimeWebSocket(
        [
            {
                "type": "error",
                "error": {
                    "code": "invalid_api_key",
                    "message": "Invalid API key",
                },
            },
        ],
    )
    provider = QwenRealtimeAsrProvider(
        settings=qwen_settings(),
        websocket_factory=FakeQwenWebSocketFactory(websocket),
    )

    with pytest.raises(RuntimeError, match="invalid_api_key"):
        await provider.events().__anext__()
