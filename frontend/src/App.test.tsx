import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { initialSessionState, useSessionStore } from './stores/session-store'

const originalMediaDevices = navigator.mediaDevices

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

describe('App', () => {
  beforeEach(() => {
    useSessionStore.setState(initialSessionState)
  })

  afterEach(() => {
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: originalMediaDevices,
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

  it('renders status bar controls and session metadata', () => {
    useSessionStore.setState({
      ...initialSessionState,
      anonymousClientStatus: 'ready',
      clientId: '11111111-1111-4111-8111-111111111111',
      remainingSecondsToday: 1500,
      serverSyncStatus: 'synced',
    })

    render(<App />)
    const statusBar = within(
      screen.getByRole('banner', { name: '会议状态栏' }),
    )

    expect(screen.getByRole('button', { name: '标签页音频' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: '系统音频' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
    expect(statusBar.getByText('音频状态')).toBeInTheDocument()
    expect(statusBar.getByText('ASR')).toBeInTheDocument()
    expect(statusBar.getByText('翻译')).toBeInTheDocument()
    expect(statusBar.getByText('会议平台')).toBeInTheDocument()
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
    const statusBar = within(
      screen.getByRole('banner', { name: '会议状态栏' }),
    )
    expect(statusBar.getAllByText('未连接').length).toBeGreaterThan(0)
  })

  it('captures display audio when starting capture', async () => {
    const user = userEvent.setup()
    mockDisplayMediaWithStream(createStream())
    render(<App />)

    await user.click(screen.getByRole('button', { name: '开始捕获' }))

    const statusBar = within(
      screen.getByRole('banner', { name: '会议状态栏' }),
    )
    expect(statusBar.getByText('已捕获音频')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '已捕获' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '结束会议' })).toBeEnabled()
  })

  it('shows a retry entry when capture permission is denied', async () => {
    const user = userEvent.setup()
    mockDisplayMediaWithError(
      Object.assign(new Error('denied'), { name: 'NotAllowedError' }),
    )
    render(<App />)

    await user.click(screen.getByRole('button', { name: '开始捕获' }))

    const statusBar = within(
      screen.getByRole('banner', { name: '会议状态栏' }),
    )
    expect(statusBar.getByText('授权被拒绝')).toBeInTheDocument()
    expect(screen.getByText('浏览器拒绝了捕获授权。')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新授权' })).toBeEnabled()
  })

  it('prompts system audio fallback when no audio track is captured', async () => {
    const user = userEvent.setup()
    mockDisplayMediaWithStream(createStream(0))
    render(<App />)

    await user.click(screen.getByRole('button', { name: '开始捕获' }))

    const statusBar = within(
      screen.getByRole('banner', { name: '会议状态栏' }),
    )
    expect(statusBar.getByText('未检测到音频轨道')).toBeInTheDocument()
    expect(screen.getByText('请切换系统音频模式后重新捕获。')).toBeInTheDocument()
  })
})
