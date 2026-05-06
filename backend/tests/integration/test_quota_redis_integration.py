from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from redis.asyncio import Redis

from meeting_mvp_backend.config import load_settings
from meeting_mvp_backend.quota import (
    QuotaDenialReason,
    QuotaService,
    QuotaSettings,
    RedisQuotaStore,
    active_sessions_key,
    budget_fuse_key,
    quota_used_seconds_key,
    seconds_until_next_shanghai_midnight,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_quota_service_uses_real_redis_state() -> None:
    settings = load_settings()
    assert settings.redis_url is not None

    fixed_now = datetime(2026, 5, 6, 3, 0, tzinfo=UTC)
    client_id = str(uuid.uuid4())
    expired_session_id = str(uuid.uuid4())
    first_session_id = str(uuid.uuid4())
    second_session_id = str(uuid.uuid4())
    quota_settings = QuotaSettings(
        daily_free_seconds=60,
        session_max_seconds=30,
        max_active_sessions_per_client=1,
        budget_fuse_rmb=1,
    )
    redis_client: Redis = Redis.from_url(settings.redis_url)
    redis_store = RedisQuotaStore(redis_client)
    service = QuotaService(
        store=redis_store,
        settings=quota_settings,
        clock=lambda: fixed_now,
    )

    quota_key = quota_used_seconds_key(client_id, fixed_now)
    active_key = active_sessions_key(client_id)
    fuse_key = budget_fuse_key(fixed_now)

    try:
        await redis_client.delete(quota_key, active_key, fuse_key)
        await redis_client.zadd(
            active_key,
            {expired_session_id: fixed_now.timestamp() - 1},
        )

        start_decision = await service.check_start_allowed(client_id)
        reserve_decision = await service.reserve_active_session(
            client_id,
            first_session_id,
        )
        second_reserve_decision = await service.reserve_active_session(
            client_id,
            second_session_id,
        )
        consumed_decision = await service.record_consumed_seconds(
            client_id=client_id,
            session_id=first_session_id,
            seconds=15,
        )
        quota_ttl = await redis_client.ttl(quota_key)
        await service.release_active_session(client_id, first_session_id)
        await redis_client.set(fuse_key, "1")
        fuse_decision = await service.check_start_allowed(client_id)

        assert start_decision.allowed is True
        assert reserve_decision.allowed is True
        assert await redis_client.zscore(active_key, expired_session_id) is None
        assert second_reserve_decision.allowed is False
        assert (
            second_reserve_decision.reason
            is QuotaDenialReason.ACTIVE_SESSION_LIMIT_REACHED
        )
        assert consumed_decision.allowed is True
        assert consumed_decision.remaining_seconds_today == 45
        assert 0 < quota_ttl <= seconds_until_next_shanghai_midnight(fixed_now)
        assert fuse_decision.allowed is False
        assert fuse_decision.reason is QuotaDenialReason.BUDGET_FUSE_TRIGGERED
    finally:
        await redis_client.delete(quota_key, active_key, fuse_key)
        await redis_client.aclose()
