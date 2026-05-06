from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol
from zoneinfo import ZoneInfo

from redis.asyncio import Redis

from meeting_mvp_backend.config import Settings

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
REDIS_KEY_PREFIX = "meeting_mvp"


class QuotaConfigurationError(RuntimeError):
    """Raised when quota service configuration is missing or invalid."""


class QuotaDenialReason(StrEnum):
    BUDGET_FUSE_TRIGGERED = "budget_fuse_triggered"
    ACTIVE_SESSION_LIMIT_REACHED = "active_session_limit_reached"
    DAILY_QUOTA_EXHAUSTED = "daily_quota_exhausted"
    SESSION_TIME_LIMIT_REACHED = "session_time_limit_reached"


@dataclass(frozen=True, slots=True)
class QuotaDecision:
    allowed: bool
    remaining_seconds_today: int
    reason: QuotaDenialReason | None = None


@dataclass(frozen=True, slots=True)
class QuotaSettings:
    daily_free_seconds: int
    session_max_seconds: int
    max_active_sessions_per_client: int
    budget_fuse_rmb: int


@dataclass(frozen=True, slots=True)
class QuotaSnapshot:
    used_seconds_today: int
    active_session_count: int
    budget_estimated_cost_cents: int
    budget_fuse_triggered: bool


class QuotaStateStore(Protocol):
    async def get_snapshot(
        self,
        client_id: str,
        now: datetime,
        settings: QuotaSettings,
    ) -> QuotaSnapshot: ...

    async def reserve_active_session(
        self,
        client_id: str,
        session_id: str,
        now: datetime,
        settings: QuotaSettings,
    ) -> QuotaDecision: ...

    async def release_active_session(
        self,
        client_id: str,
        session_id: str,
    ) -> None: ...

    async def record_consumed_seconds(
        self,
        client_id: str,
        session_id: str,
        seconds: int,
        now: datetime,
        settings: QuotaSettings,
    ) -> int: ...


Clock = Callable[[], datetime]


def quota_settings_from_app_settings(settings: Settings) -> QuotaSettings:
    return QuotaSettings(
        daily_free_seconds=settings.daily_free_seconds,
        session_max_seconds=settings.session_max_seconds,
        max_active_sessions_per_client=settings.max_active_sessions_per_client,
        budget_fuse_rmb=settings.budget_fuse_rmb,
    )


def create_quota_service_from_settings(
    settings: Settings,
    clock: Clock | None = None,
) -> QuotaService:
    if settings.redis_url is None:
        raise QuotaConfigurationError("REDIS_URL is required for quota service")

    redis_client = Redis.from_url(settings.redis_url)
    return QuotaService(
        store=RedisQuotaStore(redis_client),
        settings=quota_settings_from_app_settings(settings),
        clock=clock,
    )


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _to_shanghai(value: datetime) -> datetime:
    return _ensure_aware(value).astimezone(SHANGHAI_TZ)


def shanghai_day_key(now: datetime) -> str:
    return _to_shanghai(now).strftime("%Y%m%d")


def shanghai_month_key(now: datetime) -> str:
    return _to_shanghai(now).strftime("%Y%m")


def seconds_until_next_shanghai_midnight(now: datetime) -> int:
    shanghai_now = _to_shanghai(now)
    next_midnight = (
        shanghai_now.replace(hour=0, minute=0, second=0, microsecond=0)
        + timedelta(days=1)
    )
    return max(int((next_midnight - shanghai_now).total_seconds()), 1)


def quota_used_seconds_key(client_id: str, now: datetime) -> str:
    return f"{REDIS_KEY_PREFIX}:quota:{client_id}:{shanghai_day_key(now)}:used_seconds"


def active_sessions_key(client_id: str) -> str:
    return f"{REDIS_KEY_PREFIX}:active_sessions:{client_id}"


