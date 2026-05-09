from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable
from dataclasses import dataclass
from typing import Any, Protocol

from google.cloud.speech_v2 import SpeechAsyncClient
from google.cloud.speech_v2.types import cloud_speech

from meeting_mvp_backend.config import Settings

GOOGLE_STT_SAMPLE_RATE_HZ = 16000
GOOGLE_STT_CHANNELS = 1
GOOGLE_STT_LANGUAGE_CODES = ["en-US"]


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


class SpeechAsyncClientProtocol(Protocol):
    def streaming_recognize(
        self,
        *,
        requests: AsyncIterator[Any],
    ) -> Awaitable[Any]: ...


class GoogleStreamingSttProvider:
    def __init__(
        self,
        *,
        settings: Settings,
        speech_client: SpeechAsyncClientProtocol | None = None,
    ) -> None:
        self._settings = settings
        self._speech_client = speech_client or SpeechAsyncClient()
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._closed = False
        self._last_final_end_ms = 0
        self._sequence = 0

    async def send_audio(self, payload: bytes) -> None:
        if self._closed or payload == b"":
            return
        await self._audio_queue.put(payload)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._audio_queue.put(None)

    async def events(self) -> AsyncIterator[SttEvent]:
        response_stream = await self._speech_client.streaming_recognize(
            requests=self._request_stream(),
        )
        async for response in response_stream:
            for result in getattr(response, "results", []):
                event = self._event_from_result(result)
                if event is not None:
                    yield event

    async def _request_stream(self) -> AsyncIterator[Any]:
        yield cloud_speech.StreamingRecognizeRequest(
            recognizer=build_google_recognizer_name(self._settings),
            streaming_config=_google_streaming_config(),
        )

        while True:
            payload = await self._audio_queue.get()
            if payload is None:
                return
            yield cloud_speech.StreamingRecognizeRequest(audio=payload)

    def _event_from_result(self, result: Any) -> SttEvent | None:
        alternatives = list(getattr(result, "alternatives", []))
        if not alternatives:
            return None

        alternative = alternatives[0]
        transcript = str(getattr(alternative, "transcript", "")).strip()
        if transcript == "":
            return None

        is_final = bool(getattr(result, "is_final", False))
        if not is_final:
            return SttInterimEvent(text=transcript)

        self._sequence += 1
        end_ms = _duration_to_ms(
            getattr(result, "result_end_offset", None),
            fallback_ms=self._last_final_end_ms,
        )
        start_ms = self._last_final_end_ms
        if end_ms < start_ms:
            end_ms = start_ms
        self._last_final_end_ms = end_ms

        confidence = _confidence_or_none(getattr(alternative, "confidence", None))
        return SttFinalEvent(
            sequence=self._sequence,
            start_ms=start_ms,
            end_ms=end_ms,
            text=transcript,
            confidence=confidence,
        )


def build_google_recognizer_name(settings: Settings) -> str:
    recognizer = _required_setting(
        settings.google_stt_recognizer,
        "GOOGLE_STT_RECOGNIZER",
    )
    if recognizer.startswith("projects/"):
        return recognizer

    project = _required_setting(settings.google_cloud_project, "GOOGLE_CLOUD_PROJECT")
    location = _required_setting(settings.google_stt_location, "GOOGLE_STT_LOCATION")
    return f"projects/{project}/locations/{location}/recognizers/{recognizer}"


def create_google_stt_provider_from_settings(
    settings: Settings,
) -> GoogleStreamingSttProvider:
    return GoogleStreamingSttProvider(settings=settings)


def _google_streaming_config() -> cloud_speech.StreamingRecognitionConfig:
    decoding_config = cloud_speech.ExplicitDecodingConfig(
        encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=GOOGLE_STT_SAMPLE_RATE_HZ,
        audio_channel_count=GOOGLE_STT_CHANNELS,
    )
    recognition_config = cloud_speech.RecognitionConfig(
        explicit_decoding_config=decoding_config,
        language_codes=GOOGLE_STT_LANGUAGE_CODES,
    )
    streaming_features = cloud_speech.StreamingRecognitionFeatures(
        interim_results=True,
    )
    return cloud_speech.StreamingRecognitionConfig(
        config=recognition_config,
        streaming_features=streaming_features,
    )


def _required_setting(value: str | None, env_name: str) -> str:
    if value is None or value.strip() == "":
        raise RuntimeError(f"{env_name} is required for Google STT")
    return value.strip()


def _duration_to_ms(offset: Any, *, fallback_ms: int) -> int:
    if offset is None:
        return fallback_ms
    seconds = int(getattr(offset, "seconds", 0) or 0)
    nanos = int(getattr(offset, "nanos", 0) or 0)
    return max((seconds * 1000) + (nanos // 1_000_000), fallback_ms)


def _confidence_or_none(value: object) -> float | None:
    if not isinstance(value, int | float):
        return None
    confidence = float(value)
    if confidence <= 0 or confidence > 1:
        return None
    return confidence
