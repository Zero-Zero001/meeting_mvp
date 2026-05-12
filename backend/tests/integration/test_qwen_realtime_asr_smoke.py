from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
import uuid
import wave
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.db.models import (
    CaptureMode,
    MeetingSessionStatus,
    SourcePlatform,
)
from meeting_mvp_backend.quota import QuotaDecision
from meeting_mvp_backend.stt_providers import QwenRealtimeAsrProvider
from meeting_mvp_backend.ws_sessions import (
    InMemorySessionResumeRegistry,
    WebSocketSessionOrchestrator,
)

pytestmark = pytest.mark.integration

RUN_QWEN_ASR_SMOKE = "RUN_QWEN_ASR_SMOKE"
QWEN_ASR_SMOKE_MANIFEST = "QWEN_ASR_SMOKE_MANIFEST"
PCM16_CHUNK_BYTES = 3200
PCM16_BYTES_PER_SECOND = 32000
VALID_AUDIO_FORMAT = {
    "sample_rate_hz": 16000,
    "channels": 1,
    "encoding": "pcm16",
}
PUNCTUATION_PATTERN = re.compile(r"[,.?!;:，。？！；：]")
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
ASCII_LETTER_PATTERN = re.compile(r"[A-Za-z]")

type JsonMessage = dict[str, object]


@dataclass(slots=True)
class SmokeAudioCase:
    name: str
    path: Path
    duration_seconds: int | None = None
    max_first_interim_seconds: float = 15.0
    max_first_final_seconds: float = 45.0
    expected_terms: tuple[str, ...] = ()
    max_term_errors: int = 0
    require_punctuation: bool = False
    expect_cjk: bool = False
    expect_ascii: bool = True


@dataclass(slots=True)
class SmokeRunResult:
    session_id: str
    archive_token: str
    archive_url: str
    messages: list[JsonMessage]
    first_interim_seconds: float | None
    first_final_seconds: float | None

    @property
    def final_text(self) -> str:
        return " ".join(
            str(message["text"])
            for message in self.messages
            if message.get("type") == "asr_final" and message.get("text")
        )


@dataclass(slots=True)
class StoredSession:
    session_id: str
    client_id: str
    archive_token_hash: str
    status: MeetingSessionStatus = MeetingSessionStatus.PENDING_AUDIO


class SmokeSessionRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, StoredSession] = {}

    async def client_exists(self, client_id: str) -> bool:
        return client_id != ""

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
        _ = source_platform, capture_mode, retention_expires_at
        self.sessions[str(session_id)] = StoredSession(
            session_id=str(session_id),
            client_id=client_id,
            archive_token_hash=archive_token_hash,
        )

    async def mark_session_active(
        self,
        *,
        session_id: uuid.UUID,
        started_at: datetime,
    ) -> None:
        _ = started_at
        self.sessions[str(session_id)].status = MeetingSessionStatus.ACTIVE

    async def close_session(
        self,
        *,
        session_id: uuid.UUID,
        ended_at: datetime,
        duration_seconds: int,
        quota_seconds_consumed: int,
        status: MeetingSessionStatus,
    ) -> None:
        _ = ended_at, duration_seconds, quota_seconds_consumed
        self.sessions[str(session_id)].status = status

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
        _ = (
            session_id,
            sequence,
            start_ms,
            end_ms,
            english_text_final,
            chinese_text_final,
            is_key_sentence,
        )
        raise AssertionError("asr_final must not be persisted in Step 16")


class SmokeQuotaService:
    async def reserve_active_session(
        self,
        client_id: str,
        session_id: str,
    ) -> QuotaDecision:
        _ = client_id, session_id
        return QuotaDecision(allowed=True, remaining_seconds_today=2400, reason=None)

    async def release_active_session(self, client_id: str, session_id: str) -> None:
        _ = client_id, session_id

    async def record_consumed_seconds(
        self,
        client_id: str,
        session_id: str,
        seconds: int,
    ) -> QuotaDecision:
        _ = client_id, session_id, seconds
        return QuotaDecision(allowed=True, remaining_seconds_today=2400, reason=None)


