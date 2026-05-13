import { expect, test, type Page } from '@playwright/test'

declare global {
  interface Window {
    __audioWorkletNode: {
      port: {
        onmessage?: ((event: MessageEvent) => void) | null
      }
    }
    __meetingWebSocket: unknown
    __sentBinaryFrames: number[]
  }
}

type CaptureMockMode = 'success' | 'denied' | 'no_audio'

async function mockBrowserPipeline(page: Page, mode: CaptureMockMode) {
  await page.addInitScript((captureMode) => {
    window.localStorage.setItem(
      'meeting_mvp.client_id',
      '11111111-1111-4111-8111-111111111111',
    )

    const syncResponse = {
      client_id: '11111111-1111-4111-8111-111111111111',
      daily_free_seconds: 2400,
      is_new: false,
      remaining_seconds_today: 2400,
    }

    window.fetch = async () =>
      new Response(JSON.stringify(syncResponse), {
        headers: { 'content-type': 'application/json' },
        status: 200,
      })

    function createTrack(kind: 'audio' | 'video') {
      return {
        kind,
        stop() {},
      }
    }

    function createStream(audioTrackCount: number) {
      const audioTracks = Array.from({ length: audioTrackCount }, () =>
        createTrack('audio'),
      )
      const tracks = [...audioTracks, createTrack('video')]

      return {
        getAudioTracks: () => audioTracks,
        getTracks: () => tracks,
      }
    }

    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getDisplayMedia: async () => {
          if (captureMode === 'denied') {
            throw new DOMException('Permission denied', 'NotAllowedError')
          }

          return createStream(captureMode === 'no_audio' ? 0 : 1)
        },
      },
    })

    window.__sentBinaryFrames = []

    class FakeWebSocket {
      static CLOSED = 3
      static CONNECTING = 0
      static OPEN = 1

      binaryType = 'blob'
      onclose = null
      onerror = null
      onmessage = null
      onopen = null
      readyState = WebSocket.CONNECTING

      constructor() {
        window.__meetingWebSocket = this
        queueMicrotask(() => {
          this.readyState = WebSocket.OPEN
          this.onopen?.(new Event('open'))
        })
      }

      send(data) {
        if (data instanceof ArrayBuffer) {
          window.__sentBinaryFrames.push(data.byteLength)
          queueMicrotask(() => {
            this.onmessage?.(
              new MessageEvent('message', {
                data: JSON.stringify({
                  text: 'We need to align on the launch timeline.',
                  type: 'asr_interim',
                }),
              }),
            )
            this.onmessage?.(
              new MessageEvent('message', {
                data: JSON.stringify({
                  confidence: 0.91,
                  end_ms: 2800,
                  sequence: 1,
                  start_ms: 0,
                  text: 'We need to align before Friday.',
                  type: 'asr_final',
                }),
              }),
            )
            this.onmessage?.(
              new MessageEvent('message', {
                data: JSON.stringify({
                  text: '我们需要对齐上线时间线。',
                  type: 'translation_interim',
                }),
              }),
            )
            this.onmessage?.(
              new MessageEvent('message', {
                data: JSON.stringify({
                  chinese_text_final: '我们需要在周五前对齐上线时间线。',
                  end_ms: 3200,
                  english_text_final:
                    'We need to align on the launch timeline before Friday.',
                  segment_id: 'segment-1',
                  sequence: 1,
                  start_ms: 0,
                  type: 'segment_final',
                }),
              }),
            )
            this.onmessage?.(
              new MessageEvent('message', {
                data: JSON.stringify({
                  chinese_text_final: '我们需要在周五前对齐上线时间线。',
                  end_ms: 3200,
                  english_text_final:
                    'We need to align on the launch timeline before Friday.',
                  segment_id: 'segment-1',
                  sequence: 1,
                  start_ms: 0,
                  type: 'segment_final',
                }),
              }),
            )
            this.onmessage?.(
              new MessageEvent('message', {
                data: JSON.stringify({
                  text: '我们需要在周五前对齐上线时间线。',
                  type: 'key_sentence_update',
                }),
              }),
            )
            this.onmessage?.(
              new MessageEvent('message', {
                data: JSON.stringify({
                  items: [
                    {
                      id: 'timeline-1',
                      item_type: 'segment_final',
                      segment_id: 'segment-1',
                      text: '我们需要在周五前对齐上线时间线。',
                      timestamp_ms: 3200,
                    },
                  ],
                  type: 'timeline_update',
                }),
              }),
            )
          })
          return
        }

        const payload = JSON.parse(data)
        if (payload.type === 'session_start') {
          queueMicrotask(() => {
            this.onmessage?.(
              new MessageEvent('message', {
                data: JSON.stringify({
                  archive_token: 'archive-token',
                  archive_url: '/archive/session-1?token=archive-token',
                  remaining_seconds_today: 2400,
                  session_id: 'session-1',
                  type: 'session_started',
                }),
              }),
            )
          })
        }
      }

      close() {
        this.readyState = WebSocket.CLOSED
        this.onclose?.(new CloseEvent('close'))
      }
    }

    class FakeAudioContext {
      audioWorklet = {
        addModule: async () => undefined,
      }
      close = async () => undefined
      createMediaStreamSource = () => ({
        connect() {},
        disconnect() {},
      })
      resume = async () => undefined
      sampleRate = 48000
      state = 'running'
    }

    class FakeAudioWorkletNode {
      constructor() {
        this.port = {
          onmessage: null,
        }
        window.__audioWorkletNode = this
      }

      disconnect() {}
    }

    Object.defineProperty(window, 'WebSocket', {
      configurable: true,
      value: FakeWebSocket,
    })
    Object.defineProperty(window, 'AudioContext', {
      configurable: true,
      value: FakeAudioContext,
    })
    Object.defineProperty(window, 'AudioWorkletNode', {
      configurable: true,
      value: FakeAudioWorkletNode,
    })
  }, mode)
}

