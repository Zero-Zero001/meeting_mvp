import { beforeEach, describe, expect, it, vi } from 'vitest'

import { initialSessionState, useSessionStore } from './session-store'

function createTrack() {
  return {
    stop: vi.fn(),
  } as unknown as MediaStreamTrack
}

function createStream() {
  const track = createTrack()
  const stream = {
    getAudioTracks: () => [track],
    getTracks: () => [track],
  } as unknown as MediaStream

  return { stream, track }
}

describe('useSessionStore', () => {
  beforeEach(() => {
    useSessionStore.setState(initialSessionState)
  })

  it('starts capture with the selected mode after browser authorization', async () => {
    const { stream } = createStream()

    await useSessionStore.getState().beginCapture('system_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
      now: () => new Date('2026-05-07T09:00:00.000Z'),
      userAgent:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/136.0.0.0 Safari/537.36',
    })

    expect(useSessionStore.getState()).toMatchObject({
      captureMode: 'system_audio',
      captureStatus: 'ready',
      mediaStream: stream,
      status: 'capturing',
    })
    expect(useSessionStore.getState().lastCaptureAttempt).toMatchObject({
      authorizationResult: 'granted',
      browserName: 'chrome',
      captureMode: 'system_audio',
      failureCode: null,
      sourcePlatform: 'unknown',
    })
  })

  it('changes capture mode without starting capture', () => {
    useSessionStore.getState().setCaptureMode('system_audio')

    expect(useSessionStore.getState()).toMatchObject({
      captureMode: 'system_audio',
      status: 'idle',
    })
  })

  it('ends the active session without changing remaining quota', async () => {
    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        ok: true,
        stream: createStream().stream,
      }),
    })
    useSessionStore.getState().endSession()

    expect(useSessionStore.getState()).toMatchObject({
      captureStatus: 'idle',
      mediaStream: null,
      remainingSecondsToday: 2400,
      status: 'idle',
    })
  })

  it('records permission denial and keeps the session idle', async () => {
    useSessionStore.getState().setSourcePlatform('tencent_meeting_web')

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        errorCode: 'permission_denied',
        message: '浏览器拒绝了捕获授权。',
        ok: false,
      }),
      now: () => new Date('2026-05-07T09:00:00.000Z'),
      userAgent:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/136.0.0.0',
    })

    expect(useSessionStore.getState()).toMatchObject({
      captureErrorCode: 'permission_denied',
      captureErrorMessage: '浏览器拒绝了捕获授权。',
      captureStatus: 'denied',
      mediaStream: null,
      sourcePlatform: 'tencent_meeting_web',
      status: 'idle',
    })
    expect(useSessionStore.getState().lastCaptureAttempt).toMatchObject({
      authorizationResult: 'denied',
      browserName: 'edge',
      failureCode: 'permission_denied',
      sourcePlatform: 'tencent_meeting_web',
    })
  })

  it('stops the captured media stream when ending the session', async () => {
    const { stream, track } = createStream()

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
    })

    useSessionStore.getState().endSession()

    expect(track.stop).toHaveBeenCalledOnce()
    expect(useSessionStore.getState()).toMatchObject({
      captureStatus: 'idle',
      mediaStream: null,
      status: 'idle',
    })
  })
})
