from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.quota import (
    QuotaConfigurationError,
    QuotaDecision,
    QuotaDenialReason,
    QuotaPolicy,
    QuotaService,
    QuotaSettings,
    QuotaSnapshot,
    budget_estimated_cost_key,
    budget_fuse_key,
    create_quota_service_from_settings,
    quota_used_seconds_key,
    seconds_until_next_shanghai_midnight,
)

FIXED_NOW = datetime(2026, 5, 6, 3, 0, tzinfo=UTC)
TEST_SETTINGS = QuotaSettings(
    daily_free_seconds=2400,
    session_max_seconds=1800,
    max_active_sessions_per_client=1,
    budget_fuse_rmb=400,
)


@dataclass
class FakeQuotaStore:
    used_seconds_today: int = 0
    seeded_active_session_count: int = 0
    budget_estimated_cost_cents: int = 0
    budget_fuse_triggered: bool = False
    reserved_session_ids: set[str] = field(default_factory=set)
    last_quota_key: str | None = None
    last_quota_ttl_seconds: int | None = None

    async def get_snapshot(
        self,
        client_id: str,
        now: datetime,
        settings: QuotaSettings,
    ) -> QuotaSnapshot:
        return QuotaSnapshot(
            used_seconds_today=self.used_seconds_today,
            active_session_count=self._active_session_count(),
            budget_estimated_cost_cents=self.budget_estimated_cost_cents,
            budget_fuse_triggered=self.budget_fuse_triggered,
        )

    async def reserve_active_session(
        self,
        client_id: str,
        session_id: str,
        now: datetime,
        settings: QuotaSettings,
    ) -> QuotaDecision:
        snapshot = await self.get_snapshot(client_id, now, settings)
        decision = QuotaPolicy(settings).check_start(snapshot)
        if decision.allowed:
            self.reserved_session_ids.add(session_id)
        return decision

    async def release_active_session(
        self,
        client_id: str,
        session_id: str,
    ) -> None:
        self.reserved_session_ids.discard(session_id)

    async def record_consumed_seconds(
        self,
        client_id: str,
        session_id: str,
        seconds: int,
        now: datetime,
        settings: QuotaSettings,
    ) -> int:
        self.last_quota_key = quota_used_seconds_key(client_id, now)
        self.last_quota_ttl_seconds = seconds_until_next_shanghai_midnight(now)
        self.used_seconds_today = min(
            settings.daily_free_seconds,
            self.used_seconds_today + max(seconds, 0),
        )
        return self.used_seconds_today

    def _active_session_count(self) -> int:
        return self.seeded_active_session_count + len(self.reserved_session_ids)


def make_service(store: FakeQuotaStore) -> QuotaService:
    return QuotaService(
        store=store,
        settings=TEST_SETTINGS,
        clock=lambda: FIXED_NOW,
    )


@pytest.mark.asyncio
async def test_allows_start_when_limits_have_capacity() -> None:
    store = FakeQuotaStore(used_seconds_today=600)
    decision = await make_service(store).check_start_allowed(str(uuid.uuid4()))

    assert decision == QuotaDecision(
        allowed=True,
        remaining_seconds_today=1800,
        reason=None,
    )


@pytest.mark.asyncio
async def test_rejects_when_daily_quota_is_exhausted() -> None:
    store = FakeQuotaStore(used_seconds_today=2400)
    decision = await make_service(store).check_start_allowed(str(uuid.uuid4()))

    assert decision.allowed is False
    assert decision.remaining_seconds_today == 0
    assert decision.reason is QuotaDenialReason.DAILY_QUOTA_EXHAUSTED


@pytest.mark.asyncio
async def test_rejects_when_client_already_has_active_session() -> None:
    store = FakeQuotaStore(seeded_active_session_count=1)
    decision = await make_service(store).check_start_allowed(str(uuid.uuid4()))

    assert decision.allowed is False
    assert decision.remaining_seconds_today == 2400
    assert decision.reason is QuotaDenialReason.ACTIVE_SESSION_LIMIT_REACHED


