from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.stt_providers import (
    GoogleStreamingSttProvider,
    SttEvent,
    SttFinalEvent,
    SttInterimEvent,
)

pytestmark = pytest.mark.integration

GOOGLE_STT_SMOKE_AUDIO_PATH = "GOOGLE_STT_SMOKE_AUDIO_PATH"
GOOGLE_REQUIRED_ENV_NAMES = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_STT_LOCATION",
    "GOOGLE_STT_RECOGNIZER",
)


def _skip_reason() -> str | None:
    missing_names = [name for name in GOOGLE_REQUIRED_ENV_NAMES if not os.getenv(name)]
    if missing_names:
        return "missing Google STT smoke env: " + ", ".join(missing_names)

    audio_path = os.getenv(GOOGLE_STT_SMOKE_AUDIO_PATH)
    if not audio_path:
        return f"missing {GOOGLE_STT_SMOKE_AUDIO_PATH}"
    if not Path(audio_path).is_file():
        return f"{GOOGLE_STT_SMOKE_AUDIO_PATH} does not point to a file"
    return None


async def _wait_for_event[SttEventT: SttEvent](
    events: list[SttEvent],
    event_type: type[SttEventT],
    *,
    collector: asyncio.Task[None],
    timeout_seconds: float,
) -> SttEventT:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        for event in events:
            if isinstance(event, event_type):
                return event
        if collector.done():
            await collector
            raise AssertionError(
                f"Collector finished before {event_type.__name__} was received",
            )
        await asyncio.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {event_type.__name__}")


@pytest.mark.asyncio
async def test_google_stt_streaming_smoke_emits_interim_and_final() -> None:
    skip_reason = _skip_reason()
    if skip_reason is not None:
        pytest.skip(skip_reason)

    audio_path = Path(os.environ[GOOGLE_STT_SMOKE_AUDIO_PATH])
    provider = GoogleStreamingSttProvider(settings=Settings())
    received_events: list[SttEvent] = []

    async def collect_events() -> None:
        async for event in provider.events():
            received_events.append(event)
            if isinstance(event, SttFinalEvent):
                return

    collector = asyncio.create_task(collect_events())
    try:
        with audio_path.open("rb") as audio_file:
            while chunk := audio_file.read(3200):
                await provider.send_audio(chunk)
                await asyncio.sleep(0.1)

        interim = await _wait_for_event(
            received_events,
            SttInterimEvent,
            collector=collector,
            timeout_seconds=10,
        )
        assert interim.text.strip() != ""

        await provider.close()
        await asyncio.wait_for(collector, timeout=20)
        assert any(
            isinstance(event, SttFinalEvent) and event.text.strip() != ""
            for event in received_events
        )
    finally:
        await provider.close()
        if not collector.done():
            collector.cancel()
            with pytest.raises(asyncio.CancelledError):
                await collector
