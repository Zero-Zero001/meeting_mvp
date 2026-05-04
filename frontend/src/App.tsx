import { Activity, CircleStop, Play } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useSessionStore } from '@/stores/session-store'

function App() {
  const {
    captureMode,
    remainingSecondsToday,
    status,
    beginCapture,
    endSession,
  } = useSessionStore()
  const isCapturing = status === 'capturing'
  const quotaMinutes = Math.floor(remainingSecondsToday / 60)

  return (
    <main className="min-h-svh bg-background text-foreground">
      <section className="mx-auto flex min-h-svh w-full max-w-6xl flex-col gap-6 px-5 py-6">
        <header className="flex flex-col gap-4 border-b border-border pb-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              Meeting MVP
            </p>
            <h1 className="text-2xl font-semibold tracking-normal">
              实时会议工作台
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex h-9 items-center gap-2 rounded-lg border border-border px-3 text-sm">
              <Activity className="size-4 text-muted-foreground" />
              <span>{isCapturing ? '捕获中' : '未连接'}</span>
            </div>
            <Button
              type="button"
              onClick={() => beginCapture('tab_audio')}
              disabled={isCapturing}
            >
              <Play data-icon="inline-start" />
              开始捕获
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={endSession}
              disabled={!isCapturing}
            >
              <CircleStop data-icon="inline-start" />
              结束会议
            </Button>
          </div>
        </header>

        <section className="grid flex-1 gap-4 md:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.6fr)]">
          <div className="grid gap-4 md:grid-rows-2">
            <section className="rounded-lg border border-border p-4">
              <h2 className="text-sm font-medium text-muted-foreground">
                英文原文区
              </h2>
              <p className="mt-4 text-sm text-muted-foreground">
                尚无英文转写内容。
              </p>
            </section>

            <section className="rounded-lg border border-border p-4">
              <h2 className="text-sm font-medium text-muted-foreground">
                中文翻译区
              </h2>
              <p className="mt-4 text-sm text-muted-foreground">
                尚无中文翻译内容。
              </p>
            </section>
          </div>

          <aside className="grid gap-4">
            <section className="rounded-lg border border-border p-4">
              <h2 className="text-sm font-medium text-muted-foreground">
                当前重点句区
              </h2>
              <p className="mt-4 text-sm text-muted-foreground">
                暂无重点句。
              </p>
            </section>

            <section className="rounded-lg border border-border p-4">
              <h2 className="text-sm font-medium text-muted-foreground">
                会议时间线区
              </h2>
              <p className="mt-4 text-sm text-muted-foreground">
                暂无时间线节点。
              </p>
              <dl className="mt-4 grid gap-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">捕获模式</dt>
                  <dd>
                    {captureMode === 'tab_audio' ? '标签页音频' : '系统音频'}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">今日剩余额度</dt>
                  <dd>{quotaMinutes} 分钟</dd>
                </div>
              </dl>
            </section>
          </aside>
        </section>
      </section>
    </main>
  )
}

export default App
