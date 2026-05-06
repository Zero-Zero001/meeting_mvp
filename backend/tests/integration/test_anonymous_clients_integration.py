from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from meeting_mvp_backend.config import load_settings
from meeting_mvp_backend.db.models import AnonymousClient
from meeting_mvp_backend.db.session import create_engine, create_session_factory
from meeting_mvp_backend.main import app

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_anonymous_client_endpoint_upserts_against_postgresql() -> None:
    settings = load_settings()
    assert settings.database_url is not None

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    client_id = uuid.uuid4()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"user-agent": "integration-browser-a"},
        ) as client:
            first_response = await client.post(
                "/api/anonymous-clients",
                json={"client_id": str(client_id)},
            )
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers={"user-agent": "integration-browser-b"},
        ) as client:
            second_response = await client.post(
                "/api/anonymous-clients",
                json={"client_id": str(client_id)},
            )

        assert first_response.status_code == 200
        assert first_response.json()["is_new"] is True
        assert second_response.status_code == 200
        assert second_response.json()["is_new"] is False

        async with session_factory() as session:
            saved_client = await session.scalar(
                select(AnonymousClient).where(
                    AnonymousClient.client_id == str(client_id),
                ),
            )

        assert saved_client is not None
        assert saved_client.created_ip_hash != "127.0.0.1"
        assert saved_client.user_agent_hash != "integration-browser-b"
        assert len(saved_client.created_ip_hash) == 64
        assert len(saved_client.user_agent_hash) == 64
        assert saved_client.last_seen_at >= saved_client.first_seen_at
    finally:
        async with session_factory() as session:
            await session.execute(
                delete(AnonymousClient).where(
                    AnonymousClient.client_id == str(client_id),
                ),
            )
            await session.commit()
        await engine.dispose()
