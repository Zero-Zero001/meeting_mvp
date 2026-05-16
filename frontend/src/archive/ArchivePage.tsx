import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  AlertTriangle,
  CalendarClock,
  Check,
  Clock3,
  Copy,
  Download,
  FileText,
  Languages,
  Search,
  ShieldCheck,
} from 'lucide-react'

import {
  ArchiveAccessError,
  createArchiveExport,
  fetchArchive,
  recordArchiveEvent,
  type ArchiveExportFormat,
  type ArchiveExportResponse,
  type ArchiveResponse,
  type ArchiveSegment,
  type ArchiveEvent,
} from '@/api/archives'
import { Button } from '@/components/ui/button'

type LocationLike = Pick<Location, 'pathname' | 'search'>
type FetchArchiveFn = (options: {
  sessionId: string
  token: string
}) => Promise<ArchiveResponse>
type RecordArchiveEventFn = (options: {
  sessionId: string
  token: string
  event: ArchiveEvent
}) => Promise<void>
type CreateArchiveExportFn = (options: {
  sessionId: string
  token: string
  format: ArchiveExportFormat
}) => Promise<ArchiveExportResponse>
type WriteClipboardTextFn = (text: string) => Promise<void>

type ArchivePageProps = {
  createArchiveExportFn?: CreateArchiveExportFn
  fetchArchiveFn?: FetchArchiveFn
  location?: LocationLike
  recordArchiveEventFn?: RecordArchiveEventFn
  writeClipboardTextFn?: WriteClipboardTextFn
}

type ArchiveState =
  | { status: 'idle' | 'loading' }
  | { status: 'ready'; archive: ArchiveResponse }
  | { status: 'error'; message: string }
type ExportState =
  | { status: 'idle' }
  | { status: 'creating'; format: ArchiveExportFormat }
  | { status: 'success'; exportResponse: ArchiveExportResponse }
  | { status: 'error'; message: string }

function ArchivePage({
  createArchiveExportFn = createArchiveExport,
  fetchArchiveFn = fetchArchive,
  location = window.location,
  recordArchiveEventFn = recordArchiveEvent,
  writeClipboardTextFn = writeClipboardText,
}: ArchivePageProps) {
  const access = useMemo(() => parseArchiveLocation(location), [location])
  const [state, setState] = useState<ArchiveState>({ status: 'loading' })
  const [searchQuery, setSearchQuery] = useState('')
  const [copiedSegmentId, setCopiedSegmentId] = useState<string | null>(null)
  const [clipboardError, setClipboardError] = useState<string | null>(null)
  const [exportState, setExportState] = useState<ExportState>({ status: 'idle' })

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

  useEffect(() => {
    if (!access.ok || state.status !== 'ready') {
      return
    }
    const trimmedQuery = searchQuery.trim()
    if (trimmedQuery === '') {
      return
    }
    const archive = state.archive
    const timeoutId = window.setTimeout(() => {
      void recordArchiveEventFn({
        event: {
          event_type: 'archive_searched',
          matched_segment_count: filterArchiveSegments(
            archive.segments,
            trimmedQuery,
          ).length,
          query_length: trimmedQuery.length,
          total_segment_count: archive.segments.length,
        },
        sessionId: access.sessionId,
        token: access.token,
      }).catch(() => undefined)
    }, 400)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [access, recordArchiveEventFn, searchQuery, state])

  async function handleCopySegment(segment: ArchiveSegment): Promise<void> {
    if (!access.ok) {
      return
    }
    try {
      await writeClipboardTextFn(formatSegmentCopyText(segment))
      setCopiedSegmentId(segment.segment_id)
      setClipboardError(null)
      void recordArchiveEventFn({
        event: {
          event_type: 'segment_copied',
          segment_id: segment.segment_id,
        },
        sessionId: access.sessionId,
        token: access.token,
      }).catch(() => undefined)
    } catch {
      setClipboardError('复制失败，请手动选择文本复制')
    }
  }

  async function handleCreateExport(format: ArchiveExportFormat): Promise<void> {
    if (!access.ok) {
      return
    }
    setExportState({ format, status: 'creating' })
    try {
      const exportResponse = await createArchiveExportFn({
        format,
        sessionId: access.sessionId,
        token: access.token,
      })
      setExportState({ exportResponse, status: 'success' })
    } catch (error: unknown) {
      setExportState({
        message: exportErrorMessage(error),
        status: 'error',
      })
    }
  }

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
          <ArchiveContent
            archive={state.archive}
            clipboardError={clipboardError}
            copiedSegmentId={copiedSegmentId}
            exportState={exportState}
            onCreateExport={(format) => void handleCreateExport(format)}
            onCopySegment={(segment) => void handleCopySegment(segment)}
            onSearchQueryChange={setSearchQuery}
            searchQuery={searchQuery}
          />
        ) : null}
      </section>
    </main>
  )
}

