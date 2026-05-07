from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from meeting_mvp_backend.config import Settings, get_settings
from meeting_mvp_backend.db.models import (
    CaptureMode,
    MeetingSessionStatus,
    SourcePlatform,
)
from meeting_mvp_backend.main import app, get_websocket_session_orchestrator
from meeting_mvp_backend.quota import QuotaDecision, QuotaDenialReason
from meeting_mvp_backend.ws_sessions import (
    WebSocketSessionOrchestrator,
    hash_archive_token,
)

VALID_AUDIO_FORMAT = {
    "sample_rate_hz": 16000,
    "channels": 1,
    "encoding": "pcm16",
}
FIXED_NOW = datetime(2026, 5, 7, 3, 0, tzinfo=UTC)


@dataclass
class StoredSession:
    session_id: str
    client_id: str
    archive_token_hash: str
    source_platform: SourcePlatform
    capture_mode: CaptureMode
    retention_expires_at: datetime
    status: MeetingSessionStatus = MeetingSessionStatus.PENDING_AUDIO
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int = 0
    quota_seconds_consumed: int = 0


class FakeSessionRepository:
    def __init__(self, initialized_client_ids: set[str] | None = None) -> None:
        self.initialized_client_ids = initialized_client_ids or set()
        self.sessions: dict[str, StoredSession] = {}

    async def client_exists(self, client_id: str) -> bool:
        return client_id in self.initialized_client_ids

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
        self.sessions[str(session_id)] = StoredSession(
            session_id=str(session_id),
            client_id=client_id,
            archive_token_hash=archive_token_hash,
            source_platform=source_platform,
            capture_mode=capture_mode,
            retention_expires_at=retention_expires_at,
        )

    async def mark_session_active(
        self,
        *,
        session_id: uuid.UUID,
        started_at: datetime,
    ) -> None:
        stored_session = self.sessions[str(session_id)]
        stored_session.status = MeetingSessionStatus.ACTIVE
        stored_session.started_at = started_at

    async def close_session(
        self,
        *,
        session_id: uuid.UUID,
        ended_at: datetime,
        duration_seconds: int,
        quota_seconds_consumed: int,
        status: MeetingSessionStatus,
    ) -> None:
        stored_session = self.sessions[str(session_id)]
        stored_session.status = status
        stored_session.ended_at = ended_at
        stored_session.duration_seconds = duration_seconds
        stored_session.quota_seconds_consumed = quota_seconds_consumed


class FakeQuotaService:
    def __init__(
        self,
        *,
        remaining_seconds_today: int = 2400,
        denial_reason: QuotaDenialReason | None = None,
    ) -> None:
        self.remaining_seconds_today = remaining_seconds_today
        self.denial_reason = denial_reason
        self.reserved_session_ids: list[str] = []
        self.released_session_ids: list[str] = []
        self.consumed_seconds: list[int] = []

    async def reserve_active_session(
        self,
        client_id: str,
        session_id: str,
    ) -> QuotaDecision:
        if self.denial_reason is not None:
            return QuotaDecision(
                allowed=False,
                remaining_seconds_today=self.remaining_seconds_today,
                reason=self.denial_reason,
            )
        self.reserved_session_ids.append(session_id)
        return QuotaDecision(
            allowed=True,
            remaining_seconds_today=self.remaining_seconds_today,
            reason=None,
        )

    async def release_active_session(self, client_id: str, session_id: str) -> None:
        self.released_session_ids.append(session_id)

    async def record_consumed_seconds(
        self,
        client_id: str,
        session_id: str,
        seconds: int,
    ) -> QuotaDecision:
        self.consumed_seconds.append(seconds)
        self.remaining_seconds_today = max(self.remaining_seconds_today - seconds, 0)
        return QuotaDecision(
            allowed=self.remaining_seconds_today > 0,
            remaining_seconds_today=self.remaining_seconds_today,
            reason=(
                None
                if self.remaining_seconds_today > 0
                else QuotaDenialReason.DAILY_QUOTA_EXHAUSTED
            ),
        )


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self._values = list(values)
        self._last = values[-1] if values else FIXED_NOW

    def __call__(self) -> datetime:
        if self._values:
            self._last = self._values.pop(0)
        return self._last


@pytest.fixture(autouse=True)
async def reset_app_overrides() -> AsyncIterator[None]:
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def make_client(
    *,
    repository: FakeSessionRepository,
    quota_service: FakeQuotaService,
    clock: Callable[[], datetime] | None = None,
) -> TestClient:
    settings = Settings()
    settings.public_base_url = "https://meeting.example.test"
    settings.archive_retention_days = 30

    def override_orchestrator() -> WebSocketSessionOrchestrator:
        return WebSocketSessionOrchestrator(
            repository=repository,
            quota_service=quota_service,
            settings=settings,
            clock=clock or (lambda: FIXED_NOW),
        )

    app.dependency_overrides[get_websocket_session_orchestrator] = (
        override_orchestrator
    )
    return TestClient(app)