class SyncWebSocket(Protocol):
    def send_json(self, data: object) -> None: ...

    def send_bytes(self, data: bytes) -> None: ...

    def receive_json(self) -> JsonMessage: ...


@dataclass(slots=True)
class CollectedMessage:
    received_at: float
    payload: JsonMessage | BaseException


class WebSocketMessageCollector:
    def __init__(self, websocket: SyncWebSocket) -> None:
        self._websocket = websocket
        self._queue: queue.Queue[CollectedMessage] = queue.Queue()
        self.messages: list[JsonMessage] = []
        self._thread = threading.Thread(target=self._collect, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def wait_for_type(
        self,
        message_type: str,
        *,
        timeout_seconds: float,
    ) -> tuple[float, JsonMessage]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            remaining = max(deadline - time.monotonic(), 0.001)
            try:
                collected = self._queue.get(timeout=remaining)
            except queue.Empty:
                break
            if isinstance(collected.payload, BaseException):
                raise AssertionError("WebSocket receive loop ended") from (
                    collected.payload
                )
            message = collected.payload
            self.messages.append(message)
            if message.get("type") == "error":
                raise AssertionError(f"server returned error: {message.get('code')}")
            if message.get("type") == message_type:
                return collected.received_at, message
        raise AssertionError(f"timed out waiting for {message_type}")

    def drain(self) -> None:
        while True:
            try:
                collected = self._queue.get_nowait()
            except queue.Empty:
                return
            if not isinstance(collected.payload, BaseException):
                self.messages.append(collected.payload)

    def _collect(self) -> None:
        while True:
            try:
                payload = self._websocket.receive_json()
            except BaseException as exc:  # noqa: BLE001
                self._queue.put(
                    CollectedMessage(received_at=time.monotonic(), payload=exc),
                )
                return
            self._queue.put(
                CollectedMessage(received_at=time.monotonic(), payload=payload),
            )


def test_qwen_realtime_asr_smoke_ws_latency_and_resume() -> None:
    case = _require_smoke_case("latency")
    settings = _require_smoke_settings()
    client_id = str(uuid.uuid4())
    resume_registry = InMemorySessionResumeRegistry()

    app = _make_smoke_app(settings, resume_registry)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            first_run = _run_ws_stream(
                websocket=websocket,
                case=case,
                client_id=client_id,
                stop_at_end=False,
            )

        assert first_run.first_interim_seconds is not None
        assert first_run.first_interim_seconds <= case.max_first_interim_seconds
        assert first_run.first_final_seconds is not None
        assert first_run.first_final_seconds <= case.max_first_final_seconds

        time.sleep(0.2)
        with client.websocket_connect("/ws") as websocket:
            resumed = _resume_ws_stream(
                websocket=websocket,
                case=case,
                client_id=client_id,
                session_id=first_run.session_id,
                archive_token=first_run.archive_token,
            )

    assert resumed["type"] == "session_resumed"
    assert resumed["session_id"] == first_run.session_id
    assert resumed["archive_url"] == first_run.archive_url


@pytest.mark.parametrize(
    ("case_name", "expected_seconds"),
    [
        ("stability_30s", 30),
        ("stability_3m", 180),
        ("stability_10m", 600),
    ],
)
def test_qwen_realtime_asr_smoke_continuous_stream_stability(
    case_name: str,
    expected_seconds: int,
) -> None:
    case = _require_smoke_case(case_name)
    assert case.duration_seconds == expected_seconds
    settings = _require_smoke_settings()
    client_id = str(uuid.uuid4())

    app = _make_smoke_app(settings, InMemorySessionResumeRegistry())
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            result = _run_ws_stream(
                websocket=websocket,
                case=case,
                client_id=client_id,
                stop_at_end=True,
            )

    assert result.first_interim_seconds is not None
    assert result.first_final_seconds is not None
    assert result.final_text.strip() != ""


@pytest.mark.parametrize("case_name", ["terms", "mixed"])
def test_qwen_realtime_asr_smoke_quality_signals(case_name: str) -> None:
    case = _require_smoke_case(case_name)
    settings = _require_smoke_settings()
    client_id = str(uuid.uuid4())

    app = _make_smoke_app(settings, InMemorySessionResumeRegistry())
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            result = _run_ws_stream(
                websocket=websocket,
                case=case,
                client_id=client_id,
                stop_at_end=True,
            )

    final_text = result.final_text
    assert final_text.strip() != ""
    if case.expected_terms:
        missing_terms = _missing_terms(final_text, case.expected_terms)
        assert len(missing_terms) <= case.max_term_errors
    if case.require_punctuation:
        assert PUNCTUATION_PATTERN.search(final_text) is not None
    if case.expect_cjk:
        assert CJK_PATTERN.search(final_text) is not None
    if case.expect_ascii:
        assert ASCII_LETTER_PATTERN.search(final_text) is not None


def _run_ws_stream(
    *,
    websocket: SyncWebSocket,
    case: SmokeAudioCase,
    client_id: str,
    stop_at_end: bool,
) -> SmokeRunResult:
    collector = WebSocketMessageCollector(websocket)
    collector.start()

    websocket.send_json(
        {
            "type": "session_start",
            "client_id": client_id,
            "capture_mode": "tab_audio",
            "source_platform": "google_meet",
            "audio_format": VALID_AUDIO_FORMAT,
        },
    )
    _, started = collector.wait_for_type("session_started", timeout_seconds=5)
    session_id = str(started["session_id"])
    archive_token = str(started["archive_token"])
    archive_url = str(started["archive_url"])

    stream_started_at = time.monotonic()
    sender_error: list[BaseException] = []
    sender = threading.Thread(
        target=lambda: _send_audio_or_capture_error(
            websocket,
            case,
            sender_error,
        ),
        daemon=True,
    )
    sender.start()

    collector.wait_for_type("audio_status", timeout_seconds=5)
    interim_at, _ = collector.wait_for_type(
        "asr_interim",
        timeout_seconds=case.max_first_interim_seconds,
    )
    final_at, _ = collector.wait_for_type(
        "asr_final",
        timeout_seconds=case.max_first_final_seconds,
    )
    sender.join(timeout=(case.duration_seconds or 30) + 10)
    if sender.is_alive():
        raise AssertionError("audio sender did not finish")
    if sender_error:
        raise AssertionError("audio sender failed") from sender_error[0]

    if stop_at_end:
        websocket.send_json({"type": "session_stop", "session_id": session_id})
        collector.wait_for_type("session_closed", timeout_seconds=10)
    collector.drain()

    return SmokeRunResult(
        session_id=session_id,
        archive_token=archive_token,
        archive_url=archive_url,
        messages=collector.messages,
        first_interim_seconds=interim_at - stream_started_at,
        first_final_seconds=final_at - stream_started_at,
    )


def _resume_ws_stream(
    *,
    websocket: SyncWebSocket,
    case: SmokeAudioCase,
    client_id: str,
    session_id: str,
    archive_token: str,
) -> JsonMessage:
    collector = WebSocketMessageCollector(websocket)
    collector.start()
    websocket.send_json(
        {
            "type": "session_resume",
            "client_id": client_id,
            "session_id": session_id,
            "archive_token": archive_token,
            "audio_format": VALID_AUDIO_FORMAT,
        },
    )
    _, resumed = collector.wait_for_type("session_resumed", timeout_seconds=5)
    _send_audio(websocket, case, duration_seconds=1)
    websocket.send_json({"type": "session_stop", "session_id": session_id})
    collector.wait_for_type("session_closed", timeout_seconds=10)
    return resumed


def _send_audio_or_capture_error(
    websocket: SyncWebSocket,
    case: SmokeAudioCase,
    errors: list[BaseException],
) -> None:
    try:
        _send_audio(websocket, case, duration_seconds=case.duration_seconds)
    except BaseException as exc:  # noqa: BLE001
        errors.append(exc)


def _send_audio(
    websocket: SyncWebSocket,
    case: SmokeAudioCase,
    *,
    duration_seconds: int | None,
) -> None:
    audio = _load_pcm16_audio(case.path)
    if duration_seconds is not None:
        required_bytes = duration_seconds * PCM16_BYTES_PER_SECOND
        if len(audio) < required_bytes:
            raise AssertionError(
                f"{case.name} audio is shorter than {duration_seconds}s",
            )
        audio = audio[:required_bytes]

    for offset in range(0, len(audio), PCM16_CHUNK_BYTES):
        chunk = audio[offset : offset + PCM16_CHUNK_BYTES]
        if chunk:
            websocket.send_bytes(chunk)
            time.sleep(0.1)


def _load_pcm16_audio(path: Path) -> bytes:
    if path.suffix.lower() != ".wav":
        return path.read_bytes()

    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getframerate() != 16000:
            raise AssertionError("WAV smoke audio must be 16 kHz")
        if wav_file.getnchannels() != 1:
            raise AssertionError("WAV smoke audio must be mono")
        if wav_file.getsampwidth() != 2:
            raise AssertionError("WAV smoke audio must be 16-bit PCM")
        return wav_file.readframes(wav_file.getnframes())


def _make_smoke_app(
    settings: Settings,
    resume_registry: InMemorySessionResumeRegistry,
) -> FastAPI:
    app = FastAPI()
    repository = SmokeSessionRepository()
    quota_service = SmokeQuotaService()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        orchestrator = WebSocketSessionOrchestrator(
            repository=repository,
            quota_service=quota_service,
            settings=settings,
            clock=lambda: datetime.now(UTC),
            resume_registry=resume_registry,
            stt_provider_factory=lambda: QwenRealtimeAsrProvider(settings=settings),
        )
        await orchestrator.handle(websocket)

    return app


def _require_smoke_settings() -> Settings:
    if _env_value(RUN_QWEN_ASR_SMOKE) not in {"1", "true", "TRUE", "yes", "YES"}:
        pytest.skip(f"set {RUN_QWEN_ASR_SMOKE}=1 to run real Qwen ASR smoke tests")

    settings = _load_settings_from_env()
    missing_names = [
        name
        for name, value in {
            "QWEN_API_KEY": settings.qwen_api_key,
            "QWEN_ASR_BASE_URL": settings.qwen_asr_base_url,
            "QWEN_ASR_MODEL": settings.qwen_asr_model,
        }.items()
        if value is None or value.strip() == ""
    ]
    if missing_names:
        pytest.skip("missing Qwen ASR smoke env: " + ", ".join(missing_names))

    settings.public_base_url = "https://meeting.example.test"
    settings.session_resume_grace_seconds = max(
        settings.session_resume_grace_seconds,
        5,
    )
    return settings


def _load_settings_from_env() -> Settings:
    env_file = _env_value("MEETING_MVP_ENV_FILE")
    if env_file is None:
        return Settings()
    return Settings(_env_file=Path(env_file))  # type: ignore[call-arg]


def _require_smoke_case(case_name: str) -> SmokeAudioCase:
    case_config = _load_smoke_cases().get(case_name)
    if case_config is None:
        pytest.skip(f"missing Qwen ASR smoke audio case: {case_name}")
    path = Path(str(case_config["path"]))
    if not path.is_file():
        pytest.skip(f"Qwen ASR smoke audio not found for {case_name}")
    return SmokeAudioCase(
        name=case_name,
        path=path,
        duration_seconds=_optional_int(case_config.get("duration_seconds")),
        max_first_interim_seconds=_float_value(
            case_config.get("max_first_interim_seconds"),
            default=15.0,
        ),
        max_first_final_seconds=_float_value(
            case_config.get("max_first_final_seconds"),
            default=45.0,
        ),
        expected_terms=_string_sequence(case_config.get("expected_terms")),
        max_term_errors=_int_value(case_config.get("max_term_errors"), default=0),
        require_punctuation=_bool_value(case_config.get("require_punctuation")),
        expect_cjk=_bool_value(case_config.get("expect_cjk")),
        expect_ascii=_bool_value(case_config.get("expect_ascii"), default=True),
    )


def _load_smoke_cases() -> dict[str, JsonMessage]:
    manifest_path = _env_value(QWEN_ASR_SMOKE_MANIFEST)
    if manifest_path:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
        if not isinstance(manifest, dict):
            return {}
        raw_cases = manifest.get("cases", manifest)
        if not isinstance(raw_cases, dict):
            return {}
        return {
            str(name): _object_dict(config)
            for name, config in raw_cases.items()
            if isinstance(config, dict) and "path" in config
        }

    cases: dict[str, JsonMessage] = {}
    _add_env_case(cases, "latency", "QWEN_ASR_SMOKE_AUDIO_PATH")
    _add_env_case(
        cases,
        "stability_30s",
        "QWEN_ASR_SMOKE_30S_AUDIO_PATH",
        duration_seconds=30,
    )
    _add_env_case(
        cases,
        "stability_3m",
        "QWEN_ASR_SMOKE_3MIN_AUDIO_PATH",
        duration_seconds=180,
    )
    _add_env_case(
        cases,
        "stability_10m",
        "QWEN_ASR_SMOKE_10MIN_AUDIO_PATH",
        duration_seconds=600,
    )
    _add_env_case(
        cases,
        "terms",
        "QWEN_ASR_SMOKE_TERMS_AUDIO_PATH",
        expected_terms=_env_value("QWEN_ASR_SMOKE_EXPECTED_TERMS"),
        max_term_errors=_env_value("QWEN_ASR_SMOKE_MAX_TERM_ERRORS") or "0",
        require_punctuation=_env_value("QWEN_ASR_SMOKE_REQUIRE_PUNCTUATION")
        or "true",
    )
    _add_env_case(
        cases,
        "mixed",
        "QWEN_ASR_SMOKE_MIXED_AUDIO_PATH",
        expect_cjk=_env_value("QWEN_ASR_SMOKE_EXPECT_CJK") or "true",
        expect_ascii="true",
    )
    return cases


def _add_env_case(
    cases: dict[str, JsonMessage],
    case_name: str,
    path_env_name: str,
    **values: object,
) -> None:
    path = _env_value(path_env_name)
    if path:
        cases[case_name] = {"path": path, **values}


def _env_value(name: str) -> str | None:
    direct = os.getenv(name)
    if direct is not None and direct != "":
        return direct

    env_file = os.getenv("MEETING_MVP_ENV_FILE")
    if not env_file:
        return None
    path = Path(env_file)
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        if key.strip() == name:
            return raw_value.strip().strip('"').strip("'")
    return None


def _object_dict(value: dict[object, object]) -> JsonMessage:
    return {str(key): item for key, item in value.items()}


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(str(value))


def _int_value(value: object, *, default: int) -> int:
    if value is None or value == "":
        return default
    return int(str(value))


def _float_value(value: object, *, default: float) -> float:
    if value is None or value == "":
        return default
    return float(str(value))


def _bool_value(value: object, *, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _string_sequence(value: object) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return tuple(item.strip() for item in str(value).split(",") if item.strip())


def _missing_terms(text: str, expected_terms: tuple[str, ...]) -> list[str]:
    normalized_text = text.casefold()
    return [
        term
        for term in expected_terms
        if term.casefold() not in normalized_text
    ]