function ArchiveContent({
  archive,
  clipboardError,
  copiedSegmentId,
  exportState,
  onCreateExport,
  onCopySegment,
  onSearchQueryChange,
  searchQuery,
}: {
  archive: ArchiveResponse
  clipboardError: string | null
  copiedSegmentId: string | null
  exportState: ExportState
  onCreateExport: (format: ArchiveExportFormat) => void
  onCopySegment: (segment: ArchiveSegment) => void
  onSearchQueryChange: (query: string) => void
  searchQuery: string
}) {
  const filteredSegments = filterArchiveSegments(archive.segments, searchQuery)
  const hasSearchQuery = searchQuery.trim() !== ''
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

      <ArchiveExportPanel
        exportState={exportState}
        hasExportableSegments={archive.segments.length > 0}
        onCreateExport={onCreateExport}
      />

      <section
        aria-label="归档搜索"
        className="grid gap-2 rounded-md border border-border bg-background p-3"
      >
        <label
          className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground"
          htmlFor="archive-search"
        >
          <Search className="size-4 shrink-0" />
          <span>搜索</span>
        </label>
        <input
          aria-label="搜索归档片段"
          className="min-w-0 rounded-md border border-border bg-background px-3 py-2 text-sm text-zinc-950 outline-none focus:border-zinc-500"
          id="archive-search"
          onChange={(event) => onSearchQueryChange(event.target.value)}
          placeholder="搜索英文、中文或时间"
          value={searchQuery}
        />
        {clipboardError ? (
          <div
            className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950"
            role="alert"
          >
            {clipboardError}
          </div>
        ) : null}
      </section>

      <section
        aria-label="双语 final 片段"
        className="grid gap-3"
      >
        {archive.segments.length === 0 ? (
          <div className="rounded-md border border-border bg-background p-4 text-sm text-muted-foreground">
            暂无 final 片段
          </div>
        ) : filteredSegments.length === 0 && hasSearchQuery ? (
          <div className="rounded-md border border-border bg-background p-4 text-sm text-muted-foreground">
            未找到匹配片段
          </div>
        ) : (
          filteredSegments.map((segment) => (
            <ArchiveSegmentArticle
              copied={copiedSegmentId === segment.segment_id}
              key={segment.segment_id}
              onCopy={() => onCopySegment(segment)}
              segment={segment}
            />
          ))
        )}
      </section>
    </>
  )
}

function ArchiveExportPanel({
  exportState,
  hasExportableSegments,
  onCreateExport,
}: {
  exportState: ExportState
  hasExportableSegments: boolean
  onCreateExport: (format: ArchiveExportFormat) => void
}) {
  const isCreating = exportState.status === 'creating'
  return (
    <section
      aria-label="归档导出"
      className="grid gap-3 rounded-md border border-border bg-background p-3"
    >
      <div className="flex flex-wrap items-center gap-2">
        <Button
          aria-label="导出 Markdown"
          disabled={!hasExportableSegments || isCreating}
          onClick={() => onCreateExport('markdown')}
          type="button"
          variant="outline"
        >
          <FileText className="size-4" />
          {isCreating && exportState.format === 'markdown'
            ? '生成中'
            : '导出 Markdown'}
        </Button>
        <Button
          aria-label="导出 JSON"
          disabled={!hasExportableSegments || isCreating}
          onClick={() => onCreateExport('json')}
          type="button"
          variant="outline"
        >
          <Download className="size-4" />
          {isCreating && exportState.format === 'json' ? '生成中' : '导出 JSON'}
        </Button>
      </div>
      {exportState.status === 'success' ? (
        <div
          className="flex flex-wrap items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-950"
          role="status"
        >
          <span>导出已生成</span>
          <a
            className="font-medium underline underline-offset-4"
            href={exportState.exportResponse.download_url}
            rel="noreferrer"
            target="_blank"
          >
            下载 {exportFormatLabel(exportState.exportResponse.format)}
          </a>
        </div>
      ) : null}
      {exportState.status === 'error' ? (
        <div
          className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950"
          role="alert"
        >
          {exportState.message}
        </div>
      ) : null}
    </section>
  )
}

function ArchiveSegmentArticle({
  copied,
  onCopy,
  segment,
}: {
  copied: boolean
  onCopy: () => void
  segment: ArchiveSegment
}) {
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
        <Button
          aria-label={`复制片段 ${segment.sequence}`}
          className="ml-auto"
          onClick={onCopy}
          size="sm"
          type="button"
          variant="outline"
        >
          {copied ? (
            <Check className="size-4" />
          ) : (
            <Copy className="size-4" />
          )}
          {copied ? '已复制' : '复制'}
        </Button>
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

function exportErrorMessage(error: unknown): string {
  if (error instanceof ArchiveAccessError && error.status === 409) {
    return '暂无可导出的 final 片段'
  }
  if (error instanceof ArchiveAccessError && error.status === 404) {
    return '归档不存在或访问链接已失效'
  }
  return '导出暂时不可用，请稍后重试'
}

function exportFormatLabel(format: ArchiveExportFormat): string {
  return format === 'markdown' ? 'Markdown' : 'JSON'
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

function filterArchiveSegments(
  segments: ArchiveSegment[],
  query: string,
): ArchiveSegment[] {
  const normalizedQuery = query.trim().toLocaleLowerCase()
  if (normalizedQuery === '') {
    return segments
  }
  return segments.filter((segment) =>
    searchableSegmentValues(segment).some((value) =>
      value.toLocaleLowerCase().includes(normalizedQuery),
    ),
  )
}

function searchableSegmentValues(segment: ArchiveSegment): string[] {
  return [
    segment.english_text_final,
    segment.chinese_text_final,
    formatTimestamp(segment.start_ms),
    formatTimestamp(segment.end_ms),
    `${formatTimestamp(segment.start_ms)} - ${formatTimestamp(segment.end_ms)}`,
  ]
}

function formatSegmentCopyText(segment: ArchiveSegment): string {
  return [
    `时间：${formatTimestamp(segment.start_ms)} - ${formatTimestamp(segment.end_ms)}`,
    `英文：${segment.english_text_final}`,
    `中文：${segment.chinese_text_final || '中文 final 暂不可用'}`,
  ].join('\n')
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function writeClipboardText(text: string): Promise<void> {
  return navigator.clipboard.writeText(text)
}

export default ArchivePage
