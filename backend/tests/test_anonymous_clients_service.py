from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self, cast

import pytest
from sqlalchemy.sql import Select

from meeting_mvp_backend.anonymous_clients import AnonymousClientService
from meeting_mvp_backend.db.models import AnonymousClient
from meeting_mvp_backend.usage_events import UsageEventRecord, UsageEventType

FIXED_NOW = datetime(2026, 5, 15, 8, 30, tzinfo=UTC)


class FakeAnonymousClientSession:
    def __init__(self, existing_client: AnonymousClient | None = None) -> None:
        self.existing_client = existing_client
        self.added_client: AnonymousClient | None = None
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def scalar(
        self,
        statement: Select[tuple[AnonymousClient]],
    ) -> AnonymousClient | None:
        return self.existing_client

    def add(self, client: AnonymousClient) -> None:
        client.daily_minutes_used = 0
        self.added_client = client

    async def commit(self) -> None:
        self.committed = True


class FakeAnonymousClientSessionFactory:
    def __init__(self, existing_client: AnonymousClient | None = None) -> None:
        self.existing_client = existing_client
        self.last_session: FakeAnonymousClientSession | None = None

    def __call__(self) -> FakeAnonymousClientSession:
        self.last_session = FakeAnonymousClientSession(self.existing_client)
        return self.last_session


class FakeUsageEventRecorder:
    def __init__(self) -> None:
        self.records: list[UsageEventRecord] = []

    async def record_event(
        self,
        *,
        client_id: str,
        event_type: UsageEventType | str,
        payload: dict[str, object] | None = None,
        session_id: uuid.UUID | str | None = None,
    ) -> UsageEventRecord:
        record = UsageEventRecord(
            client_id=client_id,
            session_id=uuid.UUID(str(session_id)) if session_id is not None else None,
            event_type=UsageEventType(event_type),
            payload=payload or {},
            created_at=FIXED_NOW,
        )
        self.records.append(record)
        return record


@pytest.mark.asyncio
async def test_initialize_new_anonymous_client_records_client_created_event() -> None:
    client_id = uuid.uuid4()
    session_factory = FakeAnonymousClientSessionFactory()
    usage_events = FakeUsageEventRecorder()
    service = AnonymousClientService(
        session_factory=cast(Any, session_factory),
        daily_free_seconds=2400,
        usage_event_recorder=usage_events,
    )

    result = await service.initialize_client(
        client_id=client_id,
        ip_address="127.0.0.1",
        user_agent="test-browser",
    )

    assert result.is_new is True
    assert session_factory.last_session is not None
    assert session_factory.last_session.committed is True
    assert session_factory.last_session.added_client is not None
    assert usage_events.records == [
        UsageEventRecord(
            client_id=str(client_id),
            session_id=None,
            event_type=UsageEventType.CLIENT_CREATED,
            payload={
                "daily_free_seconds": 2400,
                "ip_hash_present": True,
                "user_agent_hash_present": True,
            },
            created_at=FIXED_NOW,
        ),
    ]


@pytest.mark.asyncio
async def test_initialize_existing_anonymous_client_does_not_record_client_created(
) -> None:
    client_id = uuid.uuid4()
    existing_client = AnonymousClient(
        client_id=str(client_id),
        first_seen_at=FIXED_NOW,
        last_seen_at=FIXED_NOW,
        daily_minutes_used=1,
        created_ip_hash="existing-ip-hash",
        user_agent_hash="existing-ua-hash",
    )
    session_factory = FakeAnonymousClientSessionFactory(existing_client)
    usage_events = FakeUsageEventRecorder()
    service = AnonymousClientService(
        session_factory=cast(Any, session_factory),
        daily_free_seconds=2400,
        usage_event_recorder=usage_events,
    )

    result = await service.initialize_client(
        client_id=client_id,
        ip_address="127.0.0.1",
        user_agent="test-browser",
    )

    assert result.is_new is False
    assert result.remaining_seconds_today == 2340
    assert usage_events.records == []
