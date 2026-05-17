import { z } from 'zod'

import { publicConfig } from '@/config/public-config'

const dailyMetricSchema = z.object({
  date: z.string(),
  meetings: z.number().int().nonnegative(),
  effective_meetings: z.number().int().nonnegative(),
  active_clients: z.number().int().nonnegative(),
  asr_minutes: z.number().nonnegative(),
  qwen_interim_requests: z.number().int().nonnegative(),
  qwen_final_requests: z.number().int().nonnegative(),
  qwen_estimated_input_tokens: z.number().int().nonnegative(),
  qwen_estimated_output_tokens: z.number().int().nonnegative(),
  exports_created: z.number().int().nonnegative(),
  errors: z.number().int().nonnegative(),
  budget_fuse_triggered: z.number().int().nonnegative(),
  estimated_cost_rmb: z.number().nonnegative(),
})

const usageDashboardResponseSchema = z.object({
  generated_at: z.string(),
  timezone: z.string(),
  days: z.number().int().min(1).max(90),
  window_start_date: z.string(),
  window_end_date: z.string(),
  totals: z.object({
    meetings: z.number().int().nonnegative(),
    effective_meetings: z.number().int().nonnegative(),
    active_clients: z.number().int().nonnegative(),
    asr_minutes: z.number().nonnegative(),
    qwen_interim_requests: z.number().int().nonnegative(),
    qwen_final_requests: z.number().int().nonnegative(),
    qwen_estimated_input_tokens: z.number().int().nonnegative(),
    qwen_estimated_output_tokens: z.number().int().nonnegative(),
    exports_created: z.number().int().nonnegative(),
    errors: z.number().int().nonnegative(),
    budget_fuse_triggered: z.number().int().nonnegative(),
    estimated_cost_rmb: z.number().nonnegative(),
  }),
  daily: z.array(dailyMetricSchema),
  funnels: z.object({
    first_use: z.object({
      client_created: z.number().int().nonnegative(),
      capture_started: z.number().int().nonnegative(),
      audio_detected: z.number().int().nonnegative(),
      session_started: z.number().int().nonnegative(),
      first_final_seen: z.number().int().nonnegative(),
      capture_to_audio_rate: z.number().nonnegative(),
    }),
    meeting_quality: z.object({
      session_started: z.number().int().nonnegative(),
      audio_detected: z.number().int().nonnegative(),
      asr_final_received: z.number().int().nonnegative(),
      translation_final_completed: z.number().int().nonnegative(),
      segment_archived: z.number().int().nonnegative(),
      archive_viewed: z.number().int().nonnegative(),
    }),
    value_validation: z.object({
      archive_viewed: z.number().int().nonnegative(),
      archive_searched: z.number().int().nonnegative(),
      segment_copied: z.number().int().nonnegative(),
      exports_created: z.number().int().nonnegative(),
      key_sentences_marked: z.number().int().nonnegative(),
    }),
  }),
  quality: z.object({
    provider_errors: z.number().int().nonnegative(),
    quota_exhausted: z.number().int().nonnegative(),
    budget_fuse_triggered: z.number().int().nonnegative(),
    avg_interim_latency_ms: z.number().nonnegative().nullable(),
    avg_final_latency_ms: z.number().nonnegative().nullable(),
    tencent_meeting_sessions: z.number().int().nonnegative(),
    tencent_meeting_successful_sessions: z.number().int().nonnegative(),
    tencent_meeting_success_rate: z.number().nonnegative(),
  }),
  cost: z.object({
    estimated_current_month_cost_rmb: z.number().nonnegative(),
    monthly_budget_rmb: z.number().int().nonnegative(),
    budget_fuse_rmb: z.number().int().nonnegative(),
    budget_usage_percent: z.number().nonnegative(),
    is_estimate: z.boolean(),
  }),
})

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

export type UsageDashboardDailyMetric = z.infer<typeof dailyMetricSchema>
export type UsageDashboardResponse = z.infer<typeof usageDashboardResponseSchema>

export class UsageDashboardAccessError extends Error {
  status: number

  constructor({ message, status }: { message: string; status: number }) {
    super(message)
    this.name = 'UsageDashboardAccessError'
    this.status = status
  }
}

export function buildUsageDashboardApiUrl({
  apiBaseUrl = publicConfig.apiBaseUrl,
  days,
}: {
  apiBaseUrl?: string
  days: number
}): string {
  const dashboardPath = `/api/admin/usage-dashboard?days=${encodeURIComponent(
    String(days),
  )}`
  if (apiBaseUrl.trim() === '') {
    return dashboardPath
  }
  return `${apiBaseUrl.replace(/\/$/, '')}${dashboardPath}`
}

export async function fetchUsageDashboard({
  adminToken,
  apiBaseUrl = publicConfig.apiBaseUrl,
  days,
  fetchFn = fetch,
}: {
  adminToken: string
  apiBaseUrl?: string
  days: number
  fetchFn?: FetchLike
}): Promise<UsageDashboardResponse> {
  if (!Number.isInteger(days) || days < 1 || days > 90) {
    throw new RangeError('Usage dashboard days must be between 1 and 90')
  }

  const response = await fetchFn(buildUsageDashboardApiUrl({ apiBaseUrl, days }), {
    headers: { Authorization: `Bearer ${adminToken}` },
    method: 'GET',
  })

  if (!response.ok) {
    throw new UsageDashboardAccessError({
      message: await responseErrorMessage(response),
      status: response.status,
    })
  }

  return usageDashboardResponseSchema.parse(await response.json())
}

async function responseErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown }
    if (typeof payload.detail === 'string' && payload.detail.trim() !== '') {
      return payload.detail
    }
  } catch {
    // Fall through to the generic HTTP status message.
  }
  return `usage dashboard request failed with HTTP ${response.status}`
}