def session_start_payload(client_id: str) -> dict[str, object]:
    return {
        "type": "session_start",
        "client_id": client_id,
        "capture_mode": "tab_audio",
        "source_platform": "google_meet",
        "audio_format": VALID_AUDIO_FORMAT,
    }


def test_session_start_returns_session_started_and_writes_pending_session() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            message = websocket.receive_json()
            session_id = message["session_id"]
            stored_session = repository.sessions[session_id]

            assert message["type"] == "session_started"
            assert message["remaining_seconds_today"] == 2400
            assert message["archive_url"] == (
                f"https://meeting.example.test/archive/{session_id}"
                f"?token={message['archive_token']}"
            )
            assert stored_session.client_id == client_id
            assert stored_session.status is MeetingSessionStatus.PENDING_AUDIO
            assert stored_session.started_at is None
            assert stored_session.archive_token_hash == hash_archive_token(
                message["archive_token"],
            )
            assert stored_session.archive_token_hash != message["archive_token"]
            assert quota_service.reserved_session_ids == [session_id]


def test_non_empty_binary_frame_activates_session_then_stop_settles_quota() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()
    active_at = FIXED_NOW + timedelta(seconds=2)
    stop_at = FIXED_NOW + timedelta(seconds=9)
    clock = SequenceClock(FIXED_NOW, active_at, stop_at)

    with make_client(
        repository=repository,
        quota_service=quota_service,
        clock=clock,
    ) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            session_id = started["session_id"]

            websocket.send_bytes(b"\x00\x01")
            audio_status = websocket.receive_json()
            websocket.send_json({"type": "heartbeat", "session_id": session_id})
            websocket.send_json({"type": "session_stop", "session_id": session_id})
            quota_update = websocket.receive_json()
            closed = websocket.receive_json()

    stored_session = repository.sessions[session_id]

    assert audio_status == {"type": "audio_status", "has_audio": True, "level": None}
    assert quota_update == {
        "type": "quota_update",
        "remaining_seconds_today": 2393,
    }
    assert closed == {"type": "session_closed", "reason": "user_stopped"}
    assert stored_session.status is MeetingSessionStatus.ENDED
    assert stored_session.started_at == active_at
    assert stored_session.ended_at == stop_at
    assert stored_session.duration_seconds == 7
    assert stored_session.quota_seconds_consumed == 7
    assert quota_service.consumed_seconds == [7]
    assert quota_service.released_session_ids == [session_id]


def test_browser_disconnect_releases_active_session() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()

    assert quota_service.released_session_ids == [started["session_id"]]
    assert (
        repository.sessions[started["session_id"]].status
        is MeetingSessionStatus.ERROR
    )


def test_rejects_duplicate_active_session() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService(
        denial_reason=QuotaDenialReason.ACTIVE_SESSION_LIMIT_REACHED,
    )

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            error = websocket.receive_json()
            closed = websocket.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "active_session_limit_reached"
    assert closed == {
        "type": "session_closed",
        "reason": "active_session_limit_reached",
    }
    assert repository.sessions == {}


def test_rejects_uninitialized_client() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository()
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            error = websocket.receive_json()
            closed = websocket.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "client_not_initialized"
    assert closed == {
        "type": "session_closed",
        "reason": "client_not_initialized",
    }
    assert quota_service.reserved_session_ids == []


def test_invalid_message_closes_with_invalid_message_error() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("{not-json")
            error = websocket.receive_json()
            closed = websocket.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "invalid_message"
    assert closed == {"type": "session_closed", "reason": "invalid_message"}


def test_session_id_mismatch_closes_and_cleans_up() -> None:
    client_id = str(uuid.uuid4())
    repository = FakeSessionRepository({client_id})
    quota_service = FakeQuotaService()

    with make_client(repository=repository, quota_service=quota_service) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json(session_start_payload(client_id))
            started = websocket.receive_json()
            websocket.send_json(
                {"type": "session_stop", "session_id": str(uuid.uuid4())},
            )
            error = websocket.receive_json()
            closed = websocket.receive_json()

    session_id = started["session_id"]
    assert error["type"] == "error"
    assert error["code"] == "session_mismatch"
    assert closed == {"type": "session_closed", "reason": "session_mismatch"}
    assert quota_service.released_session_ids == [session_id]
