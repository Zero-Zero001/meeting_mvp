import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  AlertTriangle,
  CalendarClock,
  Clock3,
  Languages,
  ShieldCheck,
} from 'lucide-react'

import {
  ArchiveAccessError,
  fetchArchive,
  type ArchiveResponse,
  type ArchiveSegment,
} from '@/api/archives'

type LocationLike = Pick<Location, 'pathname' | 'search'>
type FetchArchiveFn = (options: {
  sessionId: string
  token: string
}) => Promise<ArchiveResponse>

type ArchivePageProps = {
  fetchArchiveFn?: FetchArchiveFn
  location?: LocationLike
}

type ArchiveState =
  | { status: 'idle' | 'loading' }
  | { status: 'ready'; archive: ArchiveResponse }
  | { status: 'error'; message: string }

function ArchivePage({
  fetchArchiveFn = fetchArchive,
  location = window.location,
}: ArchivePageProps) {
  const access = useMemo(() => parseArchiveLocation(location), [location])
  const [state, setState] = useState<ArchiveState>({ status: 'loading' })

  useEffect(() => {
    if (!access.ok) {
      return
    }

    let ignore = false
    fetchArchiveFn({
      sessionId: access.sessionId,
      token: access.token,
    })
      .then((archive) => {
        if (!ignore) {
          setState({ archive, status: 'ready' })
        }
      })
      .catch((error: unknown) => {
        if (ignore) {
          return
        }
        setState({
          message:
            error instanceof ArchiveAccessError
              ? accessErrorMessage(error.status)
              : '归档暂时无法加载',
          status: 'error',
        })
      })

    return () => {
      ignore = true
    }
  }, [access, fetchArchiveFn])

  return (
    <main className="min-h-svh bg-zinc-50 text-foreground">
      <section className="mx-auto flex min-h-svh w-full max-w-5xl flex-col gap-4 px-4 py-4 sm:px-5 lg:px-6">
        <header className="border-b border-border pb-4">
          <p className="text-sm font-medium text-muted-foreground">Meeting MVP</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-normal text-zinc-950">
            会议归档
          </h1>
        </header>

        {!access.ok ? (
          <StatusPanel
            icon={<AlertTriangle className="size-4 shrink-0" />}
            message={access.message}
            role="alert"
          />
        ) : null}

        {access.ok && state.status === 'loading' ? (
          <StatusPanel message="正在加载归档内容" />
        ) : null}

        {access.ok && state.status === 'error' ? (
          <StatusPanel
            icon={<AlertTriangle className="size-4 shrink-0" />}
            message={state.message}
            role="alert"
          />
        ) : null}

        {access.ok && state.status === 'ready' ? (
          <ArchiveContent archive={state.archive} />
        ) : null}
      </section>
    </main>
  )
}

function ArchiveContent({ archive }: { archive: ArchiveResponse }) {
  return (
    <>
      <section
        aria-label="归档概览"
        className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4"
      >
        <SummaryItem
          icon={<ShieldCheck className="size-4 shrink-0" />}
          label="结束状态"
          value={endReasonLabel(archive.end_reason)}
        />
        <SummaryItem
          icon={<Languages className="size-4 shrink-0" />}
          label="会议平台"
          value={sourcePlatformLabel(archive.source_platform)}
        />
        <SummaryItem
          icon={<Clock3 className="size-4 shrink-0" />}
          label="会议时长"
          value={formatDuration(archive.duration_seconds)}
        />
        <SummaryItem
          icon={<CalendarClock className="size-4 shrink-0" />}
          label="保留至"
          value={formatDateTime(archive.retention_expires_at)}
        />
      </section>

      <section
        aria-label="双语 final 片段"
        className="grid gap-3"
      >
        {archive.segments.length === 0 ? (
          <div className="rounded-md border border-border bg-background p-4 text-sm text-muted-foreground">
            暂无 final 片段
          </div>
        ) : (
          archive.segments.map((segment) => (
            <ArchiveSegmentArticle key={segment.segment_id} segment={segment} />
          ))
        )}
      </section>
    </>
  )
}

