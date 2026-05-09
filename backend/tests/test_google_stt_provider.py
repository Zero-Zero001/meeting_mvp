from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.stt_providers import (
    GoogleStreamingSttProvider,
    SttEvent,
    SttFinalEvent,
    SttInterimEvent,
)


@dataclass
class FakeAlternative:
    transcript: str
    confidence: float = 0.0


@dataclass
class FakeOffset:
    seconds: int = 0
    nanos: int = 0


@dataclass
class FakeResult:
    transcript: str
    is_final: bool
    result_end_offset: FakeOffset
    confidence: float = 0.0

    @property
    def alternatives(self) -> list[FakeAlternative]:
        return [FakeAlternative(self.transcript, self.confidence)]


@dataclass
class FakeResponse:
    results: list[FakeResult]


class FakeSpeechAsyncClient:
    def __init__(self, responses: list[FakeResponse] | None = None) -> None:
        self.responses = responses or []
        self.captured_requests: list[Any] = []

    async def streaming_recognize(self, *, requests: Any) -> Any:
        async for request in requests:
            self.captured_requests.append(request)
            if len(self.captured_requests) >= 2:
                break

        async def response_stream() -> Any:
            for response in self.responses:
                yield response

        return response_stream()


def google_settings() -> Settings:
    settings = Settings()
    settings.google_cloud_project = "meeting-project"
    settings.google_stt_location = "global"
    settings.google_stt_recognizer = "default"
    return settings


async def read_next_event(provider: GoogleStreamingSttProvider) -> SttEvent:
    return await provider.events().__anext__()


@pytest.mark.asyncio
async def test_google_stt_provider_sends_config_then_audio_requests() -> None:
    client = FakeSpeechAsyncClient()
    provider = GoogleStreamingSttProvider(
        settings=google_settings(),
        speech_client=client,
    )

    events_task: asyncio.Task[SttEvent] = asyncio.create_task(
        read_next_event(provider),
    )
    await provider.send_audio(b"\x01\x02")
    await asyncio.sleep(0)
    await provider.close()
    with pytest.raises(StopAsyncIteration):
        await events_task

    assert len(client.captured_requests) == 2
    config_request = client.captured_requests[0]
    audio_request = client.captured_requests[1]

    assert config_request.recognizer == (
        "projects/meeting-project/locations/global/recognizers/default"
    )
    assert config_request.streaming_config.config.language_codes == ["en-US"]
    decoding_config = config_request.streaming_config.config.explicit_decoding_config
    assert decoding_config.sample_rate_hertz == 16000
    assert decoding_config.audio_channel_count == 1
    assert config_request.streaming_config.streaming_features.interim_results is True
    assert audio_request.audio == b"\x01\x02"


@pytest.mark.asyncio
async def test_google_stt_provider_yields_interim_and_final_events() -> None:
    client = FakeSpeechAsyncClient(
        responses=[
            FakeResponse(
                [
                    FakeResult(
                        transcript="hello team",
                        is_final=False,
                        result_end_offset=FakeOffset(seconds=1, nanos=500_000_000),
                    ),
                ],
            ),
            FakeResponse(
                [
                    FakeResult(
                        transcript="hello team",
                        is_final=True,
                        result_end_offset=FakeOffset(seconds=2),
                        confidence=0.91,
                    ),
                ],
            ),
        ],
    )
    provider = GoogleStreamingSttProvider(
        settings=google_settings(),
        speech_client=client,
    )

    events = provider.events()
    await provider.send_audio(b"\x01\x02")

    interim = await events.__anext__()
    final = await events.__anext__()
    await provider.close()

    assert interim == SttInterimEvent(text="hello team")
    assert final == SttFinalEvent(
        sequence=1,
        start_ms=0,
        end_ms=2000,
        text="hello team",
        confidence=0.91,
    )


@pytest.mark.asyncio
async def test_google_stt_provider_propagates_streaming_errors() -> None:
    class FailingSpeechAsyncClient:
        async def streaming_recognize(self, *, requests: Any) -> Any:
            async for _request in requests:
                raise RuntimeError("google unavailable")

    provider = GoogleStreamingSttProvider(
        settings=google_settings(),
        speech_client=FailingSpeechAsyncClient(),
    )
    events = provider.events()

    await provider.send_audio(b"\x01\x02")

    with pytest.raises(RuntimeError, match="google unavailable"):
        await events.__anext__()