async function emitAudioSamples(page: Page, value: number) {
  await page.evaluate((sampleValue) => {
    window.__audioWorkletNode.port.onmessage?.(
      new MessageEvent('message', {
        data: {
          channels: [new Float32Array(4800).fill(sampleValue)],
          inputSampleRate: 48000,
          type: 'audio_samples',
        },
      }),
    )
  }, value)
}

test('renders the desktop workspace shell', async ({ page }) => {
  await mockBrowserPipeline(page, 'success')
  await page.setViewportSize({ width: 1366, height: 900 })
  await page.goto('/')

  await expect(
    page.getByRole('heading', { name: '实时会议工作台' }),
  ).toBeVisible()
  const statusBar = page.getByRole('banner', { name: '会议状态栏' })
  await expect(statusBar).toBeVisible()
  await expect(page.getByRole('region', { name: '英文原文区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '中文翻译区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '当前重点句区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '会议时间线区' })).toBeVisible()
  await expect(page.getByRole('button', { name: '开始捕获' })).toBeVisible()
  await expect(page.getByRole('button', { name: '标签页音频' })).toBeVisible()
  await expect(page.getByRole('button', { name: '系统音频' })).toBeVisible()
  await expect(statusBar.getByText('WebSocket')).toBeVisible()
  await expect(statusBar.getByText('音频处理')).toBeVisible()
  await expect(statusBar.getByText('ASR')).toBeVisible()
  await expect(statusBar.getByText('翻译')).toBeVisible()
  await expect(page.getByRole('combobox', { name: '会议平台' })).toBeVisible()

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalOverflow).toBe(false)
})

test('renders the mobile workspace without horizontal overflow', async ({ page }) => {
  await mockBrowserPipeline(page, 'success')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')

  const statusBar = page.getByRole('banner', { name: '会议状态栏' })
  await expect(statusBar).toBeVisible()
  await expect(page.getByRole('region', { name: '英文原文区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '中文翻译区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '当前重点句区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '会议时间线区' })).toBeVisible()

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalOverflow).toBe(false)
})

test('uploads only effective PCM16 audio frames after session_started', async ({
  page,
}) => {
  await mockBrowserPipeline(page, 'success')
  await page.goto('/')

  await page.getByRole('button', { name: '开始捕获' }).click()
  const statusBar = page.getByRole('banner', { name: '会议状态栏' })
  await expect(statusBar.getByText('已建会')).toBeVisible()

  await emitAudioSamples(page, 0.1)

  await expect(statusBar.getByText('已检测到')).toBeVisible()
  await expect
    .poll(() => page.evaluate(() => window.__sentBinaryFrames.length))
    .toBeGreaterThan(0)
  await expect
    .poll(() => page.evaluate(() => window.__sentBinaryFrames[0]))
    .toBe(3200)
  await expect(
    page.getByRole('region', { name: '英文原文区' }).getByText(
      'We need to align before Friday.',
    ),
  ).toHaveCount(0)
  await expect(
    page.getByRole('region', { name: '英文原文区' }).getByText(
      'We need to align on the launch timeline before Friday.',
    ),
  ).toHaveCount(1)
  await expect(
    page.getByRole('region', { name: '中文翻译区' }).getByText(
      '我们需要在周五前对齐上线时间线。',
    ),
  ).toHaveCount(1)
  await expect(
    page.getByRole('region', { name: '当前重点句区' }).getByText(
      '我们需要在周五前对齐上线时间线。',
    ),
  ).toBeVisible()
  await expect(
    page.getByRole('region', { name: '会议时间线区' }).getByText(
      '我们需要在周五前对齐上线时间线。',
    ),
  ).toBeVisible()
})

test('does not upload silent audio frames', async ({ page }) => {
  await mockBrowserPipeline(page, 'success')
  await page.goto('/')

  await page.getByRole('button', { name: '开始捕获' }).click()
  const statusBar = page.getByRole('banner', { name: '会议状态栏' })
  await expect(statusBar.getByText('已建会')).toBeVisible()

  await emitAudioSamples(page, 0)

  await expect(statusBar.getByText('等待有效音频')).toBeVisible()
  expect(await page.evaluate(() => window.__sentBinaryFrames.length)).toBe(0)
})

test('shows retry guidance when display capture is denied', async ({ page }) => {
  await mockBrowserPipeline(page, 'denied')
  await page.goto('/')

  await page.getByRole('button', { name: '开始捕获' }).click()

  await expect(page.getByText('浏览器拒绝了捕获授权。')).toBeVisible()
  await expect(page.getByRole('button', { name: '重新授权' })).toBeVisible()
})

test('shows system audio fallback guidance when capture has no audio track', async ({
  page,
}) => {
  await mockBrowserPipeline(page, 'no_audio')
  await page.goto('/')

  await page.getByRole('button', { name: '开始捕获' }).click()

  await expect(page.getByText('请切换系统音频模式后重新捕获。')).toBeVisible()
})