function ArchiveSegmentArticle({ segment }: { segment: ArchiveSegment }) {
  return (
    <article
      aria-label={`片段 ${segment.sequence}`}
      className="rounded-md border border-border bg-background p-4"
    >
      <div className="flex flex-wrap items-center gap-2 border-b border-border pb-3 text-xs text-muted-foreground">
        <span>{formatTimestamp(segment.start_ms)} - {formatTimestamp(segment.end_ms)}</span>
        <span>片段 {segment.sequence}</span>
        <span>{translationStatusLabel(segment.translation_status)}</span>
        {segment.is_key_sentence ? (
          <span className="rounded-sm border border-zinc-300 px-2 py-0.5 font-medium text-zinc-950">
            重点句
          </span>
        ) : null}
      </div>
      <div className="mt-4 grid gap-3">
        <p className="text-sm leading-6 text-zinc-950">
          {segment.english_text_final}
        </p>
        <p className="text-sm leading-6 text-zinc-950">
          {segment.chinese_text_final || '中文 final 暂不可用'}
        </p>
      </div>
    </article>
  )
}

function StatusPanel({
  icon,
  message,
  role = 'status',
}: {
  icon?: ReactNode
  message: string
  role?: 'alert' | 'status'
}) {
  return (
    <div
      className="flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm text-zinc-950"
      role={role}
    >
      {icon}
      <span>{message}</span>
    </div>
  )
}

function SummaryItem({
  icon,
  label,
  value,
}: {
  icon: ReactNode
  label: string
  value: string
}) {
  return (
    <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
      <div className="flex items-center gap-2 text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p className="mt-1 truncate font-medium">{value}</p>
    </div>
  )
}

function parseArchiveLocation(location: LocationLike):
  | { ok: true; sessionId: string; token: string }
  | { ok: false; message: string } {
  const [, archivePrefix, rawSessionId] = location.pathname.split('/')
  const token = new URLSearchParams(location.search).get('token')
  if (archivePrefix !== 'archive' || !rawSessionId || !token?.trim()) {
    return {
      message: '归档访问链接无效',
      ok: false,
    }
  }
  return {
    ok: true,
    sessionId: decodeURIComponent(rawSessionId),
    token,
  }
}

function accessErrorMessage(status: number): string {
  if (status === 401) {
    return '归档访问链接无效'
  }
  if (status === 404) {
    return '归档不存在或访问链接已失效'
  }
  return '归档暂时无法加载'
}

function endReasonLabel(reason: string): string {
  switch (reason) {
    case 'ended':
    case 'user_stopped':
      return '正常结束'
    case 'quota_stopped':
    case 'daily_quota_exhausted':
      return '额度结束'
    case 'budget_fuse_triggered':
      return '预算暂停'
    case 'browser_disconnected':
      return '浏览器断开'
    case 'qwen_asr_error':
      return 'ASR 服务异常'
    case 'qwen_final_translation_failed':
      return '翻译服务异常'
    default:
      return reason
  }
}

function sourcePlatformLabel(platform: ArchiveResponse['source_platform']): string {
  switch (platform) {
    case 'google_meet':
      return 'Google Meet'
    case 'teams_web':
      return 'Teams Web'
    case 'zoom_web':
      return 'Zoom Web'
    case 'tencent_meeting_web':
      return '腾讯会议 Web'
    case 'unknown':
      return '未知平台'
  }
}

function translationStatusLabel(
  status: ArchiveSegment['translation_status'],
): string {
  switch (status) {
    case 'completed':
      return '翻译完成'
    case 'failed':
      return '翻译失败'
    case 'retrying':
      return '重试中'
  }
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes} 分 ${remainingSeconds} 秒`
}

function formatTimestamp(timestampMs: number): string {
  const totalSeconds = Math.floor(timestampMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export default ArchivePage
