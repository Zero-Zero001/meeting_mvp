from __future__ import annotations

import math
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.db.models import (
    MeetingSession,
    MeetingSessionStatus,
    SourcePlatform,
    UsageEvent,
)
from meeting_mvp_backend.usage_events import UsageEventType

Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class DashboardMeetingSessionRecord:
    session_id: uuid.UUID
    client_id: str
    source_platform: SourcePlatform
    status: MeetingSessionStatus
    started_at: datetime | None
    duration_seconds: int
    quota_seconds_consumed: int


@dataclass(frozen=True, slots=True)
class DashboardUsageEventRecord:
    event_id: uuid.UUID
    client_id: str
    session_id: uuid.UUID | None
    event_type: str
    payload: dict[str, object]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class UsageDashboardRecords:
    sessions: list[DashboardMeetingSessionRecord]
    usage_events: list[DashboardUsageEventRecord]


class UsageDashboardRepository(Protocol):
    async def list_records(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> UsageDashboardRecords: ...


class UsageDashboardDailyMetric(BaseModel):
    date: date
    meetings: int
    effective_meetings: int
    active_clients: int
    asr_minutes: float
    qwen_interim_requests: int
    qwen_final_requests: int
    qwen_estimated_input_tokens: int
    qwen_estimated_output_tokens: int
    exports_created: int
    errors: int
    budget_fuse_triggered: int
    estimated_cost_rmb: float


class UsageDashboardTotals(BaseModel):
    meetings: int
    effective_meetings: int
    active_clients: int
    asr_minutes: float
    qwen_interim_requests: int
    qwen_final_requests: int
    qwen_estimated_input_tokens: int
    qwen_estimated_output_tokens: int
    exports_created: int
    errors: int
    budget_fuse_triggered: int
    estimated_cost_rmb: float


class UsageDashboardFirstUseFunnel(BaseModel):
    client_created: int
    capture_started: int
    audio_detected: int
    session_started: int
    first_final_seen: int
    capture_to_audio_rate: float


class UsageDashboardMeetingQualityFunnel(BaseModel):
    session_started: int
    audio_detected: int
    asr_final_received: int
    translation_final_completed: int
    segment_archived: int
    archive_viewed: int


class UsageDashboardValueValidationFunnel(BaseModel):
    archive_viewed: int
    archive_searched: int
    segment_copied: int
    exports_created: int
    key_sentences_marked: int


class UsageDashboardFunnels(BaseModel):
    first_use: UsageDashboardFirstUseFunnel
    meeting_quality: UsageDashboardMeetingQualityFunnel
    value_validation: UsageDashboardValueValidationFunnel


class UsageDashboardQuality(BaseModel):
    provider_errors: int
    quota_exhausted: int
    budget_fuse_triggered: int
    avg_interim_latency_ms: float | None
    avg_final_latency_ms: float | None
    tencent_meeting_sessions: int
    tencent_meeting_successful_sessions: int
    tencent_meeting_success_rate: float


class UsageDashboardCost(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    estimated_current_month_cost_rmb: float
    monthly_budget_rmb: int
    budget_fuse_rmb: int
    budget_usage_percent: float
    is_estimate: bool = True


class UsageDashboardResponse(BaseModel):
    generated_at: datetime
    timezone: str
    days: int = Field(ge=1, le=90)
    window_start_date: date
    window_end_date: date
    totals: UsageDashboardTotals
    daily: list[UsageDashboardDailyMetric]
    funnels: UsageDashboardFunnels
    quality: UsageDashboardQuality
    cost: UsageDashboardCost


class SQLAlchemyUsageDashboardRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def list_records(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> UsageDashboardRecords:
        async with self._session_factory() as session:
            sessions_result = await session.scalars(
                select(MeetingSession).where(
                    MeetingSession.started_at >= start_at,
                    MeetingSession.started_at < end_at,
                ),
            )
            usage_events_result = await session.scalars(
                select(UsageEvent).where(
                    UsageEvent.created_at >= start_at,
                    UsageEvent.created_at < end_at,
                ),
            )
            sessions = list(sessions_result)
            usage_events = list(usage_events_result)

        return UsageDashboardRecords(
            sessions=[
                DashboardMeetingSessionRecord(
                    client_id=session_model.client_id,
                    duration_seconds=session_model.duration_seconds,
                    quota_seconds_consumed=session_model.quota_seconds_consumed,
                    session_id=session_model.id,
                    source_platform=session_model.source_platform,
                    started_at=session_model.started_at,
                    status=session_model.status,
                )
                for session_model in sessions
            ],
            usage_events=[
                DashboardUsageEventRecord(
                    client_id=event_model.client_id,
                    created_at=event_model.created_at,
                    event_id=event_model.id,
                    event_type=event_model.event_type,
                    payload=(
                        event_model.payload
                        if isinstance(event_model.payload, dict)
                        else {}
                    ),
                    session_id=event_model.session_id,
                )
                for event_model in usage_events
            ],
        )


class UsageDashboardService:
    def __init__(
        self,
        *,
        repository: UsageDashboardRepository,
        settings: Settings,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._clock = clock or _now_utc

    async def build_dashboard(self, *, days: int) -> UsageDashboardResponse:
        if days < 1 or days > 90:
            msg = "Usage dashboard days must be between 1 and 90"
            raise ValueError(msg)

        timezone = ZoneInfo(self._settings.app_timezone)
        generated_at = _ensure_aware(self._clock())
        local_today = generated_at.astimezone(timezone).date()
        window_start_date = local_today - timedelta(days=days - 1)
        month_start_date = local_today.replace(day=1)
        query_start_date = min(window_start_date, month_start_date)
        query_start_at = _local_start_to_utc(query_start_date, timezone)
        query_end_at = _local_start_to_utc(local_today + timedelta(days=1), timezone)

        records = await self._repository.list_records(
            start_at=query_start_at,
            end_at=query_end_at,
        )
        window_sessions = [
            session
            for session in records.sessions
            if _record_date(session.started_at, timezone) in _date_range_set(
                window_start_date,
                local_today,
            )
        ]
        window_events = [
            event
            for event in records.usage_events
            if _record_date(event.created_at, timezone) in _date_range_set(
                window_start_date,
                local_today,
            )
        ]
        month_sessions = [
            session
            for session in records.sessions
            if _date_in_range(
                _record_date(session.started_at, timezone),
                month_start_date,
                local_today,
            )
        ]
        month_events = [
            event
            for event in records.usage_events
            if _date_in_range(
                _record_date(event.created_at, timezone),
                month_start_date,
                local_today,
            )
        ]

        daily = [
            _daily_metric(
                current_date=current_date,
                events=[
                    event
                    for event in window_events
                    if _record_date(event.created_at, timezone) == current_date
                ],
                sessions=[
                    session
                    for session in window_sessions
                    if _record_date(session.started_at, timezone) == current_date
                ],
                settings=self._settings,
            )
            for current_date in _date_range(window_start_date, local_today)
        ]
        totals = _totals(
            active_clients=len({session.client_id for session in window_sessions}),
            metrics=daily,
        )
        monthly_cost = _estimated_cost_rmb(
            events=month_events,
            sessions=month_sessions,
            settings=self._settings,
        )

        return UsageDashboardResponse(
            cost=UsageDashboardCost(
                budget_fuse_rmb=self._settings.budget_fuse_rmb,
                budget_usage_percent=_rate(
                    monthly_cost,
                    self._settings.budget_fuse_rmb,
                ),
                estimated_current_month_cost_rmb=monthly_cost,
                is_estimate=True,
                monthly_budget_rmb=self._settings.monthly_budget_rmb,
            ),
            daily=daily,
            days=days,
            funnels=_funnels(window_events),
            generated_at=generated_at,
            quality=_quality(window_events, window_sessions),
            timezone=self._settings.app_timezone,
            totals=totals,
            window_end_date=local_today,
            window_start_date=window_start_date,
        )


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _local_start_to_utc(value: date, timezone: ZoneInfo) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone).astimezone(UTC)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _record_date(value: datetime | None, timezone: ZoneInfo) -> date | None:
    if value is None:
        return None
    return _ensure_aware(value).astimezone(timezone).date()


def _date_in_range(value: date | None, start_date: date, end_date: date) -> bool:
    return value is not None and start_date <= value <= end_date


def _date_range(start_date: date, end_date: date) -> Iterable[date]:
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _date_range_set(start_date: date, end_date: date) -> set[date]:
    return set(_date_range(start_date, end_date))


def _daily_metric(
    *,
    current_date: date,
    events: list[DashboardUsageEventRecord],
    sessions: list[DashboardMeetingSessionRecord],
    settings: Settings,
) -> UsageDashboardDailyMetric:
    token_metrics = _token_metrics(events)
    return UsageDashboardDailyMetric(
        active_clients=len({session.client_id for session in sessions}),
        asr_minutes=round(_asr_seconds(sessions) / 60, 4),
        budget_fuse_triggered=_count_events(
            events,
            UsageEventType.BUDGET_FUSE_TRIGGERED,
        ),
        date=current_date,
        effective_meetings=sum(1 for session in sessions if _is_effective(session)),
        errors=_error_count(events),
        estimated_cost_rmb=_estimated_cost_rmb(
            events=events,
            sessions=sessions,
            settings=settings,
        ),
        exports_created=_count_events(events, UsageEventType.EXPORT_CREATED),
        meetings=len(sessions),
        qwen_estimated_input_tokens=token_metrics[0],
        qwen_estimated_output_tokens=token_metrics[1],
        qwen_final_requests=_count_events(
            events,
            UsageEventType.TRANSLATION_FINAL_COMPLETED,
        ),
        qwen_interim_requests=_count_events(
            events,
            UsageEventType.TRANSLATION_INTERIM_REQUESTED,
        ),
    )


def _totals(
    *,
    active_clients: int,
    metrics: list[UsageDashboardDailyMetric],
) -> UsageDashboardTotals:
    return UsageDashboardTotals(
        active_clients=active_clients,
        asr_minutes=round(sum(metric.asr_minutes for metric in metrics), 4),
        budget_fuse_triggered=sum(metric.budget_fuse_triggered for metric in metrics),
        effective_meetings=sum(metric.effective_meetings for metric in metrics),
        errors=sum(metric.errors for metric in metrics),
        estimated_cost_rmb=round(
            sum(metric.estimated_cost_rmb for metric in metrics),
            4,
        ),
        exports_created=sum(metric.exports_created for metric in metrics),
        meetings=sum(metric.meetings for metric in metrics),
        qwen_estimated_input_tokens=sum(
            metric.qwen_estimated_input_tokens for metric in metrics
        ),
        qwen_estimated_output_tokens=sum(
            metric.qwen_estimated_output_tokens for metric in metrics
        ),
        qwen_final_requests=sum(metric.qwen_final_requests for metric in metrics),
        qwen_interim_requests=sum(metric.qwen_interim_requests for metric in metrics),
    )


def _funnels(events: list[DashboardUsageEventRecord]) -> UsageDashboardFunnels:
    capture_started = _count_events(events, UsageEventType.CAPTURE_STARTED)
    audio_detected = _count_events(events, UsageEventType.AUDIO_DETECTED)
    return UsageDashboardFunnels(
        first_use=UsageDashboardFirstUseFunnel(
            audio_detected=audio_detected,
            capture_started=capture_started,
            capture_to_audio_rate=_rate(audio_detected, capture_started),
            client_created=len(
                {
                    event.client_id
                    for event in events
                    if event.event_type == UsageEventType.CLIENT_CREATED.value
                },
            ),
            first_final_seen=_count_events(events, UsageEventType.SEGMENT_ARCHIVED),
            session_started=_count_events(events, UsageEventType.SESSION_STARTED),
        ),
        meeting_quality=UsageDashboardMeetingQualityFunnel(
            archive_viewed=_count_events(events, UsageEventType.ARCHIVE_VIEWED),
            asr_final_received=_count_events(events, UsageEventType.ASR_FINAL_RECEIVED),
            audio_detected=audio_detected,
            segment_archived=_count_events(events, UsageEventType.SEGMENT_ARCHIVED),
            session_started=_count_events(events, UsageEventType.SESSION_STARTED),
            translation_final_completed=_count_events(
                events,
                UsageEventType.TRANSLATION_FINAL_COMPLETED,
            ),
        ),
        value_validation=UsageDashboardValueValidationFunnel(
            archive_searched=_count_events(events, UsageEventType.ARCHIVE_SEARCHED),
            archive_viewed=_count_events(events, UsageEventType.ARCHIVE_VIEWED),
            exports_created=_count_events(events, UsageEventType.EXPORT_CREATED),
            key_sentences_marked=_count_events(
                events,
                UsageEventType.KEY_SENTENCE_MARKED,
            ),
            segment_copied=_count_events(events, UsageEventType.SEGMENT_COPIED),
        ),
    )


def _quality(
    events: list[DashboardUsageEventRecord],
    sessions: list[DashboardMeetingSessionRecord],
) -> UsageDashboardQuality:
    tencent_sessions = [
        session
        for session in sessions
        if session.source_platform is SourcePlatform.TENCENT_MEETING_WEB
    ]
    tencent_successful_sessions = [
        session
        for session in tencent_sessions
        if session.status is MeetingSessionStatus.ENDED and _is_effective(session)
    ]
    return UsageDashboardQuality(
        avg_final_latency_ms=_average_payload_number(
            events,
            UsageEventType.TRANSLATION_FINAL_COMPLETED,
            ("latency_ms", "duration_ms", "request_latency_ms"),
        ),
        avg_interim_latency_ms=_average_payload_number(
            events,
            UsageEventType.TRANSLATION_INTERIM_REQUESTED,
            ("latency_ms", "duration_ms", "request_latency_ms"),
        ),
        budget_fuse_triggered=_count_events(
            events,
            UsageEventType.BUDGET_FUSE_TRIGGERED,
        ),
        provider_errors=_count_events(events, UsageEventType.PROVIDER_ERROR),
        quota_exhausted=_count_events(events, UsageEventType.QUOTA_EXHAUSTED),
        tencent_meeting_sessions=len(tencent_sessions),
        tencent_meeting_success_rate=_rate(
            len(tencent_successful_sessions),
            len(tencent_sessions),
        ),
        tencent_meeting_successful_sessions=len(tencent_successful_sessions),
    )


def _estimated_cost_rmb(
    *,
    events: list[DashboardUsageEventRecord],
    sessions: list[DashboardMeetingSessionRecord],
    settings: Settings,
) -> float:
    input_tokens, output_tokens = _token_metrics(events)
    asr_cost_usd = _asr_seconds(sessions) * settings.dashboard_qwen_asr_usd_per_second
    input_cost_usd = (
        input_tokens / 1_000_000
    ) * settings.dashboard_qwen_text_input_usd_per_1m_tokens
    output_cost_usd = (
        output_tokens / 1_000_000
    ) * settings.dashboard_qwen_text_output_usd_per_1m_tokens
    return round(
        (asr_cost_usd + input_cost_usd + output_cost_usd)
        * settings.dashboard_usd_to_rmb,
        4,
    )


def _token_metrics(events: list[DashboardUsageEventRecord]) -> tuple[int, int]:
    input_tokens = 0
    output_tokens = 0
    for event in events:
        if event.event_type == UsageEventType.TRANSLATION_INTERIM_REQUESTED.value:
            input_tokens += _estimated_tokens_from_payload(event.payload, "text_length")
        elif event.event_type == UsageEventType.TRANSLATION_FINAL_COMPLETED.value:
            input_tokens += _estimated_tokens_from_payload(
                event.payload,
                "english_text_length",
            )
            output_tokens += _estimated_tokens_from_payload(
                event.payload,
                "chinese_text_length",
            )
    return input_tokens, output_tokens


def _estimated_tokens_from_payload(
    payload: Mapping[str, object],
    key: str,
) -> int:
    raw_value = payload.get(key)
    if not isinstance(raw_value, int | float) or raw_value <= 0:
        return 0
    return math.ceil(raw_value / 4)


def _asr_seconds(sessions: list[DashboardMeetingSessionRecord]) -> int:
    return sum(
        max(session.duration_seconds, session.quota_seconds_consumed, 0)
        for session in sessions
    )


def _is_effective(session: DashboardMeetingSessionRecord) -> bool:
    return max(session.duration_seconds, session.quota_seconds_consumed, 0) > 0


def _count_events(
    events: list[DashboardUsageEventRecord],
    event_type: UsageEventType,
) -> int:
    return sum(1 for event in events if event.event_type == event_type.value)


def _error_count(events: list[DashboardUsageEventRecord]) -> int:
    error_types = {
        UsageEventType.BUDGET_FUSE_TRIGGERED.value,
        UsageEventType.CAPTURE_FAILED.value,
        UsageEventType.EXPORT_FAILED.value,
        UsageEventType.PROVIDER_ERROR.value,
        UsageEventType.QUOTA_EXHAUSTED.value,
    }
    return sum(1 for event in events if event.event_type in error_types)


def _rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0
    return round(numerator / denominator, 4)


def _average_payload_number(
    events: list[DashboardUsageEventRecord],
    event_type: UsageEventType,
    keys: tuple[str, ...],
) -> float | None:
    values: list[float] = []
    for event in events:
        if event.event_type != event_type.value:
            continue
        for key in keys:
            raw_value = event.payload.get(key)
            if isinstance(raw_value, int | float) and raw_value >= 0:
                values.append(float(raw_value))
                break
    if not values:
        return None
    return round(sum(values) / len(values), 4)
