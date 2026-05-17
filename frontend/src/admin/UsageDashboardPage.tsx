import { useState, type FormEvent, type ReactNode } from 'react'
import {
  AlertTriangle,
  CalendarDays,
  Gauge,
  KeyRound,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Table2,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  fetchUsageDashboard,
  UsageDashboardAccessError,
  type UsageDashboardDailyMetric,
  type UsageDashboardResponse,
} from '@/api/usage-dashboard'

type DashboardDays = 7 | 30 | 90

type FetchUsageDashboardFn = (options: {
  adminToken: string
  days: number
}) => Promise<UsageDashboardResponse>

const DAY_OPTIONS: DashboardDays[] = [7, 30, 90]

function UsageDashboardPage({
  fetchUsageDashboardFn = fetchUsageDashboard,
}: {
  fetchUsageDashboardFn?: FetchUsageDashboardFn
}) {
  const [adminToken, setAdminToken] = useState('')
  const [dashboard, setDashboard] = useState<UsageDashboardResponse | null>(
    null,
  )
  const [days, setDays] = useState<DashboardDays>(30)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  async function loadDashboard(nextDays: DashboardDays = days) {
    const trimmedToken = adminToken.trim()
    if (trimmedToken === '') {
      setErrorMessage('请输入管理口令')
      return
    }

    setDays(nextDays)
    setErrorMessage(null)
    setIsLoading(true)
    try {
      const nextDashboard = await fetchUsageDashboardFn({
        adminToken: trimmedToken,
        days: nextDays,
      })
      setDashboard(nextDashboard)
    } catch (error) {
      setDashboard(null)
      setErrorMessage(dashboardErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void loadDashboard(days)
  }

  return (
    <main className="min-h-svh bg-zinc-50 text-foreground">
      <section className="mx-auto flex min-h-svh w-full max-w-7xl flex-col gap-5 px-4 py-4 sm:px-5 lg:px-6">
        <header className="border-b border-border pb-4">
          <p className="text-sm font-medium text-muted-foreground">
            Meeting MVP Admin
          </p>
          <div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-2xl font-semibold tracking-normal text-zinc-950">
                使用量与成本看板
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
                数据来自 usage_event 和 meeting_session 的安全聚合；成本是估算值。
              </p>
            </div>

            <form
              className="grid gap-2 sm:grid-cols-[minmax(220px,280px)_auto]"
              onSubmit={handleSubmit}
            >
              <label className="grid gap-1 text-sm font-medium text-zinc-950">
                <span>管理口令</span>
                <span className="relative">
                  <KeyRound className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    aria-label="管理口令"
                    autoComplete="off"
                    className="h-9 w-full rounded-md border border-border bg-background px-9 text-sm outline-none transition-colors focus:border-zinc-500"
                    onChange={(event) => setAdminToken(event.target.value)}
                    type="password"
                    value={adminToken}
                  />
                </span>
              </label>
              <Button
                className="self-end"
                disabled={isLoading}
                type="submit"
              >
                {isLoading ? (
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                ) : (
                  <RefreshCw data-icon="inline-start" />
                )}
                加载看板
              </Button>
            </form>
          </div>
        </header>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div
            aria-label="看板时间窗口"
            className="inline-flex w-full rounded-md border border-border bg-background p-1 sm:w-auto"
            role="group"
          >
            {DAY_OPTIONS.map((option) => (
              <Button
                aria-pressed={days === option}
                className="flex-1 sm:flex-none"
                disabled={isLoading}
                key={option}
                onClick={() => void loadDashboard(option)}
                size="sm"
                type="button"
                variant={days === option ? 'secondary' : 'ghost'}
              >
                {option} 天
              </Button>
            ))}
          </div>
          {dashboard ? (
            <p className="text-sm text-muted-foreground">
              {dashboard.window_start_date} 至 {dashboard.window_end_date}，
              {dashboard.timezone}
            </p>
          ) : null}
        </div>

        {errorMessage ? (
          <div
            className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950"
            role="alert"
          >
            <p className="font-medium">{errorMessage}</p>
          </div>
        ) : null}

        {dashboard ? <DashboardContent dashboard={dashboard} /> : null}
      </section>
    </main>
  )
}

function DashboardContent({
  dashboard,
}: {
  dashboard: UsageDashboardResponse
}) {
  return (
    <div className="grid gap-5">
      <section aria-labelledby="usage-summary-title" className="grid gap-3">
        <SectionTitle
          icon={<Gauge className="size-4" />}
          id="usage-summary-title"
          title="核心指标"
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricTile label="会议数" value={dashboard.totals.meetings} />
          <MetricTile
            label="有效会议"
            value={dashboard.totals.effective_meetings}
          />
          <MetricTile
            label="活跃匿名用户"
            value={dashboard.totals.active_clients}
          />
          <MetricTile
            label="ASR 分钟"
            value={formatNumber(dashboard.totals.asr_minutes)}
          />
          <MetricTile
            label="Qwen interim 请求"
            value={dashboard.totals.qwen_interim_requests}
          />
          <MetricTile
            label="Qwen final 请求"
            value={dashboard.totals.qwen_final_requests}
          />
          <MetricTile
            label="导出数"
            value={dashboard.totals.exports_created}
          />
          <MetricTile
            label="估算成本"
            value={`${formatCurrency(dashboard.totals.estimated_cost_rmb)} RMB`}
          />
        </div>
      </section>

      <section aria-labelledby="daily-trends-title" className="grid gap-3">
        <SectionTitle
          icon={<Table2 className="size-4" />}
          id="daily-trends-title"
          title="每日趋势"
        />
        <DailyTrendTable daily={dashboard.daily} />
      </section>

      <section className="grid gap-3 lg:grid-cols-3">
        <FunnelPanel
          rows={[
            ['新增匿名用户', dashboard.funnels.first_use.client_created],
            ['开始捕获', dashboard.funnels.first_use.capture_started],
            ['检测到有效音频', dashboard.funnels.first_use.audio_detected],
            ['创建会话', dashboard.funnels.first_use.session_started],
            ['收到首个 final', dashboard.funnels.first_use.first_final_seen],
            [
              '捕获到音频转化率',
              formatPercent(dashboard.funnels.first_use.capture_to_audio_rate),
            ],
          ]}
          title="首次使用漏斗"
        />
        <FunnelPanel
          rows={[
            ['创建会话', dashboard.funnels.meeting_quality.session_started],
            ['检测到有效音频', dashboard.funnels.meeting_quality.audio_detected],
            ['收到英文 final', dashboard.funnels.meeting_quality.asr_final_received],
            [
              '完成中文 final',
              dashboard.funnels.meeting_quality.translation_final_completed,
            ],
            ['归档片段', dashboard.funnels.meeting_quality.segment_archived],
            ['查看归档', dashboard.funnels.meeting_quality.archive_viewed],
          ]}
          title="会议质量漏斗"
        />
        <FunnelPanel
          rows={[
            ['查看归档', dashboard.funnels.value_validation.archive_viewed],
            ['归档搜索', dashboard.funnels.value_validation.archive_searched],
            ['复制片段', dashboard.funnels.value_validation.segment_copied],
            ['导出文件', dashboard.funnels.value_validation.exports_created],
            [
              '人工重点句',
              dashboard.funnels.value_validation.key_sentences_marked,
            ],
          ]}
          title="价值验证漏斗"
        />
      </section>

      <section className="grid gap-3 lg:grid-cols-2">
        <section
          aria-labelledby="quality-title"
          className="rounded-md border border-border bg-background p-4"
        >
          <SectionTitle
            icon={<AlertTriangle className="size-4" />}
            id="quality-title"
            title="错误与质量"
          />
          <dl className="mt-4 grid gap-3 text-sm">
            <DetailRow label="Provider 错误" value={dashboard.quality.provider_errors} />
            <DetailRow label="额度拒绝" value={dashboard.quality.quota_exhausted} />
            <DetailRow
              label="预算保险丝"
              value={dashboard.quality.budget_fuse_triggered}
            />
            <DetailRow
              label="final 平均延迟"
              value={formatNullableMilliseconds(
                dashboard.quality.avg_final_latency_ms,
              )}
            />
            <DetailRow
              label="interim 平均延迟"
              value={formatNullableMilliseconds(
                dashboard.quality.avg_interim_latency_ms,
              )}
            />
            <DetailRow
              label="腾讯会议成功率"
              value={formatPercent(dashboard.quality.tencent_meeting_success_rate)}
            />
          </dl>
        </section>

        <section
          aria-label="成本与预算"
          className="rounded-md border border-border bg-background p-4"
        >
          <SectionTitle
            icon={<ShieldCheck className="size-4" />}
            id="cost-title"
            title="成本与预算"
          />
          <dl className="mt-4 grid gap-3 text-sm">
            <DetailRow
              label="本月估算成本"
              value={formatCurrency(dashboard.cost.estimated_current_month_cost_rmb)}
            />
            <DetailRow
              label="月度预算"
              value={`${dashboard.cost.monthly_budget_rmb} RMB`}
            />
            <DetailRow
              label="预算保险丝阈值"
              value={`${dashboard.cost.budget_fuse_rmb} RMB`}
            />
            <DetailRow
              label="预算使用率"
              value={formatPercent(dashboard.cost.budget_usage_percent)}
            />
            <DetailRow
              label="成本口径"
              value={dashboard.cost.is_estimate ? '估算' : '账单'}
            />
          </dl>
        </section>
      </section>
    </div>
  )
}

function DailyTrendTable({ daily }: { daily: UsageDashboardDailyMetric[] }) {
  return (
    <div className="overflow-x-auto rounded-md border border-border bg-background">
      <table className="min-w-[920px] w-full text-left text-sm">
        <thead className="border-b border-border bg-zinc-100 text-xs text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-medium">日期</th>
            <th className="px-3 py-2 font-medium">会议</th>
            <th className="px-3 py-2 font-medium">有效会议</th>
            <th className="px-3 py-2 font-medium">活跃用户</th>
            <th className="px-3 py-2 font-medium">ASR 分钟</th>
            <th className="px-3 py-2 font-medium">interim</th>
            <th className="px-3 py-2 font-medium">final</th>
            <th className="px-3 py-2 font-medium">导出</th>
            <th className="px-3 py-2 font-medium">错误</th>
            <th className="px-3 py-2 font-medium">估算成本</th>
          </tr>
        </thead>
        <tbody>
          {daily.map((metric) => (
            <tr className="border-b border-border last:border-b-0" key={metric.date}>
              <td className="px-3 py-2 font-medium text-zinc-950">{metric.date}</td>
              <td className="px-3 py-2">{metric.meetings}</td>
              <td className="px-3 py-2">{metric.effective_meetings}</td>
              <td className="px-3 py-2">{metric.active_clients}</td>
              <td className="px-3 py-2">{formatNumber(metric.asr_minutes)}</td>
              <td className="px-3 py-2">{metric.qwen_interim_requests}</td>
              <td className="px-3 py-2">{metric.qwen_final_requests}</td>
              <td className="px-3 py-2">{metric.exports_created}</td>
              <td className="px-3 py-2">{metric.errors}</td>
              <td className="px-3 py-2">{formatCurrency(metric.estimated_cost_rmb)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function FunnelPanel({
  rows,
  title,
}: {
  rows: Array<[string, number | string]>
  title: string
}) {
  return (
    <section className="rounded-md border border-border bg-background p-4">
      <SectionTitle
        icon={<CalendarDays className="size-4" />}
        id={`${title}-title`}
        title={title}
      />
      <dl className="mt-4 grid gap-3 text-sm">
        {rows.map(([label, value]) => (
          <DetailRow
            key={label}
            label={label}
            value={typeof value === 'number' ? `${value} 次` : value}
          />
        ))}
      </dl>
    </section>
  )
}

function MetricTile({
  label,
  value,
}: {
  label: string
  value: number | string
}) {
  return (
    <div className="min-w-0 rounded-md border border-border bg-background p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-2 truncate text-2xl font-semibold text-zinc-950">
        {value}
      </p>
    </div>
  )
}

function DetailRow({
  label,
  value,
}: {
  label: string
  value: number | string
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-zinc-950">{value}</dd>
    </div>
  )
}

function SectionTitle({
  icon,
  id,
  title,
}: {
  icon: ReactNode
  id: string
  title: string
}) {
  return (
    <div className="flex items-center gap-2 text-sm font-medium text-zinc-950">
      {icon}
      <h2 id={id}>{title}</h2>
    </div>
  )
}

function dashboardErrorMessage(error: unknown): string {
  if (error instanceof UsageDashboardAccessError) {
    if (error.status === 401) {
      return '管理口令无效'
    }
    if (error.status === 503) {
      return '看板未配置'
    }
  }
  return '看板暂时无法加载'
}

function formatCurrency(value: number): string {
  return `¥${value.toFixed(4)}`
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function formatNullableMilliseconds(value: number | null): string {
  return value === null ? '暂无' : `${Math.round(value)} ms`
}

function formatPercent(value: number): string {
  return `${Math.round(value * 1000) / 10}%`
}

export default UsageDashboardPage
