from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastapi import WebSocket
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from sqlalchemy import delete, select

from meeting_mvp_backend.config import get_settings, load_settings
from meeting_mvp_backend.db.models import (
    AnonymousClient,
    MeetingSession,
    MeetingSessionStatus,
)
from meeting_mvp_backend.db.session import create_engine, create_session_factory
from meeting_mvp_backend.main import app
from meeting_mvp_backend.quota import (
    active_sessions_key,
    create_quota_service_from_settings,
)
from meeting_mvp_backend.ws_sessions import (
    SQLAlchemyMeetingSessionRepository,
    WebSocketSessionOrchestrator,
)

pytestmark = pytest.mark.integration

VALID_AUDIO_FORMAT = {
    "sample_rate_hz": 16000,
    "channels": 1,
    "encoding": "pcm16",
}


async def seed_client(client_id: str) -> None:
    settings = load_settings()
    assert settings.database_url is not None
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            session.add(
                AnonymousClient(
                    client_id=client_id,
                    first_seen_at=datetime.now(UTC),
                    last_seen_at=datetime.now(UTC),
                    created_ip_hash="integration-ip-hash",
                    user_agent_hash="integration-user-agent-hash",
                ),
            )
            await session.commit()
    finally:
        await engine.dispose()


async def fetch_session(session_id: str) -> MeetingSession:
    settings = load_settings()
    assert settings.database_url is not None
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            meeting_session = await session.scalar(
                select(MeetingSession).where(
                    MeetingSession.id == uuid.UUID(session_id),
                ),
            )
            assert meeting_session is not None
            return meeting_session
    finally:
        await engine.dispose()


async def cleanup(client_id: str) -> None:
    settings = load_settings()
    assert settings.database_url is not None
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            await session.execute(
                delete(MeetingSession).where(MeetingSession.client_id == client_id),
            )
            await session.execute(
                delete(AnonymousClient).where(AnonymousClient.client_id == client_id),
            )
            await session.commit()
    finally:
        await engine.dispose()

    assert settings.redis_url is not None
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        await redis_client.delete(active_sessions_key(client_id))
    finally:
        await redis_client.aclose()


async def active_session_count(client_id: str) -> int:
    settings = load_settings()
    assert settings.redis_url is not None
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        return int(await redis_client.zcard(active_sessions_key(client_id)))
    finally:
        await redis_client.aclose()


class ScriptedDisconnectWebSocket:
    def __init__(self, client_id: str) -> None:
        self.accepted = False
        self.closed = False
        self.sent_json: list[dict[str, Any]] = []
        self._messages: list[dict[str, Any]] = [
            {
                "type": "websocket.receive",
                "text": json.dumps(session_start_payload(client_id)),
            },
            {"type": "websocket.disconnect"},
        ]

    async def accept(self) -> None:
        self.accepted = True

    async def receive(self) -> dict[str, Any]:
        return self._messages.pop(0)

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent_json.append(data)

    async def close(self, code: int = 1000) -> None:
        self.closed = True


async def run_scripted_disconnect_session(client_id: str) -> str:
    settings = load_settings()
    assert settings.database_url is not None
    settings.session_resume_grace_seconds = 0
    engine = create_engine(settings.database_url)
    try:
        orchestrator = WebSocketSessionOrchestrator(
            repository=SQLAlchemyMeetingSessionRepository(
                create_session_factory(engine),
            ),
            quota_service=create_quota_service_from_settings(settings),
            settings=settings,
        )
        websocket = ScriptedDisconnectWebSocket(client_id)
        await orchestrator.handle(cast(WebSocket, websocket))
        for _ in range(20):
            if await active_session_count(client_id) == 0:
                break
            await asyncio.sleep(0.05)
        assert websocket.accepted is True
        assert websocket.sent_json[0]["type"] == "session_started"
        return str(websocket.sent_json[0]["session_id"])
    finally:
        await engine.dispose()


def session_start_payload(client_id: str) -> dict[str, object]:
    return {
        "type": "session_start",
        "client_id": client_id,
        "capture_mode": "tab_audio",
        "source_platform": "google_meet",
        "audio_format": VALID_AUDIO_FORMAT,
    }


def test_websocket_session_lifecycle_uses_real_postgres_and_redis() -> None:
    settings = load_settings()
    assert settings.database_url is not None
    assert settings.redis_url is not None
    get_settings.cache_clear()

    client_id = str(uuid.uuid4())
    asyncio.run(seed_client(client_id))

    try:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                websocket.send_json(session_start_payload(client_id))
                started = websocket.receive_json()
                session_id = started["session_id"]

                with client.websocket_connect("/ws") as duplicate:
                    duplicate.send_json(session_start_payload(client_id))
                    duplicate_error = duplicate.receive_json()
                    duplicate_closed = duplicate.receive_json()

                websocket.send_bytes(b"\x00\x01")
                audio_status = websocket.receive_json()
                websocket.send_json(
                    {"type": "session_stop", "session_id": session_id},
                )
                quota_update = websocket.receive_json()
                closed = websocket.receive_json()

        stored_session = asyncio.run(fetch_session(session_id))

        assert started["type"] == "session_started"
        assert duplicate_error["code"] == "active_session_limit_reached"
        assert duplicate_closed["reason"] == "active_session_limit_reached"
        assert audio_status["type"] == "audio_status"
        assert audio_status["has_audio"] is True
        assert quota_update["type"] == "quota_update"
        assert closed == {"type": "session_closed", "reason": "user_stopped"}
        assert stored_session.status is MeetingSessionStatus.ENDED
        assert stored_session.archive_token_hash != started["archive_token"]
    finally:
        asyncio.run(cleanup(client_id))


def test_websocket_disconnect_grace_expiry_releases_real_redis_active_session() -> None:
    settings = load_settings()
    assert settings.database_url is not None
    assert settings.redis_url is not None
    get_settings.cache_clear()

    client_id = str(uuid.uuid4())
    asyncio.run(seed_client(client_id))

    try:
        first_session_id = asyncio.run(run_scripted_disconnect_session(client_id))
        first_session = asyncio.run(fetch_session(first_session_id))

        assert asyncio.run(active_session_count(client_id)) == 0
        assert first_session.status is MeetingSessionStatus.ERROR
    finally:
        asyncio.run(cleanup(client_id))
