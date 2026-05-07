import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import App from './App'
import { initialSessionState, useSessionStore } from './stores/session-store'

describe('App', () => {
  beforeEach(() => {
    useSessionStore.setState(initialSessionState)
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
    expect(statusBar.getByText('25 分钟')).toBeInTheDocument()
    expect(statusBar.getByText('11111111')).toBeInTheDocument()
    expect(statusBar.getByText('已同步')).toBeInTheDocument()
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

  it('updates capture status when starting capture', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '开始捕获' }))

    const statusBar = within(
      screen.getByRole('banner', { name: '会议状态栏' }),
    )
    expect(statusBar.getByText('捕获中')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '开始捕获' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '结束会议' })).toBeEnabled()
  })
})
