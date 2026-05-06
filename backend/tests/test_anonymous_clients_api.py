from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from meeting_mvp_backend.anonymous_clients import AnonymousClientInitialization
from meeting_mvp_backend.config import get_settings
from meeting_mvp_backend.main import app, get_anonymous_client_service


class FakeAnonymousClientService:
    def __init__(self, result: AnonymousClientInitialization) -> None:
        self.result = result
        self.calls: list[tuple[uuid.UUID, str | None, str | None]] = []

    async def initialize_client(
        self,
        *,
        client_id: uuid.UUID,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AnonymousClientInitialization:
        self.calls.append((client_id, ip_address, user_agent))
        return self.result


@pytest.fixture(autouse=True)
async def reset_dependency_overrides() -> AsyncIterator[None]:
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_anonymous_client_endpoint_initializes_new_client() -> None:
    client_id = uuid.uuid4()
    service = FakeAnonymousClientService(
        AnonymousClientInitialization(
            client_id=client_id,
            daily_free_seconds=2400,
            remaining_seconds_today=2400,
            is_new=True,
        ),
    )
    app.dependency_overrides[get_anonymous_client_service] = lambda: service
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"user-agent": "test-browser"},
    ) as client:
        response = await client.post(
            "/api/anonymous-clients",
            json={"client_id": str(client_id)},
        )

    assert response.status_code == 200
    assert response.json() == {
        "client_id": str(client_id),
        "daily_free_seconds": 2400,
        "remaining_seconds_today": 2400,
        "is_new": True,
    }
    assert service.calls == [(client_id, "127.0.0.1", "test-browser")]


@pytest.mark.asyncio
async def test_anonymous_client_endpoint_does_not_return_raw_request_identity() -> None:
    client_id = uuid.uuid4()
    service = FakeAnonymousClientService(
        AnonymousClientInitialization(
            client_id=client_id,
            daily_free_seconds=2400,
            remaining_seconds_today=1800,
            is_new=False,
        ),
    )
    app.dependency_overrides[get_anonymous_client_service] = lambda: service
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"user-agent": "secret-test-user-agent"},
    ) as client:
        response = await client.post(
            "/api/anonymous-clients",
            json={"client_id": str(client_id)},
        )

    assert response.status_code == 200
    response_text = response.text
    assert "127.0.0.1" not in response_text
    assert "secret-test-user-agent" not in response_text


@pytest.mark.asyncio
async def test_anonymous_client_endpoint_rejects_invalid_client_id() -> None:
    service = FakeAnonymousClientService(
        AnonymousClientInitialization(
            client_id=uuid.uuid4(),
            daily_free_seconds=2400,
            remaining_seconds_today=2400,
            is_new=True,
        ),
    )
    app.dependency_overrides[get_anonymous_client_service] = lambda: service
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/anonymous-clients",
            json={"client_id": "not-a-uuid"},
        )

    assert response.status_code == 422
    assert service.calls == []


@pytest.mark.asyncio
async def test_anonymous_client_endpoint_returns_503_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MEETING_MVP_ENV_FILE", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/anonymous-clients",
            json={"client_id": str(uuid.uuid4())},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "DATABASE_URL is required to initialize anonymous clients",
    }