def budget_estimated_cost_key(now: datetime) -> str:
    return (
        f"{REDIS_KEY_PREFIX}:budget:{shanghai_month_key(now)}:estimated_cost_cents"
    )


def budget_fuse_key(now: datetime) -> str:
    return f"{REDIS_KEY_PREFIX}:budget:{shanghai_month_key(now)}:fuse_triggered"


def _decode_redis_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    msg = f"Unsupported Redis value type: {type(value).__name__}"
    raise TypeError(msg)


def _redis_int(value: object) -> int:
    decoded = _decode_redis_value(value)
    if decoded is None or decoded == "":
        return 0
    return int(decoded)


def _redis_bool(value: object) -> bool:
    return _decode_redis_value(value) == "1"


class QuotaPolicy:
    def __init__(self, settings: QuotaSettings) -> None:
        self._settings = settings

    def check_start(self, snapshot: QuotaSnapshot) -> QuotaDecision:
        remaining_seconds = self.remaining_seconds(snapshot.used_seconds_today)
        if self._is_budget_fuse_triggered(snapshot):
            return QuotaDecision(
                allowed=False,
                remaining_seconds_today=remaining_seconds,
                reason=QuotaDenialReason.BUDGET_FUSE_TRIGGERED,
            )
        if (
            snapshot.active_session_count
            >= self._settings.max_active_sessions_per_client
        ):
            return QuotaDecision(
                allowed=False,
                remaining_seconds_today=remaining_seconds,
                reason=QuotaDenialReason.ACTIVE_SESSION_LIMIT_REACHED,
            )
        if remaining_seconds <= 0:
            return QuotaDecision(
                allowed=False,
                remaining_seconds_today=0,
                reason=QuotaDenialReason.DAILY_QUOTA_EXHAUSTED,
            )
        return QuotaDecision(
            allowed=True,
            remaining_seconds_today=remaining_seconds,
            reason=None,
        )

    def check_session_duration(
        self,
        elapsed_seconds: int,
        used_seconds_today: int = 0,
    ) -> QuotaDecision:
        remaining_seconds = self.remaining_seconds(used_seconds_today)
        if elapsed_seconds >= self._settings.session_max_seconds:
            return QuotaDecision(
                allowed=False,
                remaining_seconds_today=remaining_seconds,
                reason=QuotaDenialReason.SESSION_TIME_LIMIT_REACHED,
            )
        return QuotaDecision(
            allowed=True,
            remaining_seconds_today=remaining_seconds,
            reason=None,
        )

    def remaining_seconds(self, used_seconds_today: int) -> int:
        return max(self._settings.daily_free_seconds - used_seconds_today, 0)

    def consumption_decision(self, used_seconds_today: int) -> QuotaDecision:
        remaining_seconds = self.remaining_seconds(used_seconds_today)
        if remaining_seconds <= 0:
            return QuotaDecision(
                allowed=False,
                remaining_seconds_today=0,
                reason=QuotaDenialReason.DAILY_QUOTA_EXHAUSTED,
            )
        return QuotaDecision(
            allowed=True,
            remaining_seconds_today=remaining_seconds,
            reason=None,
        )

    def _is_budget_fuse_triggered(self, snapshot: QuotaSnapshot) -> bool:
        threshold_cents = self._settings.budget_fuse_rmb * 100
        return (
            snapshot.budget_fuse_triggered
            or snapshot.budget_estimated_cost_cents >= threshold_cents
        )


