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
  type ServerSyncStatus,
} from '@/stores/session-store'

function captureModeLabel(mode: CaptureMode): string {
  return mode === 'tab_audio' ? '标签页音频' : '系统音频'
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

function App() {
  const {
    anonymousClientError,
    anonymousClientStatus,
    captureMode,
    clientId,
    initializeAnonymousClient,
    remainingSecondsToday,
    serverSyncError,
    serverSyncStatus,
    status,
    beginCapture,
    endSession,
    setCaptureMode,
  } = useSessionStore()
  const isCapturing = status === 'capturing'
  const quotaMinutes = Math.floor(remainingSecondsToday / 60)
  const clientIdLabel =
    anonymousClientStatus === 'ready' && clientId
      ? clientId.slice(0, 8)
      : '未初始化'
  const audioStatusLabel = isCapturing ? '捕获中' : '未连接'
  const asrStatusLabel = isCapturing ? '等待音频' : '未连接'
  const translationStatusLabel = isCapturing ? '等待英文 final' : '未连接'

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
              <div
                aria-label="捕获模式"
                role="group"
                className="inline-flex w-full rounded-md border border-border bg-background p-1 sm:w-auto"
              >
                <Button
                  aria-pressed={captureMode === 'tab_audio'}
                  className="flex-1 sm:flex-none"
                  disabled={isCapturing}
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
                  disabled={isCapturing}
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
                  disabled={isCapturing}
                  onClick={() => beginCapture(captureMode)}
                  type="button"
                >
                  <Play data-icon="inline-start" />
                  开始捕获
                </Button>
                <Button
                  disabled={!isCapturing}
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
              <p className="mt-1 font-medium">{audioStatusLabel}</p>
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
                  {isCapturing ? '实时等待中' : '未开始'}
                </span>
              </div>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-muted-foreground">
                等待英文转写。Step 12 仅保留工作台占位，开始捕获不会调用真实音频 API。
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
                等待中文翻译。interim 与 final 数据流会在后续步骤接入。
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
                暂无重点句。后续实时链路会把当前最值得关注的英文句子和中文理解推送到这里。
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
                  <dt className="text-muted-foreground">捕获模式</dt>
                  <dd className="font-medium">{captureModeLabel(captureMode)}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">音频状态</dt>
                  <dd className="font-medium">{audioStatusLabel}</dd>
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
                暂无会议事件。会话创建、有效音频、final 片段和异常降级会在后续步骤进入时间线。
              </p>
            </section>
          </aside>
        </section>
      </section>
    </main>
  )
}

export default App
