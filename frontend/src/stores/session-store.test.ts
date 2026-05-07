import { beforeEach, describe, expect, it } from 'vitest'

import { initialSessionState, useSessionStore } from './session-store'

describe('useSessionStore', () => {
  beforeEach(() => {
    useSessionStore.setState(initialSessionState)
  })

  it('starts capture with the selected mode', () => {
    useSessionStore.getState().beginCapture('system_audio')

    expect(useSessionStore.getState()).toMatchObject({
      captureMode: 'system_audio',
      status: 'capturing',
    })
  })

  it('changes capture mode without starting capture', () => {
    useSessionStore.getState().setCaptureMode('system_audio')

    expect(useSessionStore.getState()).toMatchObject({
      captureMode: 'system_audio',
      status: 'idle',
    })
  })

  it('ends the active session without changing remaining quota', () => {
    useSessionStore.getState().beginCapture('tab_audio')
    useSessionStore.getState().endSession()

    expect(useSessionStore.getState()).toMatchObject({
      remainingSecondsToday: 2400,
      status: 'idle',
    })
  })
})
