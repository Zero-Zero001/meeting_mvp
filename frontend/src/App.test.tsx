import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { initialSessionState, useSessionStore } from './stores/session-store'

const originalMediaDevices = navigator.mediaDevices
const originalWebSocket = window.WebSocket
const OriginalAudioContext = window.AudioContext
const OriginalAudioWorkletNode = window.AudioWorkletNode

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  static CLOSED = 3
  static CONNECTING = 0
  static OPEN = 1

  binaryType: BinaryType = 'blob'
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onopen: ((event: Event) => void) | null = null
  readyState = WebSocket.CONNECTING
  sent: unknown[] = []

  constructor() {
    FakeWebSocket.instances.push(this)
    queueMicrotask(() => {
      this.readyState = WebSocket.OPEN
      this.onopen?.(new Event('open'))
    })
  }

  send(data: unknown) {
    this.sent.push(data)
    if (typeof data === 'string' && JSON.parse(data).type === 'session_start') {
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
    addModule: vi.fn().mockResolvedValue(undefined),
  }
  createMediaStreamSource = vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  }))
  close = vi.fn().mockResolvedValue(undefined)
  resume = vi.fn().mockResolvedValue(undefined)
  sampleRate = 48000
  state = 'running'
}

class FakeAudioWorkletNode {
  static instances: FakeAudioWorkletNode[] = []

  disconnect = vi.fn()
  port = {
    onmessage: null as ((event: MessageEvent) => void) | null,
  }

  constructor() {
    FakeAudioWorkletNode.instances.push(this)
  }
}

function createTrack(kind: 'audio' | 'video' = 'audio') {
  return {
    kind,
    stop: vi.fn(),
  } as unknown as MediaStreamTrack
}

function createStream(audioTrackCount = 1) {
  const audioTracks = Array.from({ length: audioTrackCount }, () =>
    createTrack('audio'),
  )
  const videoTrack = createTrack('video')
  const tracks = [...audioTracks, videoTrack]

  return {
    getAudioTracks: () => audioTracks,
    getTracks: () => tracks,
  } as unknown as MediaStream
}

function mockDisplayMediaWithStream(stream: MediaStream) {
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getDisplayMedia: vi.fn().mockResolvedValue(stream),
    },
  })
}

function mockDisplayMediaWithError(error: unknown) {
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getDisplayMedia: vi.fn().mockRejectedValue(error),
    },
  })
}

function setReadyIdentity() {
  useSessionStore.setState({
    ...initialSessionState,
    anonymousClientStatus: 'ready',
    clientId: '11111111-1111-4111-8111-111111111111',
    remainingSecondsToday: 1500,
    serverSyncStatus: 'synced',
  })
}

function installRealtimeMocks() {
  FakeWebSocket.instances = []
  FakeAudioWorkletNode.instances = []
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
}

