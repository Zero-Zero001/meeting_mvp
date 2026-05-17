import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import UsageDashboardPage from './UsageDashboardPage'
import {
  UsageDashboardAccessError,
  type UsageDashboardResponse,
} from '@/api/usage-dashboard'

const dashboardResponse: UsageDashboardResponse = {
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

describe('UsageDashboardPage', () => {
  it('loads metrics after entering the admin token without writing storage', async () => {
    const user = userEvent.setup()
    const fetchUsageDashboardFn = vi.fn().mockResolvedValue(dashboardResponse)
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')

    render(
      <UsageDashboardPage fetchUsageDashboardFn={fetchUsageDashboardFn} />,
    )

    expect(screen.getByLabelText('管理口令')).toHaveAttribute('type', 'password')
    expect(screen.queryByText('核心指标')).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('管理口令'), 'admin-secret')
    await user.click(screen.getByRole('button', { name: '加载看板' }))

    expect(fetchUsageDashboardFn).toHaveBeenCalledWith({
      adminToken: 'admin-secret',
      days: 30,
    })
    expect(await screen.findByText('核心指标')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('¥0.2726')).toBeInTheDocument()
    expect(setItemSpy).not.toHaveBeenCalled()
    setItemSpy.mockRestore()
  })

  it('switches between 7, 30, and 90 day windows using the same in-memory token', async () => {
    const user = userEvent.setup()
    const fetchUsageDashboardFn = vi.fn().mockResolvedValue(dashboardResponse)

    render(
      <UsageDashboardPage fetchUsageDashboardFn={fetchUsageDashboardFn} />,
    )

    await user.type(screen.getByLabelText('管理口令'), 'admin-secret')
    await user.click(screen.getByRole('button', { name: '加载看板' }))
    await screen.findByText('核心指标')
    await user.click(screen.getByRole('button', { name: '7 天' }))
    await user.click(screen.getByRole('button', { name: '90 天' }))

    expect(fetchUsageDashboardFn).toHaveBeenNthCalledWith(2, {
      adminToken: 'admin-secret',
      days: 7,
    })
    expect(fetchUsageDashboardFn).toHaveBeenNthCalledWith(3, {
      adminToken: 'admin-secret',
      days: 90,
    })
  })

  it('renders daily trends, funnels, quality, and cost sections', async () => {
    const user = userEvent.setup()

    render(
      <UsageDashboardPage
        fetchUsageDashboardFn={vi.fn().mockResolvedValue(dashboardResponse)}
      />,
    )

    await user.type(screen.getByLabelText('管理口令'), 'admin-secret')
    await user.click(screen.getByRole('button', { name: '加载看板' }))

    expect(await screen.findByText('每日趋势')).toBeInTheDocument()
    expect(screen.getByText('首次使用漏斗')).toBeInTheDocument()
    expect(screen.getByText('会议质量漏斗')).toBeInTheDocument()
    expect(screen.getByText('价值验证漏斗')).toBeInTheDocument()
    expect(screen.getByText('错误与质量')).toBeInTheDocument()
    const costRegion = within(screen.getByRole('region', { name: '成本与预算' }))
    expect(costRegion.getByText('¥0.2726')).toBeInTheDocument()
    expect(costRegion.getByText('400 RMB')).toBeInTheDocument()
  })

  it('shows accessible guidance for auth, missing config, and network errors', async () => {
    const user = userEvent.setup()
    const fetchUsageDashboardFn = vi
      .fn()
      .mockRejectedValueOnce(
        new UsageDashboardAccessError({
          message: 'Invalid dashboard admin token',
          status: 401,
        }),
      )
      .mockRejectedValueOnce(
        new UsageDashboardAccessError({
          message: 'Usage dashboard is not configured',
          status: 503,
        }),
      )
      .mockRejectedValueOnce(new Error('network down'))

    render(
      <UsageDashboardPage fetchUsageDashboardFn={fetchUsageDashboardFn} />,
    )

    await user.type(screen.getByLabelText('管理口令'), 'wrong')
    await user.click(screen.getByRole('button', { name: '加载看板' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('管理口令无效')

    await user.click(screen.getByRole('button', { name: '加载看板' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('看板未配置')

    await user.click(screen.getByRole('button', { name: '加载看板' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      '看板暂时无法加载',
    )
  })
})
