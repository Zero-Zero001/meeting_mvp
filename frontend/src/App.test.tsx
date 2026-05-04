import { render, screen } from '@testing-library/react'
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
    expect(screen.getByText('英文原文区')).toBeInTheDocument()
    expect(screen.getByText('中文翻译区')).toBeInTheDocument()
    expect(screen.getByText('当前重点句区')).toBeInTheDocument()
    expect(screen.getByText('会议时间线区')).toBeInTheDocument()
  })

  it('updates capture status when starting capture', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '开始捕获' }))

    expect(screen.getByText('捕获中')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '开始捕获' })).toBeDisabled()
  })
})
