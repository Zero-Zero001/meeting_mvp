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
  ListChecks,
  Search,
  ShieldCheck,
  Star,
} from 'lucide-react'

import {
  ArchiveAccessError,
  createArchiveExport,
  fetchArchive,
  recordArchiveEvent,
  updateArchiveSegmentKeySentence,
  type ArchiveExportFormat,
  type ArchiveExportResponse,
  type ArchiveResponse,
  type ArchiveSegment,
  type ArchiveTimelineItem,
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
type UpdateArchiveSegmentKeySentenceFn = (options: {
  sessionId: string
  token: string
  segmentId: string
  isKeySentence: boolean
}) => Promise<ArchiveSegment>
type WriteClipboardTextFn = (text: string) => Promise<void>
type TimelineFilter = 'all' | ArchiveTimelineItem['item_type']

const TIMELINE_FILTERS: Array<{
  label: string
  value: TimelineFilter
}> = [
  { label: '全部', value: 'all' },
  { label: 'final', value: 'segment_final' },
  { label: '重点句', value: 'key_sentence' },
  { label: '导出', value: 'export_created' },
  { label: '异常', value: 'exception' },
]

type ArchivePageProps = {
  createArchiveExportFn?: CreateArchiveExportFn
  fetchArchiveFn?: FetchArchiveFn
  location?: LocationLike
  recordArchiveEventFn?: RecordArchiveEventFn
  retryPollingIntervalMs?: number
  updateArchiveSegmentKeySentenceFn?: UpdateArchiveSegmentKeySentenceFn
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
  retryPollingIntervalMs = 5000,
  updateArchiveSegmentKeySentenceFn = updateArchiveSegmentKeySentence,
  writeClipboardTextFn = writeClipboardText,
}: ArchivePageProps) {
  const access = useMemo(() => parseArchiveLocation(location), [location])
  const [state, setState] = useState<ArchiveState>({ status: 'loading' })
  const [searchQuery, setSearchQuery] = useState('')
  const [copiedSegmentId, setCopiedSegmentId] = useState<string | null>(null)
  const [clipboardError, setClipboardError] = useState<string | null>(null)
  const [exportState, setExportState] = useState<ExportState>({ status: 'idle' })
  const [keySentenceError, setKeySentenceError] = useState<string | null>(null)
  const [showKeyOnly, setShowKeyOnly] = useState(false)
  const [updatingKeySegmentId, setUpdatingKeySegmentId] = useState<string | null>(
    null,
  )

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

  useEffect(() => {
    if (
      !access.ok ||
      state.status !== 'ready' ||
      !hasPendingTranslationRetries(state.archive)
    ) {
      return
    }

    let ignore = false
    let requestInFlight = false
    const intervalId = window.setInterval(() => {
      if (requestInFlight) {
        return
      }
      requestInFlight = true
      void Promise.resolve(
        fetchArchiveFn({
          sessionId: access.sessionId,
          token: access.token,
        }),
      )
        .then((archive) => {
          if (!ignore && archive) {
            setState({ archive, status: 'ready' })
          }
        })
        .catch(() => undefined)
        .finally(() => {
          requestInFlight = false
        })
    }, retryPollingIntervalMs)

    return () => {
      ignore = true
      window.clearInterval(intervalId)
    }
  }, [access, fetchArchiveFn, retryPollingIntervalMs, state])

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
      setState((currentState) => {
        if (currentState.status !== 'ready') {
          return currentState
        }
        return {
          archive: {
            ...currentState.archive,
            timeline_items: upsertTimelineItem(
              currentState.archive.timeline_items,
              exportTimelineItemFromResponse(exportResponse, currentState.archive),
            ),
          },
          status: 'ready',
        }
      })
    } catch (error: unknown) {
      setExportState({
        message: exportErrorMessage(error),
        status: 'error',
      })
    }
  }

  async function handleUpdateKeySentence(
    segment: ArchiveSegment,
    isKeySentence: boolean,
  ): Promise<void> {
    if (!access.ok) {
      return
    }
    setUpdatingKeySegmentId(segment.segment_id)
    setKeySentenceError(null)
    try {
      const updatedSegment = await updateArchiveSegmentKeySentenceFn({
        isKeySentence,
        segmentId: segment.segment_id,
        sessionId: access.sessionId,
        token: access.token,
      })
      setState((currentState) => {
        if (currentState.status !== 'ready') {
          return currentState
        }
        return {
          archive: {
            ...currentState.archive,
            segments: currentState.archive.segments.map((currentSegment) =>
              currentSegment.segment_id === updatedSegment.segment_id
                ? updatedSegment
                : currentSegment,
            ),
          },
          status: 'ready',
        }
      })
    } catch {
      setKeySentenceError('重点句更新失败，请稍后重试')
    } finally {
      setUpdatingKeySegmentId(null)
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
            keySentenceError={keySentenceError}
            onCreateExport={(format) => void handleCreateExport(format)}
            onCopySegment={(segment) => void handleCopySegment(segment)}
            onSearchQueryChange={setSearchQuery}
            onShowKeyOnlyChange={setShowKeyOnly}
            onUpdateKeySentence={(segment, isKeySentence) =>
              void handleUpdateKeySentence(segment, isKeySentence)
            }
            searchQuery={searchQuery}
            showKeyOnly={showKeyOnly}
            updatingKeySegmentId={updatingKeySegmentId}
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
  keySentenceError,
  onCreateExport,
  onCopySegment,
  onSearchQueryChange,
  onShowKeyOnlyChange,
  onUpdateKeySentence,
  searchQuery,
  showKeyOnly,
  updatingKeySegmentId,
}: {
  archive: ArchiveResponse
  clipboardError: string | null
  copiedSegmentId: string | null
  exportState: ExportState
  keySentenceError: string | null
  onCreateExport: (format: ArchiveExportFormat) => void
  onCopySegment: (segment: ArchiveSegment) => void
  onSearchQueryChange: (query: string) => void
  onShowKeyOnlyChange: (showKeyOnly: boolean) => void
  onUpdateKeySentence: (segment: ArchiveSegment, isKeySentence: boolean) => void
  searchQuery: string
  showKeyOnly: boolean
  updatingKeySegmentId: string | null
}) {
  const [timelineFilter, setTimelineFilter] = useState<TimelineFilter>('all')
  const filteredSegments = filterArchiveSegments(
    archive.segments,
    searchQuery,
    showKeyOnly,
  )
  const hasSearchQuery = searchQuery.trim() !== ''
  const hasActiveFilter = hasSearchQuery || showKeyOnly
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

      <ArchiveTimelinePanel
        activeFilter={timelineFilter}
        items={archive.timeline_items}
        onFilterChange={setTimelineFilter}
        onSelectSegment={(segmentId) =>
          scrollToElement(archiveSegmentElementId(segmentId))
        }
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
        <label
          className="flex w-fit items-center gap-2 text-sm text-zinc-950"
          htmlFor="archive-key-only"
        >
          <input
            checked={showKeyOnly}
            className="size-4"
            id="archive-key-only"
            onChange={(event) => onShowKeyOnlyChange(event.target.checked)}
            type="checkbox"
          />
          <span>只看重点句</span>
        </label>
        {clipboardError ? (
          <div
            className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950"
            role="alert"
          >
            {clipboardError}
          </div>
        ) : null}
        {keySentenceError ? (
          <div
            className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950"
            role="alert"
          >
            {keySentenceError}
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
        ) : filteredSegments.length === 0 && hasActiveFilter ? (
          <div className="rounded-md border border-border bg-background p-4 text-sm text-muted-foreground">
            未找到匹配片段
          </div>
        ) : (
          filteredSegments.map((segment) => (
            <ArchiveSegmentArticle
              copied={copiedSegmentId === segment.segment_id}
              key={segment.segment_id}
              onCopy={() => onCopySegment(segment)}
              onToggleKeySentence={() =>
                onUpdateKeySentence(segment, !segment.is_key_sentence)
              }
              segment={segment}
              updatingKeySentence={updatingKeySegmentId === segment.segment_id}
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

function ArchiveTimelinePanel({
  activeFilter,
  items,
  onFilterChange,
  onSelectSegment,
}: {
  activeFilter: TimelineFilter
  items: ArchiveTimelineItem[]
  onFilterChange: (filter: TimelineFilter) => void
  onSelectSegment: (segmentId: string) => void
}) {
  return (
    <section
      aria-label="归档时间线"
      className="grid gap-3 rounded-md border border-border bg-background p-3"
    >
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <ListChecks className="size-4 shrink-0" />
        <span>会议时间线</span>
      </div>
      {items.length > 0 ? (
        <>
          <TimelineFilterButtons
            activeFilter={activeFilter}
            ariaLabel="筛选归档时间线"
            onFilterChange={onFilterChange}
          />
          <TimelineEventList
            emptyMessage="当前筛选下暂无归档事件。"
            items={filterTimelineItems(items, activeFilter)}
            onSelectSegment={onSelectSegment}
          />
        </>
      ) : (
        <p className="text-sm leading-6 text-muted-foreground">
          暂无时间线事件。
        </p>
      )}
    </section>
  )
}

function TimelineFilterButtons({
  activeFilter,
  ariaLabel,
  onFilterChange,
}: {
  activeFilter: TimelineFilter
  ariaLabel: string
  onFilterChange: (filter: TimelineFilter) => void
}) {
  return (
    <div
      aria-label={ariaLabel}
      className="inline-flex w-full rounded-md border border-border bg-background p-1 sm:w-auto"
      role="group"
    >
      {TIMELINE_FILTERS.map((filter) => (
        <Button
          aria-pressed={activeFilter === filter.value}
          className="flex-1 sm:flex-none"
          key={filter.value}
          onClick={() => onFilterChange(filter.value)}
          size="sm"
          type="button"
          variant={activeFilter === filter.value ? 'secondary' : 'ghost'}
        >
          {filter.label}
        </Button>
      ))}
    </div>
  )
}

function TimelineEventList({
  emptyMessage,
  items,
  onSelectSegment,
}: {
  emptyMessage: string
  items: ArchiveTimelineItem[]
  onSelectSegment: (segmentId: string) => void
}) {
  if (items.length === 0) {
    return <p className="text-sm leading-6 text-muted-foreground">{emptyMessage}</p>
  }

  return (
    <ol className="grid gap-3 text-sm">
      {items.map((item) => (
        <li className="border-l-2 border-zinc-300 pl-3 leading-6" key={item.id}>
          {item.segment_id ? (
            <button
              aria-label={`${timelineTypeLabel(item.item_type)} ${item.text}`}
              className="grid w-full gap-1 text-left"
              onClick={() => onSelectSegment(item.segment_id as string)}
              type="button"
            >
              <TimelineEventContent item={item} />
            </button>
          ) : (
            <TimelineEventContent item={item} />
          )}
        </li>
      ))}
    </ol>
  )
}

function TimelineEventContent({ item }: { item: ArchiveTimelineItem }) {
  return (
    <>
      <p className="text-xs font-medium text-muted-foreground">
        {timelineTypeLabel(item.item_type)}
      </p>
      <p className="font-medium text-zinc-950">{item.text}</p>
      <p className="text-xs text-muted-foreground">
        {formatTimestamp(item.timestamp_ms)}
      </p>
    </>
  )
}

function ArchiveSegmentArticle({
  copied,
  onCopy,
  onToggleKeySentence,
  segment,
  updatingKeySentence,
}: {
  copied: boolean
  onCopy: () => void
  onToggleKeySentence: () => void
  segment: ArchiveSegment
  updatingKeySentence: boolean
}) {
  return (
    <article
      aria-label={`片段 ${segment.sequence}`}
      className="rounded-md border border-border bg-background p-4"
      id={archiveSegmentElementId(segment.segment_id)}
    >
      <div className="flex flex-wrap items-center gap-2 border-b border-border pb-3 text-xs text-muted-foreground">
        <span>{formatTimestamp(segment.start_ms)} - {formatTimestamp(segment.end_ms)}</span>
        <span>片段 {segment.sequence}</span>
        <span>{translationStatusLabel(segment)}</span>
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
        <Button
          aria-label={
            segment.is_key_sentence
              ? `取消片段 ${segment.sequence} 重点句`
              : `标记片段 ${segment.sequence} 为重点句`
          }
          disabled={updatingKeySentence}
          onClick={onToggleKeySentence}
          size="sm"
          type="button"
          variant="outline"
        >
          <Star className="size-4" />
          {segment.is_key_sentence ? '取消重点句' : '标为重点句'}
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
  segment: ArchiveSegment,
): string {
  switch (segment.translation_status) {
    case 'completed':
      return '翻译完成'
    case 'failed':
      return segment.translation_retry_exhausted ? '补译失败' : '等待后台补译'
    case 'retrying':
      return '后台补译中'
  }
}

function hasPendingTranslationRetries(archive: ArchiveResponse): boolean {
  return archive.segments.some(
    (segment) =>
      segment.translation_status === 'retrying' ||
      (segment.translation_status === 'failed' &&
        !segment.translation_retry_exhausted),
  )
}

function filterTimelineItems(
  items: ArchiveTimelineItem[],
  activeFilter: TimelineFilter,
): ArchiveTimelineItem[] {
  if (activeFilter === 'all') {
    return items
  }
  return items.filter((item) => item.item_type === activeFilter)
}

function timelineTypeLabel(itemType: ArchiveTimelineItem['item_type']): string {
  switch (itemType) {
    case 'segment_final':
      return 'final'
    case 'key_sentence':
      return '重点句'
    case 'export_created':
      return '导出事件'
    case 'exception':
      return '异常'
  }
}

function exportTimelineItemFromResponse(
  exportResponse: ArchiveExportResponse,
  archive: ArchiveResponse,
): ArchiveTimelineItem {
  return {
    id: `export-created-${exportResponse.export_id}`,
    item_type: 'export_created',
    text: `已生成 ${exportFormatLabel(exportResponse.format)} 导出`,
    timestamp_ms: exportTimelineTimestampMs(exportResponse, archive),
  }
}

function exportTimelineTimestampMs(
  exportResponse: ArchiveExportResponse,
  archive: ArchiveResponse,
): number {
  if (!archive.started_at) {
    return Math.max(archive.duration_seconds, 0) * 1000
  }
  return Math.max(
    Math.floor(
      new Date(exportResponse.created_at).getTime() -
        new Date(archive.started_at).getTime(),
    ),
    0,
  )
}

function upsertTimelineItem(
  items: ArchiveTimelineItem[],
  nextItem: ArchiveTimelineItem,
): ArchiveTimelineItem[] {
  const filteredItems = items.filter((item) => item.id !== nextItem.id)
  return [...filteredItems, nextItem].sort((first, second) => {
    if (first.timestamp_ms !== second.timestamp_ms) {
      return first.timestamp_ms - second.timestamp_ms
    }
    return timelineSortOrder(first.item_type) - timelineSortOrder(second.item_type)
  })
}

function timelineSortOrder(itemType: ArchiveTimelineItem['item_type']): number {
  switch (itemType) {
    case 'segment_final':
      return 0
    case 'key_sentence':
      return 1
    case 'exception':
      return 2
    case 'export_created':
      return 3
  }
}

function archiveSegmentElementId(segmentId: string): string {
  return `archive-segment-${segmentId}`
}

function scrollToElement(elementId: string): void {
  document.getElementById(elementId)?.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
  })
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
  showKeyOnly = false,
): ArchiveSegment[] {
  const normalizedQuery = query.trim().toLocaleLowerCase()
  return segments.filter((segment) => {
    if (showKeyOnly && !segment.is_key_sentence) {
      return false
    }
    if (normalizedQuery === '') {
      return true
    }
    return searchableSegmentValues(segment).some((value) =>
      value.toLocaleLowerCase().includes(normalizedQuery),
    )
  })
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
