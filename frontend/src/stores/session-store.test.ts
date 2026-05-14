import { beforeEach, describe, expect, it, vi } from 'vitest'

import { MeetingWebSocketError, type ConnectMeetingWebSocketOptions } from '@/lib/meeting-websocket'

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
    expect(useSessionStore.getState().activeNotice).toMatchObject({
      code: 'permission_denied',
      severity: 'warning',
      title: '无法开始捕获音频',
    })
  })

  it('guides Tencent Meeting no-audio tab capture to system audio fallback', async () => {
    setReadyIdentity()
    useSessionStore.getState().setSourcePlatform('tencent_meeting_web')

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        errorCode: 'no_audio_track',
        message: '未捕获到音频轨道。',
        ok: false,
      }),
    })

    expect(useSessionStore.getState()).toMatchObject({
      captureErrorCode: 'no_audio_track',
      captureStatus: 'no_audio',
    })
    expect(useSessionStore.getState().activeNotice).toMatchObject({
      code: 'no_audio_track',
      title: '没有捕获到会议声音',
    })
    expect(useSessionStore.getState().activeNotice?.action).toContain(
      '切换到系统音频模式后重新捕获',
    )
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
    expect(useSessionStore.getState().activeNotice).toMatchObject({
      code: 'websocket_failed',
      severity: 'error',
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
    expect(useSessionStore.getState().activeNotice).toMatchObject({
      code: 'audio_silent_timeout',
      title: '暂未检测到会议声音',
    })
  })

  it('records recoverable provider warnings without clearing realtime content', async () => {
    setReadyIdentity()
    const { stream } = createStream()
    const meetingSocket = createStartedWebSocket()
    let websocketOptions: ConnectMeetingWebSocketOptions | null = null

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
      connectMeetingWebSocket: async (options) => {
        websocketOptions = options
        return meetingSocket
      },
      startAudioProcessing: async () => createAudioProcessor(),
    })

    websocketOptions?.onSegmentFinal?.({
      chinese_text_final: '我们需要在周五前对齐上线时间线。',
      end_ms: 3200,
      english_text_final: 'We need to align on the launch timeline before Friday.',
      segment_id: 'segment-1',
      sequence: 1,
      start_ms: 0,
      type: 'segment_final',
    })
    websocketOptions?.onWarning?.({
      code: 'qwen_final_translation_failed',
      message: '中文正式翻译失败，英文 final 已归档待重试。',
      type: 'warning',
    })

    expect(useSessionStore.getState().finalSegments).toHaveLength(1)
    expect(useSessionStore.getState().archiveUrl).toBe(
      '/archive/session-1?token=archive-token',
    )
    expect(useSessionStore.getState().activeNotice).toMatchObject({
      code: 'qwen_final_translation_failed',
      severity: 'warning',
      title: '正式中文翻译失败',
    })
  })

  it('records blocking websocket errors and preserves archived content references', async () => {
    setReadyIdentity()
    const { stream, track } = createStream()
    const meetingSocket = createStartedWebSocket()
    const audioProcessor = createAudioProcessor()
    let websocketOptions: ConnectMeetingWebSocketOptions | null = null

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
      connectMeetingWebSocket: async (options) => {
        websocketOptions = options
        return meetingSocket
      },
      startAudioProcessing: async () => audioProcessor,
    })

    websocketOptions?.onSegmentFinal?.({
      chinese_text_final: '预算审查调整到周五。',
      end_ms: 2400,
      english_text_final: 'The budget review moved to Friday.',
      segment_id: 'segment-1',
      sequence: 1,
      start_ms: 0,
      type: 'segment_final',
    })
    websocketOptions?.onError?.(
      new MeetingWebSocketError({
        code: 'qwen_asr_error',
        message: 'Qwen ASR unavailable',
      }),
    )
    await Promise.resolve()

    expect(audioProcessor.stop).toHaveBeenCalledOnce()
    expect(track.stop).toHaveBeenCalledOnce()
    expect(useSessionStore.getState().finalSegments).toHaveLength(1)
    expect(useSessionStore.getState()).toMatchObject({
      archiveUrl: '/archive/session-1?token=archive-token',
      sessionId: 'session-1',
      status: 'idle',
      webSocketStatus: 'error',
    })
    expect(useSessionStore.getState().activeNotice).toMatchObject({
      code: 'qwen_asr_error',
      severity: 'error',
      title: '英文转写服务暂时不可用',
    })
  })

  it('shows reconnecting and resume-failed notices from websocket close reasons', async () => {
    setReadyIdentity()
    const { stream } = createStream()
    const meetingSocket = createStartedWebSocket()
    let websocketOptions: ConnectMeetingWebSocketOptions | null = null

    await useSessionStore.getState().beginCapture('tab_audio', {
      captureService: async () => ({
        ok: true,
        stream,
      }),
      connectMeetingWebSocket: async (options) => {
        websocketOptions = options
        return meetingSocket
      },
      startAudioProcessing: async () => createAudioProcessor(),
    })

    websocketOptions?.onStatusChange?.('connecting')
    expect(useSessionStore.getState().activeNotice).toMatchObject({
      code: 'websocket_reconnecting',
      severity: 'warning',
    })

    websocketOptions?.onClosed?.({
      reason: 'session_resume_failed',
      type: 'session_closed',
    })
    expect(useSessionStore.getState().lastClosedReason).toBe(
      'session_resume_failed',
    )
    expect(useSessionStore.getState().activeNotice).toMatchObject({
      code: 'session_resume_failed',
      severity: 'error',
      title: '断线恢复失败',
    })
  })

  it('keeps realtime workspace state independent and deduplicates confirmed final segments', async () => {
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
          text: 'We need to align.',
          type: 'asr_interim',
        })
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
        options.onAsrFinal?.({
          confidence: 0.88,
          end_ms: 6400,
          sequence: 2,
          start_ms: 3200,
          text: 'Finance will confirm the budget tomorrow.',
          type: 'asr_final',
        })
        options.onTranslationInterim?.({
          text: '我们需要对齐。',
          type: 'translation_interim',
        })
        options.onTranslationInterim?.({
          text: '我们需要对齐上线时间线。',
          type: 'translation_interim',
        })
        const confirmedSegment = {
          chinese_text_final: '我们需要在周五前对齐上线时间线。',
          end_ms: 3200,
          english_text_final: 'We need to align on the launch timeline before Friday.',
          segment_id: 'segment-1',
          sequence: 1,
          start_ms: 0,
          type: 'segment_final',
        } as const
        options.onSegmentFinal?.(confirmedSegment)
        options.onSegmentFinal?.(confirmedSegment)
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
        options.onTimelineUpdate?.({
          items: [
            {
              id: 'timeline-2',
              item_type: 'segment_final',
              segment_id: 'segment-2',
              text: '财务明天确认预算。',
              timestamp_ms: 6400,
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
    expect(useSessionStore.getState().englishFinalSegments).toEqual([
      expect.objectContaining({
        sequence: 2,
        text: 'Finance will confirm the budget tomorrow.',
      }),
    ])
    expect(useSessionStore.getState().finalSegments).toHaveLength(1)
    expect(useSessionStore.getState().finalSegments[0]).toMatchObject({
      chinese_text_final: '我们需要在周五前对齐上线时间线。',
      english_text_final: 'We need to align on the launch timeline before Friday.',
      segment_id: 'segment-1',
    })
    expect(useSessionStore.getState().timelineItems).toEqual([
      expect.objectContaining({
        segment_id: 'segment-2',
        text: '财务明天确认预算。',
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
