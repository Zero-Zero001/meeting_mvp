from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from meeting_mvp_backend.config import Settings
from meeting_mvp_backend.db.models import MeetingSessionStatus, SourcePlatform
from meeting_mvp_backend.main import app, get_app_settings, get_usage_dashboard_service
from meeting_mvp_backend.usage_dashboard import (
    DashboardMeetingSessionRecord,
    DashboardUsageEventRecord,
    UsageDashboardRecords,
    UsageDashboardResponse,
    UsageDashboardService,
)

FIXED_NOW = datetime(2026, 5, 17, 4, 0, tzinfo=UTC)


@dataclass
class FakeUsageDashboardRepository:
    records: UsageDashboardRecords

    async def list_records(
        self,
        *,
        end_at: datetime,
        start_at: datetime,
    ) -> UsageDashboardRecords:
        assert start_at <= end_at
        return self.records


class FakeUsageDashboardService:
    def __init__(self, response: UsageDashboardResponse) -> None:
        self.response = response
        self.calls: list[int] = []

    async def build_dashboard(self, *, days: int) -> UsageDashboardResponse:
        self.calls.append(days)
        return self.response


@pytest.fixture(autouse=True)
async def reset_dependency_overrides() -> Any:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def dashboard_settings(**overrides: object) -> Settings:
    values: dict[str, Any] = {
        "DASHBOARD_ADMIN_TOKEN": "admin-secret",
        "DASHBOARD_QWEN_ASR_USD_PER_SECOND": 0.00009,
        "DASHBOARD_QWEN_TEXT_INPUT_USD_PER_1M_TOKENS": 0.861,
        "DASHBOARD_QWEN_TEXT_OUTPUT_USD_PER_1M_TOKENS": 3.441,
        "DASHBOARD_USD_TO_RMB": 7.2,
        "MONTHLY_BUDGET_RMB": 500,
        "BUDGET_FUSE_RMB": 400,
    }
    values.update(overrides)
    return Settings(**values)


def sample_records() -> UsageDashboardRecords:
    session_1 = uuid.UUID("11111111-1111-4111-8111-111111111111")
    session_2 = uuid.UUID("22222222-2222-4222-8222-222222222222")
    session_3 = uuid.UUID("33333333-3333-4333-8333-333333333333")
    return UsageDashboardRecords(
        sessions=[
            DashboardMeetingSessionRecord(
                client_id="client-a",
                duration_seconds=300,
                quota_seconds_consumed=300,
                session_id=session_1,
                source_platform=SourcePlatform.TENCENT_MEETING_WEB,
                started_at=datetime(2026, 5, 16, 2, 0, tzinfo=UTC),
                status=MeetingSessionStatus.ENDED,
            ),
            DashboardMeetingSessionRecord(
                client_id="client-b",
                duration_seconds=0,
                quota_seconds_consumed=0,
                session_id=session_2,
                source_platform=SourcePlatform.TENCENT_MEETING_WEB,
                started_at=datetime(2026, 5, 16, 3, 0, tzinfo=UTC),
                status=MeetingSessionStatus.ERROR,
            ),
            DashboardMeetingSessionRecord(
                client_id="client-a",
                duration_seconds=120,
                quota_seconds_consumed=120,
                session_id=session_3,
                source_platform=SourcePlatform.GOOGLE_MEET,
                started_at=datetime(2026, 5, 17, 1, 0, tzinfo=UTC),
                status=MeetingSessionStatus.ENDED,
            ),
        ],
        usage_events=[
            event("client-a", None, "client_created", {}, "2026-05-16T01:00:00Z"),
            event("client-b", None, "client_created", {}, "2026-05-16T01:05:00Z"),
            event("client-a", session_1, "capture_started", {}, "2026-05-16T02:00:01Z"),
            event("client-b", session_2, "capture_started", {}, "2026-05-16T03:00:01Z"),
            event("client-a", session_1, "audio_detected", {}, "2026-05-16T02:00:05Z"),
            event("client-a", session_1, "session_started", {}, "2026-05-16T02:00:00Z"),
            event("client-b", session_2, "session_started", {}, "2026-05-16T03:00:00Z"),
            event("client-a", session_3, "session_started", {}, "2026-05-17T01:00:00Z"),
            event(
                "client-a",
                session_1,
                "translation_interim_requested",
                {"text_length": 40},
                "2026-05-16T02:00:10Z",
            ),
            event(
                "client-a",
                session_1,
                "translation_interim_requested",
                {"text_length": 40},
                "2026-05-16T02:00:12Z",
            ),
            event(
                "client-a",
                session_1,
                "asr_final_received",
                {"text_length": 80},
                "2026-05-16T02:00:20Z",
            ),
            event(
                "client-a",
                session_1,
                "translation_final_completed",
                {
                    "chinese_text_length": 36,
                    "english_text_length": 80,
                    "latency_ms": 1800,
                    "sequence": 1,
                },
                "2026-05-16T02:00:22Z",
            ),
            event(
                "client-a",
                session_1,
                "segment_archived",
                {
                    "chinese_text_length": 36,
                    "english_text_length": 80,
                    "segment_id": str(uuid.uuid4()),
                    "sequence": 1,
                },
                "2026-05-16T02:00:23Z",
            ),
            event("client-a", session_1, "archive_viewed", {}, "2026-05-16T02:10:00Z"),
            event(
                "client-a",
                session_1,
                "archive_searched",
                {"query_length": 5},
                "2026-05-16T02:11:00Z",
            ),
            event(
                "client-a",
                session_1,
                "segment_copied",
                {"segment_id": str(uuid.uuid4()), "sequence": 1},
                "2026-05-16T02:12:00Z",
            ),
            event(
                "client-a",
                session_1,
                "export_created",
                {"format": "markdown", "segment_count": 1},
                "2026-05-16T02:13:00Z",
            ),
            event(
                "client-b",
                session_2,
                "provider_error",
                {"code": "qwen_asr_error", "provider": "qwen_asr"},
                "2026-05-16T03:01:00Z",
            ),
            event(
                "client-c",
                None,
                "budget_fuse_triggered",
                {"reason": "monthly_budget"},
                "2026-05-16T04:01:00Z",
            ),
            event(
                "client-old",
                None,
                "client_created",
                {},
                "2026-04-30T12:00:00Z",
            ),
        ],
    )


