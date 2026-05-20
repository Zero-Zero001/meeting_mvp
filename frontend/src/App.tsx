import { useEffect, useState, type ReactNode } from 'react'
import {
  Activity,
  Captions,
  CircleStop,
  Clock3,
  Languages,
  ListChecks,
  Mic2,
  Play,
  RadioTower,
  ShieldCheck,
  UserRound,
  Volume2,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import ArchivePage from '@/archive/ArchivePage'
import UsageDashboardPage from '@/admin/UsageDashboardPage'
import type { ProviderStatus } from '@/protocol/websocket-messages'
import {
  useSessionStore,
  type AudioProcessingStatus,
  type CaptureMode,
  type CaptureStatus,
  type ServerSyncStatus,
  type SourcePlatform,
  type TimelineItem,
  type WebSocketStatus,
} from '@/stores/session-store'

type TimelineItemType =
  | 'segment_final'
  | 'key_sentence'
  | 'export_created'
  | 'exception'
type TimelineFilter = 'all' | TimelineItemType

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

const SOURCE_PLATFORM_OPTIONS: Array<{
  label: string
  value: SourcePlatform
}> = [
  { label: '未知平台', value: 'unknown' },
  { label: 'Google Meet', value: 'google_meet' },
  { label: 'Teams Web', value: 'teams_web' },
  { label: 'Zoom Web', value: 'zoom_web' },
  { label: '腾讯会议 Web', value: 'tencent_meeting_web' },
]

function captureModeLabel(mode: CaptureMode): string {
  return mode === 'tab_audio' ? '标签页音频' : '系统音频'
}

function sourcePlatformLabel(platform: SourcePlatform): string {
  return (
    SOURCE_PLATFORM_OPTIONS.find((option) => option.value === platform)?.label ??
    '未知平台'
  )
}

function serverSyncLabel(status: ServerSyncStatus): string {
  switch (status) {
    case 'synced':
      return '已同步'
    case 'syncing':
      return '同步中'
    case 'error':
      return '稍后重试'
    case 'idle':
      return '待同步'
  }
}

function audioStatusLabel(status: CaptureStatus): string {
  switch (status) {
    case 'idle':
      return '未连接'
    case 'requesting':
      return '等待授权'
    case 'ready':
      return '已捕获音频'
    case 'denied':
      return '授权被拒绝'
    case 'no_audio':
      return '未检测到音频轨道'
    case 'unsupported':
      return '浏览器不支持'
    case 'failed':
      return '捕获失败'
  }
}

function webSocketStatusLabel(status: WebSocketStatus): string {
  switch (status) {
    case 'idle':
      return '未连接'
    case 'connecting':
      return '连接中'
    case 'started':
      return '已建会'
    case 'closing':
      return '关闭中'
    case 'closed':
      return '已关闭'
    case 'error':
      return '连接失败'
  }
}

function audioProcessingStatusLabel(status: AudioProcessingStatus): string {
  switch (status) {
    case 'idle':
      return '未开始'
    case 'starting':
      return '启动中'
    case 'running':
      return '运行中'
    case 'silent':
      return '静音'
    case 'unsupported':
      return '不支持'
    case 'failed':
      return '处理失败'
  }
}

function providerAwareAsrStatusLabel({
  englishFinalCount,
  englishInterimText,
  finalCount,
  providerStatus,
  webSocketStatus,
}: {
  englishFinalCount: number
  englishInterimText: string | null
  finalCount: number
  providerStatus: ProviderStatus | null
  webSocketStatus: WebSocketStatus
}): string {
  switch (providerStatus?.qwen_realtime_asr) {
    case 'disabled':
      return 'ASR 已关闭'
    case 'unconfigured':
      return 'ASR 未配置'
    case 'local_mock':
      return webSocketStatus === 'started' ? '本地 mock' : '未连接'
    case 'enabled':
    case undefined:
      break
  }

  if (englishFinalCount > 0 || finalCount > 0) {
    return `${englishFinalCount + finalCount} 条 final`
  }
  if (englishInterimText) {
    return '收到 interim'
  }
  return webSocketStatus === 'started' ? '等待后端 ASR' : '未连接'
}

function providerAwareTranslationStatusLabel({
  finalCount,
  providerStatus,
  translationInterimText,
  webSocketStatus,
}: {
  finalCount: number
  providerStatus: ProviderStatus | null
  translationInterimText: string | null
  webSocketStatus: WebSocketStatus
}): string {
  const interimStatus = providerStatus?.qwen_interim_translation
  const finalStatus = providerStatus?.qwen_final_translation
  if (interimStatus === 'disabled' && finalStatus === 'disabled') {
    return '翻译已关闭'
  }
  if (finalStatus === 'disabled') {
    return '正式翻译已关闭'
  }
  if (finalStatus === 'unconfigured') {
    return '正式翻译未配置'
  }
  if (interimStatus === 'disabled' && webSocketStatus === 'started') {
    return '临时理解关闭'
  }
  if (interimStatus === 'unconfigured' && webSocketStatus === 'started') {
    return '临时理解未配置'
  }
  if (
    (interimStatus === 'local_mock' || finalStatus === 'local_mock') &&
    webSocketStatus === 'started'
  ) {
    return '本地 mock'
  }

  if (finalCount > 0) {
    return `${finalCount} 条 final`
  }
  if (translationInterimText) {
    return '临时理解'
  }
  return webSocketStatus === 'started' ? '等待英文 final' : '未连接'
}

function startButtonLabel({
  captureStatus,
  identityReady,
  webSocketStatus,
}: {
  captureStatus: CaptureStatus
  identityReady: boolean
  webSocketStatus: WebSocketStatus
}): string {
  if (!identityReady) {
    return '等待身份同步'
  }

  if (webSocketStatus === 'connecting') {
    return '连接中'
  }

  switch (captureStatus) {
    case 'requesting':
      return '等待授权'
    case 'ready':
      return '已捕获'
    case 'denied':
    case 'no_audio':
    case 'unsupported':
    case 'failed':
      return '重新授权'
    case 'idle':
      return '开始捕获'
  }
}

function App() {
  if (isUsageDashboardPath()) {
    return <UsageDashboardPage />
  }

  if (isArchivePath()) {
    return <ArchivePage />
  }

  return <MeetingWorkspace />
}

function MeetingWorkspace() {
  const [timelineFilter, setTimelineFilter] = useState<TimelineFilter>('all')
  const {
    activeNotice,
    anonymousClientError,
    anonymousClientStatus,
    archiveUrl,
    audioLevel,
    audioProcessingStatus,
    captureErrorMessage,
    captureMode,
    captureStatus,
    clientId,
    endSession,
    englishFinalSegments,
    englishInterimText,
    finalSegments,
    hasEffectiveAudio,
    initializeAnonymousClient,
    keySentenceText,
    providerStatus,
    remainingSecondsToday,
    serverSyncError,
    serverSyncStatus,
    sessionId,
    silenceWarning,
    sourcePlatform,
    timelineItems,
    translationInterimText,
    webSocketStatus,
    beginCapture,
    setCaptureMode,
    setSourcePlatform,
  } = useSessionStore()
  const identityReady =
    anonymousClientStatus === 'ready' &&
    clientId !== null &&
    serverSyncStatus === 'synced'
  const isRequestingCapture = captureStatus === 'requesting'
  const isConnecting = webSocketStatus === 'connecting'
  const isProcessingStarting = audioProcessingStatus === 'starting'
  const isPipelineActive =
    captureStatus === 'ready' ||
    webSocketStatus === 'started' ||
    audioProcessingStatus === 'running' ||
    audioProcessingStatus === 'silent'
  const canChangeCaptureInputs =
    !isRequestingCapture && !isConnecting && !isProcessingStarting && !isPipelineActive
  const startDisabled =
    !identityReady ||
    isRequestingCapture ||
    isConnecting ||
    isProcessingStarting ||
    isPipelineActive
  const endDisabled =
    !isRequestingCapture &&
    !isConnecting &&
    !isProcessingStarting &&
    !isPipelineActive
  const quotaMinutes = Math.floor(remainingSecondsToday / 60)
  const clientIdLabel =
    anonymousClientStatus === 'ready' && clientId
      ? clientId.slice(0, 8)
      : '未初始化'
  const audioLabel = audioStatusLabel(captureStatus)
  const webSocketLabel = webSocketStatusLabel(webSocketStatus)
  const audioProcessingLabel =
    audioProcessingStatusLabel(audioProcessingStatus)
  const effectiveAudioLabel = hasEffectiveAudio ? '已检测到' : '等待有效音频'
  const audioLevelLabel = `${Math.round(Math.min(audioLevel, 1) * 100)}%`
  const asrStatusLabel = providerAwareAsrStatusLabel({
    englishFinalCount: englishFinalSegments.length,
    englishInterimText,
    finalCount: finalSegments.length,
    providerStatus,
    webSocketStatus,
  })
  const translationStatusLabel = providerAwareTranslationStatusLabel({
    finalCount: finalSegments.length,
    providerStatus,
    translationInterimText,
    webSocketStatus,
  })
  const captureGuide =
    captureMode === 'system_audio'
      ? '系统音频模式可能包含其他应用声音。'
      : '共享会议标签页时请勾选共享音频。'

  useEffect(() => {
    void initializeAnonymousClient()
  }, [initializeAnonymousClient])

  return (
    <main className="min-h-svh bg-zinc-50 text-foreground">
      <section className="mx-auto flex min-h-svh w-full max-w-7xl flex-col gap-4 px-4 py-4 sm:px-5 lg:px-6">
        <header
          aria-label="会议状态栏"
          className="flex flex-col gap-4 border-b border-border bg-zinc-50 pb-4"
          role="banner"
        >
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-muted-foreground">
                Meeting MVP
              </p>
              <h1 className="text-2xl font-semibold tracking-normal text-zinc-950">
                实时会议工作台
              </h1>
            </div>

            <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center lg:justify-end">
              <label className="grid gap-1 text-xs font-medium text-muted-foreground sm:w-40">
                <span>会议平台</span>
                <select
                  aria-label="会议平台"
                  className="h-9 rounded-md border border-border bg-background px-3 text-sm font-medium text-zinc-950 outline-none transition-colors focus:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!canChangeCaptureInputs}
                  onChange={(event) =>
                    setSourcePlatform(event.target.value as SourcePlatform)
                  }
                  value={sourcePlatform}
                >
                  {SOURCE_PLATFORM_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <div
                aria-label="捕获模式"
                className="inline-flex w-full rounded-md border border-border bg-background p-1 sm:w-auto"
                role="group"
              >
                <Button
                  aria-pressed={captureMode === 'tab_audio'}
                  className="flex-1 sm:flex-none"
                  disabled={!canChangeCaptureInputs}
                  onClick={() => setCaptureMode('tab_audio')}
                  size="sm"
                  type="button"
                  variant={captureMode === 'tab_audio' ? 'secondary' : 'ghost'}
                >
                  <Mic2 data-icon="inline-start" />
                  标签页音频
                </Button>
                <Button
                  aria-pressed={captureMode === 'system_audio'}
                  className="flex-1 sm:flex-none"
                  disabled={!canChangeCaptureInputs}
                  onClick={() => setCaptureMode('system_audio')}
                  size="sm"
                  type="button"
                  variant={captureMode === 'system_audio' ? 'secondary' : 'ghost'}
                >
                  <Volume2 data-icon="inline-start" />
                  系统音频
                </Button>
              </div>

              <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
                <Button
                  disabled={startDisabled}
                  onClick={() => void beginCapture(captureMode)}
                  type="button"
                >
                  <Play data-icon="inline-start" />
                  {startButtonLabel({
                    captureStatus,
                    identityReady,
                    webSocketStatus,
                  })}
                </Button>
                <Button
                  disabled={endDisabled}
                  onClick={() => void endSession()}
                  type="button"
                  variant="outline"
                >
                  <CircleStop data-icon="inline-start" />
                  结束会议
                </Button>
              </div>
            </div>
          </div>

          <div
            aria-live="polite"
            className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-5 xl:grid-cols-9"
          >
            <StatusItem
              icon={<UserRound className="size-4 shrink-0" />}
              label="匿名身份"
              value={clientIdLabel}
            />
            <StatusItem
              icon={<ShieldCheck className="size-4 shrink-0" />}
              label="服务端同步"
              value={serverSyncLabel(serverSyncStatus)}
            />
            <StatusItem
              icon={<Clock3 className="size-4 shrink-0" />}
              label="今日剩余额度"
              value={`${quotaMinutes} 分钟`}
            />
            <StatusItem
              icon={<Activity className="size-4 shrink-0" />}
              label="音频状态"
              value={audioLabel}
            />
            <StatusItem
              icon={<RadioTower className="size-4 shrink-0" />}
              label="WebSocket"
              value={webSocketLabel}
            />
            <StatusItem
              icon={<Volume2 className="size-4 shrink-0" />}
              label="音频处理"
              value={audioProcessingLabel}
            />
            <StatusItem
              icon={<Activity className="size-4 shrink-0" />}
              label="音量电平"
              value={audioLevelLabel}
            />
            <StatusItem
              icon={<Captions className="size-4 shrink-0" />}
              label="ASR"
              value={asrStatusLabel}
            />
            <StatusItem
              icon={<Languages className="size-4 shrink-0" />}
              label="翻译"
              value={translationStatusLabel}
            />
          </div>

          <div className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <StatusItem
              icon={<Activity className="size-4 shrink-0" />}
              label="有效音频"
              value={effectiveAudioLabel}
            />
            <StatusItem
              icon={<RadioTower className="size-4 shrink-0" />}
              label="会话编号"
              value={sessionId ? sessionId.slice(0, 8) : '未创建'}
            />
            <StatusItem
              icon={<ShieldCheck className="size-4 shrink-0" />}
              label="归档入口"
              value={archiveUrl ? '已生成' : '未生成'}
            />
            <StatusItem
              icon={<ListChecks className="size-4 shrink-0" />}
              label="会议平台"
              value={sourcePlatformLabel(sourcePlatform)}
            />
          </div>

          <div className="rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
            <p>{captureGuide}</p>
            {!identityReady ? (
              <p className="mt-1 font-medium text-zinc-950" role="status">
                匿名身份同步完成后才能开始上传音频。
              </p>
            ) : null}
            {captureErrorMessage ? (
              <p className="mt-1 font-medium text-zinc-950">
                {captureErrorMessage}
              </p>
            ) : null}
            {captureStatus === 'no_audio' ? (
              <p className="mt-1 font-medium text-zinc-950">
                请切换系统音频模式后重新捕获。
              </p>
            ) : null}
            {silenceWarning ? (
              <p className="mt-1 font-medium text-zinc-950">
                30 秒内未检测到有效音频，请检查共享音频。
              </p>
            ) : null}
          </div>

          {activeNotice ? (
            <div
              aria-live={activeNotice.severity === 'error' ? 'assertive' : 'polite'}
              className={
                activeNotice.severity === 'error'
                  ? 'rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950'
                  : 'rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950'
              }
              role={activeNotice.severity === 'error' ? 'alert' : 'status'}
            >
              <p className="font-medium">{activeNotice.title}</p>
              <p className="mt-1 text-sm">{activeNotice.message}</p>
              <p className="mt-1 text-sm">{activeNotice.action}</p>
            </div>
          ) : null}

          {anonymousClientError || serverSyncError ? (
            <p className="text-sm text-muted-foreground">
              {anonymousClientError
                ? '请启用浏览器本地存储后继续使用。'
                : '本地匿名身份已生成，服务端同步稍后重试。'}
            </p>
          ) : null}
        </header>

        <section className="grid flex-1 gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
          <div className="grid min-w-0 gap-4 lg:grid-rows-2">
            <section
              aria-label="英文原文区"
              aria-live="polite"
              className="min-h-[260px] min-w-0 rounded-md border border-border bg-background p-4"
            >
              <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
                <h2 className="text-sm font-medium text-muted-foreground">
                  英文原文区
                </h2>
                <span className="text-xs text-muted-foreground">
                  {webSocketStatus === 'started' ? '等待后端事件' : '未开始'}
                </span>
              </div>
              <div className="mt-4 space-y-3">
                {englishInterimText ? (
                  <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                    {englishInterimText}
                  </p>
                ) : null}
                {englishFinalSegments.map((segment) => (
                  <article
                    className="max-w-3xl border-l-2 border-zinc-300 pl-3"
                    key={`${segment.sequence}-${segment.end_ms}-${segment.text}`}
                  >
                    <p className="text-sm leading-6 text-zinc-950">
                      {segment.text}
                    </p>
                  </article>
                ))}
                {finalSegments.map((segment) => (
                  <article
                    className="max-w-3xl border-l-2 border-zinc-300 pl-3"
                    id={realtimeSegmentElementId(segment.segment_id)}
                    key={segment.segment_id}
                  >
                    <p className="text-sm leading-6 text-zinc-950">
                      {segment.english_text_final}
                    </p>
                  </article>
                ))}
                {!englishInterimText &&
                englishFinalSegments.length === 0 &&
                finalSegments.length === 0 ? (
                  <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                    等待英文转写内容。
                  </p>
                ) : null}
              </div>
            </section>

            <section
              aria-label="中文翻译区"
              aria-live="polite"
              className="min-h-[260px] min-w-0 rounded-md border border-border bg-background p-4"
            >
              <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
                <h2 className="text-sm font-medium text-muted-foreground">
                  中文翻译区
                </h2>
                <span className="text-xs text-muted-foreground">
                  {translationStatusLabel}
                </span>
              </div>
              <div className="mt-4 space-y-3">
                {translationInterimText ? (
                  <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                    {translationInterimText}
                  </p>
                ) : null}
                {finalSegments.map((segment) => (
                  <article
                    className="max-w-3xl border-l-2 border-zinc-300 pl-3"
                    data-segment-id={segment.segment_id}
                    key={segment.segment_id}
                  >
                    <p className="text-sm leading-6 text-zinc-950">
                      {segment.chinese_text_final}
                    </p>
                  </article>
                ))}
                {!translationInterimText && finalSegments.length === 0 ? (
                  <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                    等待中文翻译内容。
                  </p>
                ) : null}
              </div>
            </section>
          </div>

          <aside className="grid min-w-0 gap-4 lg:grid-rows-[minmax(220px,0.8fr)_minmax(260px,1fr)]">
            <section
              aria-label="当前重点句区"
              aria-live="polite"
              className="min-w-0 rounded-md border border-border bg-background p-4"
            >
              <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
                <h2 className="text-sm font-medium text-muted-foreground">
                  当前重点句区
                </h2>
                <RadioTower className="size-4 text-muted-foreground" />
              </div>
              <p className="mt-4 text-sm leading-6 text-zinc-950">
                {keySentenceText ?? '暂无重点句。'}
              </p>
            </section>

            <section
              aria-label="会议时间线区"
              aria-live="polite"
              className="min-w-0 rounded-md border border-border bg-background p-4"
            >
              <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
                <h2 className="text-sm font-medium text-muted-foreground">
                  会议时间线区
                </h2>
                <ListChecks className="size-4 text-muted-foreground" />
              </div>
              <dl className="mt-4 grid gap-3 text-sm">
                <TimelineStatusItem label="会议平台" value={sourcePlatformLabel(sourcePlatform)} />
                <TimelineStatusItem label="捕获模式" value={captureModeLabel(captureMode)} />
                <TimelineStatusItem label="音频状态" value={audioLabel} />
                <TimelineStatusItem label="WebSocket" value={webSocketLabel} />
                <TimelineStatusItem label="有效音频" value={effectiveAudioLabel} />
                <TimelineStatusItem label="ASR" value={asrStatusLabel} />
                <TimelineStatusItem label="翻译" value={translationStatusLabel} />
              </dl>
              {timelineItems.length > 0 ? (
                <>
                  <TimelineFilterButtons
                    activeFilter={timelineFilter}
                    ariaLabel="筛选会议时间线"
                    className="mt-4"
                    onFilterChange={setTimelineFilter}
                  />
                  <TimelineEventList
                    emptyMessage="当前筛选下暂无会议事件。"
                    items={filterTimelineItems(timelineItems, timelineFilter)}
                    onSelectSegment={(segmentId) =>
                      scrollToElement(realtimeSegmentElementId(segmentId))
                    }
                  />
                </>
              ) : (
                <p className="mt-4 text-sm leading-6 text-muted-foreground">
                  暂无会议事件。
                </p>
              )}
            </section>
          </aside>
        </section>
      </section>
    </main>
  )
}

function formatTimestamp(timestampMs: number): string {
  const totalSeconds = Math.floor(timestampMs / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function StatusItem({
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

function TimelineStatusItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  )
}

function TimelineFilterButtons({
  activeFilter,
  ariaLabel,
  className,
  onFilterChange,
}: {
  activeFilter: TimelineFilter
  ariaLabel: string
  className?: string
  onFilterChange: (filter: TimelineFilter) => void
}) {
  return (
    <div
      aria-label={ariaLabel}
      className={`inline-flex w-full rounded-md border border-border bg-background p-1 sm:w-auto ${
        className ?? ''
      }`}
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
  items: TimelineItem[]
  onSelectSegment: (segmentId: string) => void
}) {
  if (items.length === 0) {
    return (
      <p className="mt-4 text-sm leading-6 text-muted-foreground">
        {emptyMessage}
      </p>
    )
  }

  return (
    <ol className="mt-4 grid gap-3 text-sm">
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

function TimelineEventContent({ item }: { item: TimelineItem }) {
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

function filterTimelineItems(
  items: TimelineItem[],
  activeFilter: TimelineFilter,
): TimelineItem[] {
  if (activeFilter === 'all') {
    return items
  }
  return items.filter((item) => item.item_type === activeFilter)
}

function timelineTypeLabel(itemType: string): string {
  switch (itemType) {
    case 'segment_final':
      return 'final'
    case 'key_sentence':
      return '重点句'
    case 'export_created':
      return '导出事件'
    case 'exception':
      return '异常'
    default:
      return itemType
  }
}

function realtimeSegmentElementId(segmentId: string): string {
  return `realtime-segment-${segmentId}`
}

function scrollToElement(elementId: string): void {
  document.getElementById(elementId)?.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
  })
}

function isArchivePath(): boolean {
  if (typeof window === 'undefined') {
    return false
  }
  return window.location.pathname.startsWith('/archive/')
}

function isUsageDashboardPath(): boolean {
  if (typeof window === 'undefined') {
    return false
  }
  return window.location.pathname === '/admin/usage-dashboard'
}

export default App
