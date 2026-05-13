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

function setReadyIdentity() {
  useSessionStore.setState({
    ...initialSessionState,
    anonymousClientStatus: 'ready',
    clientId: '11111111-1111-4111-8111-111111111111',
    serverSyncStatus: 'synced',
  })
}

function createStartedWebSocket() {
  return {
    archiveToken: 'archive-token',
    archiveUrl: '/archive/session-1?token=archive-token',
    sendAudioFrame: vi.fn(),
    sessionId: 'session-1',
    stop: vi.fn(),
  }
}

function createAudioProcessor() {
  return {
    stop: vi.fn(),
  }
}

describe('useSessionStore', () => {
  beforeEach(() => {
    useSessionStore.setState(initialSessionState)
  })

  it('starts capture, websocket session, and audio processing after browser authorization', async () => {
    setReadyIdentity()
    const { stream } = createStream()
    const meetingSocket = createStartedWebSocket()
    const audioProcessor = createAudioProcessor()
    const frame = new ArrayBuffer(3200)

    await useSessionStore.getState().beginCapture('system_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
      connectMeetingWebSocket: async (options) => {
        expect(options).toMatchObject({
          captureMode: 'system_audio',
          clientId: '11111111-1111-4111-8111-111111111111',
          sourcePlatform: 'unknown',
        })
        return meetingSocket
      },
      now: () => new Date('2026-05-07T09:00:00.000Z'),
      startAudioProcessing: async (options) => {
        expect(options.stream).toBe(stream)
        options.onLevel?.({
          hasEffectiveAudio: true,
          level: 0.42,
          silenceWarning: false,
        })
        options.onFrame(frame, { level: 0.42 })
        return audioProcessor
      },
      userAgent:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/136.0.0.0 Safari/537.36',
    })

    expect(meetingSocket.sendAudioFrame).toHaveBeenCalledWith(frame)
    expect(useSessionStore.getState()).toMatchObject({
      archiveToken: 'archive-token',
      archiveUrl: '/archive/session-1?token=archive-token',
      audioLevel: 0.42,
      audioPipelineErrorCode: null,
      audioProcessingStatus: 'running',
      captureMode: 'system_audio',
      captureStatus: 'ready',
      hasEffectiveAudio: true,
      mediaStream: stream,
      sessionId: 'session-1',
      status: 'capturing',
      webSocketStatus: 'started',
    })
    expect(useSessionStore.getState().lastCaptureAttempt).toMatchObject({
      authorizationResult: 'granted',
      browserName: 'chrome',
      captureMode: 'system_audio',
      failureCode: null,
      sourcePlatform: 'unknown',
    })
  })

  it('requires a synced anonymous identity before capture starts', async () => {
    const captureService = vi.fn()

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService,
    })

    expect(captureService).not.toHaveBeenCalled()
    expect(useSessionStore.getState()).toMatchObject({
      audioPipelineErrorCode: 'identity_not_ready',
      captureStatus: 'idle',
      status: 'idle',
      webSocketStatus: 'error',
    })
  })

  it('changes capture mode without starting capture', () => {
    useSessionStore.getState().setCaptureMode('system_audio')

    expect(useSessionStore.getState()).toMatchObject({
      captureMode: 'system_audio',
      status: 'idle',
    })
  })

  it('records permission denial and keeps the session idle', async () => {
    setReadyIdentity()
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

  it('handles websocket failure by stopping the captured media stream', async () => {
    setReadyIdentity()
    const { stream, track } = createStream()

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
      connectMeetingWebSocket: async () => {
        throw new Error('connect failed')
      },
    })

    expect(track.stop).toHaveBeenCalledOnce()
    expect(useSessionStore.getState()).toMatchObject({
      audioPipelineErrorCode: 'websocket_failed',
      captureStatus: 'failed',
      mediaStream: null,
      status: 'idle',
      webSocketStatus: 'error',
    })
  })

  it('records the 30 second silence warning without uploading silent frames', async () => {
    setReadyIdentity()
    const { stream } = createStream()
    const meetingSocket = createStartedWebSocket()

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
      connectMeetingWebSocket: async () => meetingSocket,
      startAudioProcessing: async (options) => {
        options.onLevel?.({
          hasEffectiveAudio: false,
          level: 0,
          silenceWarning: false,
        })
        options.onSilenceWarning?.()
        return createAudioProcessor()
      },
    })

    expect(meetingSocket.sendAudioFrame).not.toHaveBeenCalled()
    expect(useSessionStore.getState()).toMatchObject({
      audioLevel: 0,
      audioPipelineErrorCode: 'audio_silent_timeout',
      audioProcessingStatus: 'silent',
      hasEffectiveAudio: false,
      silenceWarning: true,
    })
  })

  it('stores realtime mock provider messages from the websocket callbacks', async () => {
    setReadyIdentity()
    const { stream } = createStream()
    const meetingSocket = createStartedWebSocket()

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
      connectMeetingWebSocket: async (options) => {
        options.onAsrInterim?.({
          text: 'We need to align on the launch timeline.',
          type: 'asr_interim',
        })
        options.onAsrFinal?.({
          confidence: 0.91,
          end_ms: 3200,
          sequence: 1,
          start_ms: 0,
          text: 'We need to align on the launch timeline before Friday.',
          type: 'asr_final',
        })
        options.onTranslationInterim?.({
          text: '我们需要对齐上线时间线。',
          type: 'translation_interim',
        })
        options.onSegmentFinal?.({
          chinese_text_final: '我们需要在周五前对齐上线时间线。',
          end_ms: 3200,
          english_text_final: 'We need to align on the launch timeline before Friday.',
          segment_id: 'segment-1',
          sequence: 1,
          start_ms: 0,
          type: 'segment_final',
        })
        options.onKeySentenceUpdate?.({
          text: '我们需要在周五前对齐上线时间线。',
          type: 'key_sentence_update',
        })
        options.onTimelineUpdate?.({
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
        })
        return meetingSocket
      },
      startAudioProcessing: async () => createAudioProcessor(),
    })

    expect(useSessionStore.getState()).toMatchObject({
      englishInterimText: 'We need to align on the launch timeline.',
      keySentenceText: '我们需要在周五前对齐上线时间线。',
      translationInterimText: '我们需要对齐上线时间线。',
    })
    expect(useSessionStore.getState().englishFinalSegments).toEqual([])
    expect(useSessionStore.getState().finalSegments).toHaveLength(1)
    expect(useSessionStore.getState().finalSegments[0]).toMatchObject({
      chinese_text_final: '我们需要在周五前对齐上线时间线。',
      english_text_final: 'We need to align on the launch timeline before Friday.',
      segment_id: 'segment-1',
    })
    expect(useSessionStore.getState().timelineItems).toEqual([
      expect.objectContaining({
        segment_id: 'segment-1',
        text: '我们需要在周五前对齐上线时间线。',
      }),
    ])
  })

  it('stops audio processing, websocket, and media tracks when ending the session', async () => {
    setReadyIdentity()
    const { stream, track } = createStream()
    const meetingSocket = createStartedWebSocket()
    const audioProcessor = createAudioProcessor()

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
      connectMeetingWebSocket: async () => meetingSocket,
      startAudioProcessing: async () => audioProcessor,
    })

    await useSessionStore.getState().endSession()

    expect(audioProcessor.stop).toHaveBeenCalledOnce()
    expect(meetingSocket.stop).toHaveBeenCalledOnce()
    expect(track.stop).toHaveBeenCalledOnce()
    expect(useSessionStore.getState()).toMatchObject({
      audioLevel: 0,
      audioProcessingStatus: 'idle',
      captureStatus: 'idle',
      hasEffectiveAudio: false,
      mediaStream: null,
      remainingSecondsToday: 2400,
      archiveToken: null,
      sessionId: null,
      status: 'idle',
      webSocketStatus: 'closed',
    })
  })
})