describe('App', () => {
  beforeEach(() => {
    useSessionStore.setState(initialSessionState)
    setReadyIdentity()
    installRealtimeMocks()
  })

  afterEach(() => {
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: originalMediaDevices,
    })
    Object.defineProperty(window, 'WebSocket', {
      configurable: true,
      value: originalWebSocket,
    })
    Object.defineProperty(window, 'AudioContext', {
      configurable: true,
      value: OriginalAudioContext,
    })
    Object.defineProperty(window, 'AudioWorkletNode', {
      configurable: true,
      value: OriginalAudioWorkletNode,
    })
  })

  it('renders the meeting workspace shell', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: '实时会议工作台' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('banner', { name: '会议状态栏' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: '英文原文区' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: '中文翻译区' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: '当前重点句区' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: '会议时间线区' })).toBeInTheDocument()
  })

  it('marks all realtime workspace regions as polite live regions', () => {
    render(<App />)

    expect(screen.getByRole('region', { name: '英文原文区' })).toHaveAttribute(
      'aria-live',
      'polite',
    )
    expect(screen.getByRole('region', { name: '中文翻译区' })).toHaveAttribute(
      'aria-live',
      'polite',
    )
    expect(screen.getByRole('region', { name: '当前重点句区' })).toHaveAttribute(
      'aria-live',
      'polite',
    )
    expect(screen.getByRole('region', { name: '会议时间线区' })).toHaveAttribute(
      'aria-live',
      'polite',
    )
  })

  it('renders status bar controls and session metadata', () => {
    render(<App />)
    const statusBar = within(screen.getByRole('banner', { name: '会议状态栏' }))

    expect(screen.getByRole('button', { name: '标签页音频' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: '系统音频' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(statusBar.getByText('音频状态')).toBeInTheDocument()
    expect(statusBar.getByText('WebSocket')).toBeInTheDocument()
    expect(statusBar.getByText('音频处理')).toBeInTheDocument()
    expect(statusBar.getByText('音量电平')).toBeInTheDocument()
    expect(statusBar.getByText('有效音频')).toBeInTheDocument()
    expect(statusBar.getByText('ASR')).toBeInTheDocument()
    expect(statusBar.getByText('翻译')).toBeInTheDocument()
    expect(statusBar.getAllByText('会议平台').length).toBeGreaterThan(0)
    expect(statusBar.getByText('25 分钟')).toBeInTheDocument()
    expect(statusBar.getByText('11111111')).toBeInTheDocument()
    expect(statusBar.getByText('已同步')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: '会议平台' })).toHaveValue(
      'unknown',
    )
  })

  it('switches capture mode from the toolbar without starting capture', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '系统音频' }))

    expect(screen.getByRole('button', { name: '系统音频' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: '标签页音频' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    const statusBar = within(screen.getByRole('banner', { name: '会议状态栏' }))
    expect(statusBar.getAllByText('未连接').length).toBeGreaterThan(0)
  })

  it('captures display audio, starts websocket, and shows audio processing state', async () => {
    const user = userEvent.setup()
    mockDisplayMediaWithStream(createStream())
    render(<App />)

    await user.click(screen.getByRole('button', { name: '开始捕获' }))

    const statusBar = within(screen.getByRole('banner', { name: '会议状态栏' }))
    expect(await statusBar.findByText('已建会')).toBeInTheDocument()
    expect(statusBar.getByText('运行中')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '已捕获' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '结束会议' })).toBeEnabled()
  })

  it('updates audio level and effective audio state from worklet samples', async () => {
    const user = userEvent.setup()
    mockDisplayMediaWithStream(createStream())
    render(<App />)

    await user.click(screen.getByRole('button', { name: '开始捕获' }))
    const statusBar = within(screen.getByRole('banner', { name: '会议状态栏' }))
    await statusBar.findByText('已建会')

    FakeAudioWorkletNode.instances[0].port.onmessage?.(
      new MessageEvent('message', {
        data: {
          channels: [new Float32Array(4800).fill(0.1)],
          inputSampleRate: 48000,
          type: 'audio_samples',
        },
      }),
    )

    expect(await statusBar.findByText('已检测到')).toBeInTheDocument()
    expect(statusBar.getByText('10%')).toBeInTheDocument()
  })

  it('shows a 30 second silence warning from the audio pipeline', () => {
    useSessionStore.setState({
      ...useSessionStore.getState(),
      activeNotice: {
        action: '确认会议中有人讲话，并检查共享音频；必要时切换系统音频。',
        code: 'audio_silent_timeout',
        message: '已捕获窗口或屏幕，但 30 秒内没有有效声音，静音帧不会上传。',
        severity: 'warning',
        title: '暂未检测到会议声音',
      },
      audioPipelineErrorCode: 'audio_silent_timeout',
      audioProcessingStatus: 'silent',
      silenceWarning: true,
    })

    render(<App />)

    expect(
      screen.getByText('30 秒内未检测到有效音频，请检查共享音频。'),
    ).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('暂未检测到会议声音')
  })

  it('renders blocking degradation notices as alerts without hiding workspace content', () => {
    useSessionStore.setState({
      ...useSessionStore.getState(),
      activeNotice: {
        action: '稍后重新开始会议；已经归档的 final 片段会保留。',
        code: 'qwen_asr_error',
        message: '核心 ASR 连接异常，本场实时转写无法继续。',
        severity: 'error',
        title: '英文转写服务暂时不可用',
      },
      finalSegments: [
        {
          chinese_text_final: '预算审查调整到周五。',
          end_ms: 2400,
          english_text_final: 'The budget review moved to Friday.',
          segment_id: 'segment-1',
          sequence: 1,
          start_ms: 0,
          type: 'segment_final',
        },
      ],
    })

    render(<App />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      '英文转写服务暂时不可用',
    )
    expect(
      within(screen.getByRole('region', { name: '英文原文区' })).getByText(
        'The budget review moved to Friday.',
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: '中文翻译区' })).getByText(
        '预算审查调整到周五。',
      ),
    ).toBeInTheDocument()
  })

  it('renders realtime mock provider transcript, translation, key sentence, and timeline content', () => {
    useSessionStore.setState({
      ...useSessionStore.getState(),
      englishInterimText: 'We need to align on the launch timeline.',
      englishFinalSegments: [
        {
          confidence: 0.91,
          end_ms: 2800,
          sequence: 1,
          start_ms: 0,
          text: 'We need to align before Friday.',
          type: 'asr_final',
        },
      ],
      finalSegments: [
        {
          chinese_text_final: '我们需要在周五前对齐上线时间线。',
          end_ms: 3200,
          english_text_final: 'We need to align on the launch timeline before Friday.',
          segment_id: 'segment-1',
          sequence: 1,
          start_ms: 0,
          type: 'segment_final',
        },
      ],
      keySentenceText: '我们需要在周五前对齐上线时间线。',
      timelineItems: [
        {
          id: 'timeline-1',
          item_type: 'segment_final',
          segment_id: 'segment-1',
          text: '我们需要在周五前对齐上线时间线。',
          timestamp_ms: 3200,
        },
      ],
      translationInterimText: '我们需要对齐上线时间线。',
    })

    render(<App />)

    expect(
      within(screen.getByRole('region', { name: '英文原文区' })).getByText(
        'We need to align on the launch timeline.',
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: '英文原文区' })).getByText(
        'We need to align on the launch timeline before Friday.',
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: '英文原文区' })).getByText(
        'We need to align before Friday.',
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: '中文翻译区' })).getByText(
        '我们需要对齐上线时间线。',
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: '中文翻译区' })).getByText(
        '我们需要在周五前对齐上线时间线。',
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: '当前重点句区' })).getByText(
        '我们需要在周五前对齐上线时间线。',
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getByRole('region', { name: '会议时间线区' })).getByText(
        '我们需要在周五前对齐上线时间线。',
      ),
    ).toBeInTheDocument()
  })

  it('filters realtime timeline nodes and scrolls to linked final segments', async () => {
    const user = userEvent.setup()
    const scrollIntoView = vi.fn()
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    })
    useSessionStore.setState({
      ...useSessionStore.getState(),
      finalSegments: [
        {
          chinese_text_final: '预算审查调整到周五。',
          end_ms: 2400,
          english_text_final: 'The budget review moved to Friday.',
          segment_id: 'segment-1',
          sequence: 1,
          start_ms: 0,
          type: 'segment_final',
        },
      ],
      timelineItems: [
        {
          id: 'segment-final-segment-1',
          item_type: 'segment_final',
          segment_id: 'segment-1',
          text: '预算审查调整到周五。',
          timestamp_ms: 2400,
        },
        {
          id: 'key-sentence-segment-1',
          item_type: 'key_sentence',
          segment_id: 'segment-1',
          text: '预算审查调整到周五。',
          timestamp_ms: 2400,
        },
        {
          id: 'export-created-export-1',
          item_type: 'export_created',
          text: '已生成 Markdown 导出',
          timestamp_ms: 540000,
        },
        {
          id: 'exception-qwen_asr_error-0',
          item_type: 'exception',
          text: '英文转写服务异常',
          timestamp_ms: 0,
        },
      ],
    })

    render(<App />)
    const timelineRegion = within(
      screen.getByRole('region', { name: '会议时间线区' }),
    )

    await user.click(timelineRegion.getByRole('button', { name: '导出' }))
    expect(timelineRegion.getByText('已生成 Markdown 导出')).toBeInTheDocument()
    expect(timelineRegion.queryByText('英文转写服务异常')).not.toBeInTheDocument()

    await user.click(timelineRegion.getByRole('button', { name: '全部' }))
    await user.click(timelineRegion.getAllByRole('button', { name: /预算审查/ })[0])

    expect(scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'center',
    })
  })

  it('keeps Chinese interim visually distinct from final translation text', () => {
    useSessionStore.setState({
      ...useSessionStore.getState(),
      finalSegments: [
        {
          chinese_text_final: '我们需要在周五前对齐上线时间线。',
          end_ms: 3200,
          english_text_final: 'We need to align on the launch timeline before Friday.',
          segment_id: 'segment-1',
          sequence: 1,
          start_ms: 0,
          type: 'segment_final',
        },
      ],
      translationInterimText: '我们需要对齐上线时间线。',
    })

    render(<App />)

    const translationRegion = within(
      screen.getByRole('region', { name: '中文翻译区' }),
    )
    const interimText = translationRegion.getByText('我们需要对齐上线时间线。')
    const finalText = translationRegion.getByText(
      '我们需要在周五前对齐上线时间线。',
    )

    expect(interimText).toHaveClass('text-muted-foreground')
    expect(finalText).toHaveClass('text-zinc-950')
  })

  it('shows a retry entry when capture permission is denied', async () => {
    const user = userEvent.setup()
    mockDisplayMediaWithError(
      Object.assign(new Error('denied'), { name: 'NotAllowedError' }),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: '开始捕获' }))

    const statusBar = within(screen.getByRole('banner', { name: '会议状态栏' }))
    expect(statusBar.getByText('授权被拒绝')).toBeInTheDocument()
    expect(screen.getByText('浏览器拒绝了捕获授权。')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新授权' })).toBeEnabled()
  })

  it('prompts system audio fallback when no audio track is captured', async () => {
    const user = userEvent.setup()
    mockDisplayMediaWithStream(createStream(0))
    render(<App />)

    await user.click(screen.getByRole('button', { name: '开始捕获' }))

    const statusBar = within(screen.getByRole('banner', { name: '会议状态栏' }))
    expect(statusBar.getByText('未检测到音频轨道')).toBeInTheDocument()
    expect(
      screen.getByText('请切换系统音频模式后重新捕获。'),
    ).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('没有捕获到会议声音')
  })
})
