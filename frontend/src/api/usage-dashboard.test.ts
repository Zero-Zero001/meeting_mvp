import { describe, expect, it, vi } from 'vitest'

import {
  UsageDashboardAccessError,
  buildUsageDashboardApiUrl,
  fetchUsageDashboard,
} from './usage-dashboard'

const dashboardPayload = {
  cost: {
    budget_fuse_rmb: 400,
    budget_usage_percent: 0.07,
    estimated_current_month_cost_rmb: 0.2726,
    is_estimate: true,
    monthly_budget_rmb: 500,
  },
  daily: [
    {
      active_clients: 2,
      asr_minutes: 5,
      budget_fuse_triggered: 1,
      date: '2026-05-16',
      effective_meetings: 1,
      errors: 2,
      estimated_cost_rmb: 0.1949,
      exports_created: 1,
      meetings: 2,
      qwen_estimated_input_tokens: 40,
      qwen_estimated_output_tokens: 9,
      qwen_final_requests: 1,
      qwen_interim_requests: 2,
    },
  ],
  days: 7,
  funnels: {
    first_use: {
      audio_detected: 1,
      capture_started: 2,
      capture_to_audio_rate: 0.5,
      client_created: 2,
      first_final_seen: 1,
      session_started: 3,
    },
    meeting_quality: {
      archive_viewed: 1,
      asr_final_received: 1,
      audio_detected: 1,
      segment_archived: 1,
      session_started: 3,
      translation_final_completed: 1,
    },
    value_validation: {
      archive_searched: 1,
      archive_viewed: 1,
      exports_created: 1,
      key_sentences_marked: 0,
      segment_copied: 1,
    },
  },
  generated_at: '2026-05-17T04:00:00Z',
  quality: {
    avg_final_latency_ms: 1800,
    avg_interim_latency_ms: null,
    budget_fuse_triggered: 1,
    provider_errors: 1,
    quota_exhausted: 0,
    tencent_meeting_sessions: 2,
    tencent_meeting_success_rate: 0.5,
    tencent_meeting_successful_sessions: 1,
  },
  timezone: 'Asia/Shanghai',
  totals: {
    active_clients: 2,
    asr_minutes: 7,
    budget_fuse_triggered: 1,
    effective_meetings: 2,
    errors: 2,
    estimated_cost_rmb: 0.2726,
    exports_created: 1,
    meetings: 3,
    qwen_estimated_input_tokens: 40,
    qwen_estimated_output_tokens: 9,
    qwen_final_requests: 1,
    qwen_interim_requests: 2,
  },
  window_end_date: '2026-05-17',
  window_start_date: '2026-05-11',
}

describe('usage dashboard API', () => {
  it('builds dashboard URLs with days but without admin token', () => {
    expect(
      buildUsageDashboardApiUrl({
        apiBaseUrl: 'https://api.example.test/',
        days: 30,
      }),
    ).toBe('https://api.example.test/api/admin/usage-dashboard?days=30')
  })

  it('fetches dashboard metrics with bearer authorization header', async () => {
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(dashboardPayload), {
        headers: { 'content-type': 'application/json' },
        status: 200,
      }),
    )

    const dashboard = await fetchUsageDashboard({
      adminToken: 'admin-secret',
      apiBaseUrl: '',
      days: 7,
      fetchFn,
    })

    expect(fetchFn).toHaveBeenCalledWith(
      '/api/admin/usage-dashboard?days=7',
      expect.objectContaining({
        headers: { Authorization: 'Bearer admin-secret' },
        method: 'GET',
      }),
    )
    expect(dashboard.days).toBe(7)
    expect(dashboard.totals.meetings).toBe(3)
    expect(dashboard.cost.is_estimate).toBe(true)
    const [, init] = fetchFn.mock.calls[0]
    expect(String(fetchFn.mock.calls[0][0])).not.toContain('admin-secret')
    expect('body' in init).toBe(false)
  })

  it('reports 401 and 503 responses as typed access errors', async () => {
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Invalid dashboard admin token' }), {
        headers: { 'content-type': 'application/json' },
        status: 401,
      }),
    )

    await expect(
      fetchUsageDashboard({
        adminToken: 'wrong',
        days: 30,
        fetchFn,
      }),
    ).rejects.toMatchObject(
      new UsageDashboardAccessError({
        message: 'Invalid dashboard admin token',
        status: 401,
      }),
    )
  })

  it('rejects invalid day ranges before making a request', async () => {
    const fetchFn = vi.fn()

    await expect(
      fetchUsageDashboard({
        adminToken: 'admin-secret',
        days: 91,
        fetchFn,
      }),
    ).rejects.toThrow('Usage dashboard days must be between 1 and 90')
    expect(fetchFn).not.toHaveBeenCalled()
  })
})
