from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from meeting_mvp_backend.db.models import AnonymousClient
from meeting_mvp_backend.usage_events import (
    UsageEventRecorder,
    UsageEventType,
    record_usage_event_best_effort,
)


@dataclass(frozen=True)
class AnonymousClientInitialization:
    client_id: uuid.UUID
    daily_free_seconds: int
    remaining_seconds_today: int
    is_new: bool


def hash_request_identity(*, client_id: uuid.UUID, value: str | None) -> str:
    normalized_value = (value or "").strip()
    raw_value = f"{client_id}:{normalized_value}".encode()
    return hashlib.sha256(raw_value).hexdigest()


class AnonymousClientService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        daily_free_seconds: int,
        usage_event_recorder: UsageEventRecorder | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._daily_free_seconds = daily_free_seconds
        self._usage_event_recorder = usage_event_recorder

    async def initialize_client(
        self,
        *,
        client_id: uuid.UUID,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AnonymousClientInitialization:
        now = datetime.now(UTC)
        client_id_string = str(client_id)
        ip_hash = hash_request_identity(client_id=client_id, value=ip_address)
        user_agent_hash = hash_request_identity(client_id=client_id, value=user_agent)

        async with self._session_factory() as session:
            anonymous_client = await session.scalar(
                select(AnonymousClient).where(
                    AnonymousClient.client_id == client_id_string,
                ),
            )
            is_new = anonymous_client is None

            if anonymous_client is None:
                anonymous_client = AnonymousClient(
                    client_id=client_id_string,
                    first_seen_at=now,
                    last_seen_at=now,
                    created_ip_hash=ip_hash,
                    user_agent_hash=user_agent_hash,
                )
                session.add(anonymous_client)
            else:
                anonymous_client.last_seen_at = now
                anonymous_client.user_agent_hash = user_agent_hash

            await session.commit()
            remaining_seconds_today = max(
                self._daily_free_seconds - anonymous_client.daily_minutes_used * 60,
                0,
            )

        if is_new:
            await record_usage_event_best_effort(
                recorder=self._usage_event_recorder,
                client_id=client_id_string,
                event_type=UsageEventType.CLIENT_CREATED,
                payload={
                    "daily_free_seconds": self._daily_free_seconds,
                    "ip_hash_present": bool((ip_address or "").strip()),
                    "user_agent_hash_present": bool((user_agent or "").strip()),
                },
            )

        return AnonymousClientInitialization(
            client_id=client_id,
            daily_free_seconds=self._daily_free_seconds,
            remaining_seconds_today=remaining_seconds_today,
            is_new=is_new,
        )
