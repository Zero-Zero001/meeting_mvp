import { useEffect } from 'react'
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
import {
  useSessionStore,
  type CaptureMode,
  type CaptureStatus,
  type ServerSyncStatus,
  type SourcePlatform,
} from '@/stores/session-store'

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

function startButtonLabel(status: CaptureStatus): string {
  switch (status) {
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
  const {
    anonymousClientError,
    anonymousClientStatus,
    captureErrorMessage,
    captureMode,
    captureStatus,
    clientId,
    initializeAnonymousClient,
    remainingSecondsToday,
    serverSyncError,
    serverSyncStatus,
    sourcePlatform,
    beginCapture,
    endSession,
    setCaptureMode,
    setSourcePlatform,
  } = useSessionStore()
  const isRequestingCapture = captureStatus === 'requesting'
  const isCaptureReady = captureStatus === 'ready'
  const canChangeCaptureInputs = !isRequestingCapture && !isCaptureReady
  const quotaMinutes = Math.floor(remainingSecondsToday / 60)
  const clientIdLabel =
    anonymousClientStatus === 'ready' && clientId
      ? clientId.slice(0, 8)
      : '未初始化'
  const audioLabel = audioStatusLabel(captureStatus)
  const asrStatusLabel = isCaptureReady ? '等待音频处理' : '未连接'
  const translationStatusLabel = isCaptureReady ? '等待英文 final' : '未连接'
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
                role="group"
                className="inline-flex w-full rounded-md border border-border bg-background p-1 sm:w-auto"
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
                  disabled={isRequestingCapture || isCaptureReady}
                  onClick={() => void beginCapture(captureMode)}
                  type="button"
                >
                  <Play data-icon="inline-start" />
                  {startButtonLabel(captureStatus)}
                </Button>
                <Button
                  disabled={!isCaptureReady}
                  onClick={endSession}
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
            className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-6"
          >
            <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <UserRound className="size-4 shrink-0" />
                <span>匿名身份</span>
              </div>
              <p className="mt-1 truncate font-medium">{clientIdLabel}</p>
            </div>
            <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <ShieldCheck className="size-4 shrink-0" />
                <span>服务端同步</span>
              </div>
              <p className="mt-1 font-medium">{serverSyncLabel(serverSyncStatus)}</p>
            </div>
            <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock3 className="size-4 shrink-0" />
                <span>今日剩余额度</span>
              </div>
              <p className="mt-1 font-medium">{quotaMinutes} 分钟</p>
            </div>
            <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Activity className="size-4 shrink-0" />
                <span>音频状态</span>
              </div>
              <p className="mt-1 font-medium">{audioLabel}</p>
            </div>
            <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Captions className="size-4 shrink-0" />
                <span>ASR</span>
              </div>
              <p className="mt-1 font-medium">{asrStatusLabel}</p>
            </div>
            <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Languages className="size-4 shrink-0" />
                <span>翻译</span>
              </div>
              <p className="mt-1 font-medium">{translationStatusLabel}</p>
            </div>
          </div>

          <div className="rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
            <p>{captureGuide}</p>
            {captureErrorMessage ? (
              <p className="mt-1 font-medium text-zinc-950" role="status">
                {captureErrorMessage}
              </p>
            ) : null}
            {captureStatus === 'no_audio' ? (
              <p className="mt-1 font-medium text-zinc-950">
                请切换系统音频模式后重新捕获。
              </p>
            ) : null}
          </div>

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
              className="min-h-[260px] min-w-0 rounded-md border border-border bg-background p-4"
            >
              <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
                <h2 className="text-sm font-medium text-muted-foreground">
                  英文原文区
                </h2>
                <span className="text-xs text-muted-foreground">
                  {isCaptureReady ? '实时等待中' : '未开始'}
                </span>
              </div>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground">
                等待英文转写内容。
              </p>
            </section>

            <section
              aria-label="中文翻译区"
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
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground">
                等待中文翻译内容。
              </p>
            </section>
          </div>

          <aside className="grid min-w-0 gap-4 lg:grid-rows-[minmax(220px,0.8fr)_minmax(260px,1fr)]">
            <section
              aria-label="当前重点句区"
              className="min-w-0 rounded-md border border-border bg-background p-4"
            >
              <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
                <h2 className="text-sm font-medium text-muted-foreground">
                  当前重点句区
                </h2>
                <RadioTower className="size-4 text-muted-foreground" />
              </div>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">
                暂无重点句。
              </p>
            </section>

            <section
              aria-label="会议时间线区"
              className="min-w-0 rounded-md border border-border bg-background p-4"
            >
              <div className="flex items-center justify-between gap-3 border-b border-border pb-3">
                <h2 className="text-sm font-medium text-muted-foreground">
                  会议时间线区
                </h2>
                <ListChecks className="size-4 text-muted-foreground" />
              </div>
              <dl className="mt-4 grid gap-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">会议平台</dt>
                  <dd className="font-medium">{sourcePlatformLabel(sourcePlatform)}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">捕获模式</dt>
                  <dd className="font-medium">{captureModeLabel(captureMode)}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">音频状态</dt>
                  <dd className="font-medium">{audioLabel}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">ASR</dt>
                  <dd className="font-medium">{asrStatusLabel}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">翻译</dt>
                  <dd className="font-medium">{translationStatusLabel}</dd>
                </div>
              </dl>
              <p className="mt-4 text-sm leading-6 text-muted-foreground">
                暂无会议事件。
              </p>
            </section>
          </aside>
        </section>
      </section>
    </main>
  )
}

export default App