def test_rejects_when_session_duration_reaches_limit() -> None:
    decision = make_service(FakeQuotaStore()).check_session_duration(1800)

    assert decision.allowed is False
    assert decision.remaining_seconds_today == 2400
    assert decision.reason is QuotaDenialReason.SESSION_TIME_LIMIT_REACHED


@pytest.mark.asyncio
async def test_budget_fuse_has_highest_rejection_priority() -> None:
    store = FakeQuotaStore(
        used_seconds_today=2400,
        seeded_active_session_count=1,
        budget_fuse_triggered=True,
    )
    decision = await make_service(store).check_start_allowed(str(uuid.uuid4()))

    assert decision.allowed is False
    assert decision.reason is QuotaDenialReason.BUDGET_FUSE_TRIGGERED


@pytest.mark.asyncio
async def test_budget_cost_at_threshold_triggers_fuse() -> None:
    store = FakeQuotaStore(budget_estimated_cost_cents=40000)
    decision = await make_service(store).check_start_allowed(str(uuid.uuid4()))

    assert decision.allowed is False
    assert decision.reason is QuotaDenialReason.BUDGET_FUSE_TRIGGERED


@pytest.mark.asyncio
async def test_reserve_and_release_active_session() -> None:
    client_id = str(uuid.uuid4())
    first_session_id = str(uuid.uuid4())
    second_session_id = str(uuid.uuid4())
    store = FakeQuotaStore()
    service = make_service(store)

    first_decision = await service.reserve_active_session(client_id, first_session_id)
    second_decision = await service.reserve_active_session(client_id, second_session_id)
    await service.release_active_session(client_id, first_session_id)
    third_decision = await service.reserve_active_session(client_id, second_session_id)

    assert first_decision.allowed is True
    assert second_decision.allowed is False
    assert second_decision.reason is QuotaDenialReason.ACTIVE_SESSION_LIMIT_REACHED
    assert third_decision.allowed is True


@pytest.mark.asyncio
async def test_record_consumed_seconds_caps_daily_usage() -> None:
    client_id = str(uuid.uuid4())
    store = FakeQuotaStore(used_seconds_today=2390)
    service = make_service(store)

    decision = await service.record_consumed_seconds(
        client_id=client_id,
        session_id=str(uuid.uuid4()),
        seconds=30,
    )

    assert decision.allowed is False
    assert decision.remaining_seconds_today == 0
    assert decision.reason is QuotaDenialReason.DAILY_QUOTA_EXHAUSTED
    assert store.used_seconds_today == 2400
    assert store.last_quota_key == (
        f"meeting_mvp:quota:{client_id}:20260506:used_seconds"
    )


def test_uses_asia_shanghai_day_key_and_midnight_ttl() -> None:
    client_id = str(uuid.uuid4())
    one_minute_before_midnight = datetime(2026, 5, 6, 15, 59, tzinfo=UTC)
    next_shanghai_day = datetime(2026, 5, 6, 16, 0, tzinfo=UTC)

    assert (
        quota_used_seconds_key(client_id, one_minute_before_midnight)
        == f"meeting_mvp:quota:{client_id}:20260506:used_seconds"
    )
    assert (
        quota_used_seconds_key(client_id, next_shanghai_day)
        == f"meeting_mvp:quota:{client_id}:20260507:used_seconds"
    )
    assert (
        budget_estimated_cost_key(one_minute_before_midnight)
        == "meeting_mvp:budget:202605:estimated_cost_cents"
    )
    assert budget_fuse_key(one_minute_before_midnight) == (
        "meeting_mvp:budget:202605:fuse_triggered"
    )
    assert seconds_until_next_shanghai_midnight(one_minute_before_midnight) == 60


def test_create_quota_service_from_settings_requires_redis_url() -> None:
    with pytest.raises(QuotaConfigurationError, match="REDIS_URL is required"):
        create_quota_service_from_settings(Settings())