class RedisQuotaStore:
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    async def get_snapshot(
        self,
        client_id: str,
        now: datetime,
        settings: QuotaSettings,
    ) -> QuotaSnapshot:
        active_key = active_sessions_key(client_id)
        await self._prune_active_sessions(active_key, now)

        used_seconds = _redis_int(
            await self._redis.get(quota_used_seconds_key(client_id, now)),
        )
        active_session_count = _redis_int(await self._redis.zcard(active_key))
        budget_estimated_cost_cents = _redis_int(
            await self._redis.get(budget_estimated_cost_key(now)),
        )
        budget_fuse_triggered = _redis_bool(
            await self._redis.get(budget_fuse_key(now)),
        )
        return QuotaSnapshot(
            used_seconds_today=used_seconds,
            active_session_count=active_session_count,
            budget_estimated_cost_cents=budget_estimated_cost_cents,
            budget_fuse_triggered=budget_fuse_triggered,
        )

    async def reserve_active_session(
        self,
        client_id: str,
        session_id: str,
        now: datetime,
        settings: QuotaSettings,
    ) -> QuotaDecision:
        policy = QuotaPolicy(settings)
        decision = policy.check_start(
            await self.get_snapshot(client_id, now, settings),
        )
        if not decision.allowed:
            return decision

        active_key = active_sessions_key(client_id)
        expires_at = _ensure_aware(now).timestamp() + settings.session_max_seconds
        await self._redis.zadd(active_key, {session_id: expires_at})
        await self._redis.expire(active_key, settings.session_max_seconds + 300)

        active_session_count = _redis_int(await self._redis.zcard(active_key))
        if active_session_count > settings.max_active_sessions_per_client:
            await self._redis.zrem(active_key, session_id)
            return QuotaDecision(
                allowed=False,
                remaining_seconds_today=decision.remaining_seconds_today,
                reason=QuotaDenialReason.ACTIVE_SESSION_LIMIT_REACHED,
            )
        return decision

    async def release_active_session(
        self,
        client_id: str,
        session_id: str,
    ) -> None:
        await self._redis.zrem(active_sessions_key(client_id), session_id)

    async def record_consumed_seconds(
        self,
        client_id: str,
        session_id: str,
        seconds: int,
        now: datetime,
        settings: QuotaSettings,
    ) -> int:
        quota_key = quota_used_seconds_key(client_id, now)
        current_used_seconds = _redis_int(await self._redis.get(quota_key))
        new_used_seconds = min(
            settings.daily_free_seconds,
            current_used_seconds + max(seconds, 0),
        )
        await self._redis.set(
            quota_key,
            new_used_seconds,
            ex=seconds_until_next_shanghai_midnight(now),
        )
        return new_used_seconds

    async def _prune_active_sessions(self, active_key: str, now: datetime) -> None:
        await self._redis.zremrangebyscore(
            active_key,
            "-inf",
            _ensure_aware(now).timestamp(),
        )


class QuotaService:
    def __init__(
        self,
        store: QuotaStateStore,
        settings: QuotaSettings,
        clock: Clock | None = None,
    ) -> None:
        self._store = store
        self._settings = settings
        self._policy = QuotaPolicy(settings)
        self._clock = clock or _now_utc

    async def check_start_allowed(self, client_id: str) -> QuotaDecision:
        now = self._clock()
        snapshot = await self._store.get_snapshot(client_id, now, self._settings)
        return self._policy.check_start(snapshot)

    async def reserve_active_session(
        self,
        client_id: str,
        session_id: str,
    ) -> QuotaDecision:
        return await self._store.reserve_active_session(
            client_id,
            session_id,
            self._clock(),
            self._settings,
        )

    async def release_active_session(self, client_id: str, session_id: str) -> None:
        await self._store.release_active_session(client_id, session_id)

    async def record_consumed_seconds(
        self,
        client_id: str,
        session_id: str,
        seconds: int,
    ) -> QuotaDecision:
        used_seconds_today = await self._store.record_consumed_seconds(
            client_id,
            session_id,
            seconds,
            self._clock(),
            self._settings,
        )
        return self._policy.consumption_decision(used_seconds_today)

    def check_session_duration(
        self,
        elapsed_seconds: int,
        used_seconds_today: int = 0,
    ) -> QuotaDecision:
        return self._policy.check_session_duration(
            elapsed_seconds,
            used_seconds_today,
        )