def event(
    client_id: str,
    session_id: uuid.UUID | None,
    event_type: str,
    payload: dict[str, object],
    created_at: str,
) -> DashboardUsageEventRecord:
    return DashboardUsageEventRecord(
        client_id=client_id,
        created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")),
        event_id=uuid.uuid4(),
        event_type=event_type,
        payload=payload,
        session_id=session_id,
    )


@pytest.mark.asyncio
async def test_usage_dashboard_aggregates_usage_cost_and_funnels() -> None:
    service = UsageDashboardService(
        clock=lambda: FIXED_NOW,
        repository=FakeUsageDashboardRepository(sample_records()),
        settings=dashboard_settings(),
    )

    dashboard = await service.build_dashboard(days=7)

    assert dashboard.days == 7
    assert dashboard.timezone == "Asia/Shanghai"
    assert dashboard.window_start_date.isoformat() == "2026-05-11"
    assert dashboard.window_end_date.isoformat() == "2026-05-17"
    assert dashboard.totals.meetings == 3
    assert dashboard.totals.effective_meetings == 2
    assert dashboard.totals.active_clients == 2
    assert dashboard.totals.asr_minutes == pytest.approx(7.0)
    assert dashboard.totals.qwen_interim_requests == 2
    assert dashboard.totals.qwen_final_requests == 1
    assert dashboard.totals.qwen_estimated_input_tokens == 40
    assert dashboard.totals.qwen_estimated_output_tokens == 9
    assert dashboard.totals.exports_created == 1
    assert dashboard.totals.errors == 2
    assert dashboard.quality.tencent_meeting_success_rate == pytest.approx(0.5)
    assert dashboard.quality.avg_final_latency_ms == pytest.approx(1800)
    assert dashboard.cost.estimated_current_month_cost_rmb == pytest.approx(
        0.2726,
        abs=0.0001,
    )
    assert dashboard.cost.budget_fuse_rmb == 400
    assert dashboard.cost.monthly_budget_rmb == 500
    assert dashboard.cost.is_estimate is True
    may_16 = next(
        item for item in dashboard.daily if item.date.isoformat() == "2026-05-16"
    )
    assert may_16.meetings == 2
    assert may_16.effective_meetings == 1
    assert may_16.active_clients == 2
    assert may_16.asr_minutes == pytest.approx(5.0)
    assert may_16.qwen_estimated_input_tokens == 40
    assert may_16.qwen_estimated_output_tokens == 9
    assert may_16.estimated_cost_rmb == pytest.approx(0.1949, abs=0.0001)
    assert dashboard.funnels.first_use.audio_detected == 1
    assert dashboard.funnels.first_use.capture_to_audio_rate == pytest.approx(0.5)
    assert dashboard.funnels.value_validation.exports_created == 1


@pytest.mark.asyncio
async def test_usage_dashboard_response_excludes_sensitive_values() -> None:
    service = UsageDashboardService(
        clock=lambda: FIXED_NOW,
        repository=FakeUsageDashboardRepository(sample_records()),
        settings=dashboard_settings(),
    )

    payload = (await service.build_dashboard(days=7)).model_dump_json()

    assert "admin-secret" not in payload
    assert "archive-token" not in payload
    assert "download_url" not in payload
    assert "cos_object_key" not in payload
    assert "english_text_final" not in payload
    assert "chinese_text_final" not in payload


@pytest.mark.asyncio
async def test_usage_dashboard_endpoint_requires_bearer_admin_token() -> None:
    response_model = await UsageDashboardService(
        clock=lambda: FIXED_NOW,
        repository=FakeUsageDashboardRepository(sample_records()),
        settings=dashboard_settings(),
    ).build_dashboard(days=7)
    service = FakeUsageDashboardService(response_model)
    app.dependency_overrides[get_app_settings] = lambda: dashboard_settings()
    app.dependency_overrides[get_usage_dashboard_service] = lambda: service
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        missing = await client.get("/api/admin/usage-dashboard?days=7")
        query_token = await client.get(
            "/api/admin/usage-dashboard?days=7&token=admin-secret",
        )
        wrong = await client.get(
            "/api/admin/usage-dashboard?days=7",
            headers={"Authorization": "Bearer wrong-token"},
        )
        ok = await client.get(
            "/api/admin/usage-dashboard?days=7",
            headers={"Authorization": "Bearer admin-secret"},
        )

    assert missing.status_code == 401
    assert query_token.status_code == 401
    assert wrong.status_code == 401
    assert ok.status_code == 200
    assert ok.json()["days"] == 7
    assert service.calls == [7]


@pytest.mark.asyncio
async def test_usage_dashboard_endpoint_returns_503_when_admin_token_unconfigured(
) -> None:
    app.dependency_overrides[get_app_settings] = lambda: dashboard_settings(
        DASHBOARD_ADMIN_TOKEN="",
    )
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/admin/usage-dashboard",
            headers={"Authorization": "Bearer any-value"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Usage dashboard is not configured"}
