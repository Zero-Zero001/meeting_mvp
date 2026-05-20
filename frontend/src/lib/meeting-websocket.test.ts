import { describe, expect, it, vi } from 'vitest'

import { AUDIO_FORMAT } from './audio-frames'
import {
  connectMeetingWebSocket,
  MeetingWebSocketError,
  resolveWebSocketUrl,
  type MeetingWebSocketConstructor,
} from './meeting-websocket'

const providerStatus = {
  qwen_final_translation: 'enabled',
  qwen_interim_translation: 'enabled',
  qwen_realtime_asr: 'enabled',
} as const

class FakeWebSocket {
  static instances: FakeWebSocket[] = []

  binaryType: BinaryType = 'blob'
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onopen: ((event: Event) => void) | null = null
  readyState = 0
  sent: unknown[] = []
  url: string

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  send(data: unknown) {
    this.sent.push(data)
  }

  close() {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close'))
  }

  open() {
    this.readyState = 1
    this.onopen?.(new Event('open'))
  }

  message(payload: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: payload }))
  }

  failBeforeStart() {
    this.readyState = 3
    this.onerror?.(new Event('error'))
    this.onclose?.(new CloseEvent('close'))
  }
}

const WebSocketCtor = FakeWebSocket as unknown as MeetingWebSocketConstructor

describe('meeting websocket client', () => {
  it('derives the websocket URL from the current page when no env URL is set', () => {
    expect(
      resolveWebSocketUrl('', {
        host: 'meeting.example.test',
        protocol: 'https:',
      } as Location),
    ).toBe('wss://meeting.example.test/ws')
    expect(
      resolveWebSocketUrl('', {
        host: 'localhost:5173',
        protocol: 'http:',
      } as Location),
    ).toBe('ws://localhost:5173/ws')
    expect(resolveWebSocketUrl('wss://api.example.test/ws')).toBe(
      'wss://api.example.test/ws',
    )
  })

  it('sends session_start and resolves after session_started', async () => {
    FakeWebSocket.instances = []
    const onStatusChange = vi.fn()
    const connection = connectMeetingWebSocket({
      WebSocketCtor,
      captureMode: 'tab_audio',
      clientId: '11111111-1111-4111-8111-111111111111',
      onStatusChange,
      sourcePlatform: 'google_meet',
      url: 'ws://localhost/ws',
    })
    const socket = FakeWebSocket.instances[0]

    socket.open()
    expect(JSON.parse(socket.sent[0] as string)).toEqual({
      audio_format: AUDIO_FORMAT,
      capture_mode: 'tab_audio',
      client_id: '11111111-1111-4111-8111-111111111111',
      source_platform: 'google_meet',
      type: 'session_start',
    })

    socket.message(
      JSON.stringify({
        archive_token: 'archive-token',
        archive_url: '/archive/session-1?token=archive-token',
        provider_status: providerStatus,
        remaining_seconds_today: 2400,
        session_id: 'session-1',
        type: 'session_started',
      }),
    )

    const client = await connection
    expect(client.sessionId).toBe('session-1')
    expect(client.archiveToken).toBe('archive-token')
    expect(client.archiveUrl).toBe('/archive/session-1?token=archive-token')
    expect(onStatusChange).toHaveBeenCalledWith('started')
  })

  it('sends binary audio frames after the session starts', async () => {
    FakeWebSocket.instances = []
    const connection = connectMeetingWebSocket({
      WebSocketCtor,
      captureMode: 'tab_audio',
      clientId: '11111111-1111-4111-8111-111111111111',
      sourcePlatform: 'unknown',
      url: 'ws://localhost/ws',
    })
    const socket = FakeWebSocket.instances[0]
    socket.open()
    socket.message(
      JSON.stringify({
        archive_token: 'archive-token',
        archive_url: '/archive/session-1?token=archive-token',
        provider_status: providerStatus,
        remaining_seconds_today: 2400,
        session_id: 'session-1',
        type: 'session_started',
      }),
    )
    const client = await connection
    const frame = new ArrayBuffer(3200)

    client.sendAudioFrame(frame)

    expect(socket.sent.at(-1)).toBe(frame)
  })

  it('resumes the same backend session after an unexpected browser websocket close', async () => {
    FakeWebSocket.instances = []
    const onStatusChange = vi.fn()
    const connection = connectMeetingWebSocket({
      WebSocketCtor,
      captureMode: 'tab_audio',
      clientId: '11111111-1111-4111-8111-111111111111',
      onStatusChange,
      sourcePlatform: 'unknown',
      url: 'ws://localhost/ws',
    })
    const firstSocket = FakeWebSocket.instances[0]
    firstSocket.open()
    firstSocket.message(
      JSON.stringify({
        archive_token: 'archive-token',
        archive_url: '/archive/session-1?token=archive-token',
        provider_status: providerStatus,
        remaining_seconds_today: 2400,
        session_id: 'session-1',
        type: 'session_started',
      }),
    )
    const client = await connection

    firstSocket.close()
    const resumedSocket = FakeWebSocket.instances[1]
    resumedSocket.open()

    expect(JSON.parse(resumedSocket.sent[0] as string)).toEqual({
      archive_token: 'archive-token',
      audio_format: AUDIO_FORMAT,
      client_id: '11111111-1111-4111-8111-111111111111',
      session_id: 'session-1',
      type: 'session_resume',
    })

    resumedSocket.message(
      JSON.stringify({
        archive_url: '/archive/session-1?token=archive-token',
        remaining_seconds_today: 2390,
        session_id: 'session-1',
        type: 'session_resumed',
      }),
    )
    const frame = new ArrayBuffer(3200)
    client.sendAudioFrame(frame)

    expect(resumedSocket.sent.at(-1)).toBe(frame)
    expect(onStatusChange).toHaveBeenCalledWith('connecting')
    expect(onStatusChange).toHaveBeenCalledWith('started')
  })

  it('forwards realtime transcript, translation, timeline, and warning messages', async () => {
    FakeWebSocket.instances = []
    const onAsrInterim = vi.fn()
    const onAsrFinal = vi.fn()
    const onKeySentenceUpdate = vi.fn()
    const onSegmentFinal = vi.fn()
    const onTimelineUpdate = vi.fn()
    const onTranslationInterim = vi.fn()
    const onWarning = vi.fn()
    const connection = connectMeetingWebSocket({
      WebSocketCtor,
      captureMode: 'tab_audio',
      clientId: '11111111-1111-4111-8111-111111111111',
      onAsrInterim,
      onAsrFinal,
      onKeySentenceUpdate,
      onSegmentFinal,
      onTimelineUpdate,
      onTranslationInterim,
      onWarning,
      sourcePlatform: 'unknown',
      url: 'ws://localhost/ws',
    })
    const socket = FakeWebSocket.instances[0]
    socket.open()
    socket.message(
      JSON.stringify({
        archive_token: 'archive-token',
        archive_url: '/archive/session-1?token=archive-token',
        provider_status: providerStatus,
        remaining_seconds_today: 2400,
        session_id: 'session-1',
        type: 'session_started',
      }),
    )
    await connection

    socket.message(
      JSON.stringify({
        text: 'We need to align on the launch timeline.',
        type: 'asr_interim',
      }),
    )
    socket.message(
      JSON.stringify({
        confidence: 0.91,
        end_ms: 3200,
        sequence: 1,
        start_ms: 0,
        text: 'We need to align on the launch timeline before Friday.',
        type: 'asr_final',
      }),
    )
    socket.message(
      JSON.stringify({
        code: 'mock_qwen_interim_retry',
        message: 'Mock interim provider recovered after a simulated retry.',
        type: 'warning',
      }),
    )
    socket.message(
      JSON.stringify({
        text: '我们需要对齐上线时间线。',
        type: 'translation_interim',
      }),
    )
    socket.message(
      JSON.stringify({
        chinese_text_final: '我们需要在周五前对齐上线时间线。',
        end_ms: 3200,
        english_text_final: 'We need to align on the launch timeline before Friday.',
        segment_id: 'segment-1',
        sequence: 1,
        start_ms: 0,
        type: 'segment_final',
      }),
    )
    socket.message(
      JSON.stringify({
        text: '我们需要在周五前对齐上线时间线。',
        type: 'key_sentence_update',
      }),
    )
    socket.message(
      JSON.stringify({
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
    )

    expect(onAsrInterim).toHaveBeenCalledWith({
      text: 'We need to align on the launch timeline.',
      type: 'asr_interim',
    })
    expect(onAsrFinal).toHaveBeenCalledWith({
      confidence: 0.91,
      end_ms: 3200,
      sequence: 1,
      start_ms: 0,
      text: 'We need to align on the launch timeline before Friday.',
      type: 'asr_final',
    })
    expect(onWarning).toHaveBeenCalledWith({
      code: 'mock_qwen_interim_retry',
      message: 'Mock interim provider recovered after a simulated retry.',
      type: 'warning',
    })
    expect(onTranslationInterim).toHaveBeenCalledWith({
      text: '我们需要对齐上线时间线。',
      type: 'translation_interim',
    })
    expect(onSegmentFinal).toHaveBeenCalledWith(
      expect.objectContaining({
        chinese_text_final: '我们需要在周五前对齐上线时间线。',
        english_text_final: 'We need to align on the launch timeline before Friday.',
        segment_id: 'segment-1',
      }),
    )
    expect(onKeySentenceUpdate).toHaveBeenCalledWith({
      text: '我们需要在周五前对齐上线时间线。',
      type: 'key_sentence_update',
    })
    expect(onTimelineUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        items: [
          expect.objectContaining({
            segment_id: 'segment-1',
            text: '我们需要在周五前对齐上线时间线。',
          }),
        ],
      }),
    )
  })

  it('isolates realtime callback failures while dispatching later workspace messages', async () => {
    FakeWebSocket.instances = []
    const onAsrInterim = vi.fn(() => {
      throw new Error('render failed')
    })
    const onError = vi.fn()
    const onKeySentenceUpdate = vi.fn()
    const onSegmentFinal = vi.fn()
    const onTimelineUpdate = vi.fn()
    const onTranslationInterim = vi.fn()
    const connection = connectMeetingWebSocket({
      WebSocketCtor,
      captureMode: 'tab_audio',
      clientId: '11111111-1111-4111-8111-111111111111',
      onAsrInterim,
      onError,
      onKeySentenceUpdate,
      onSegmentFinal,
      onTimelineUpdate,
      onTranslationInterim,
      sourcePlatform: 'unknown',
      url: 'ws://localhost/ws',
    })
    const socket = FakeWebSocket.instances[0]
    socket.open()
    socket.message(
      JSON.stringify({
        archive_token: 'archive-token',
        archive_url: '/archive/session-1?token=archive-token',
        provider_status: providerStatus,
        remaining_seconds_today: 2400,
        session_id: 'session-1',
        type: 'session_started',
      }),
    )
    await connection

    expect(() =>
      socket.message(
        JSON.stringify({
          text: 'This callback fails.',
          type: 'asr_interim',
        }),
      ),
    ).not.toThrow()
    socket.message(
      JSON.stringify({
        text: '后续中文临时理解仍然分发。',
        type: 'translation_interim',
      }),
    )
    socket.message(
      JSON.stringify({
        chinese_text_final: '正式中文仍然分发。',
        end_ms: 3200,
        english_text_final: 'The final message still dispatches.',
        segment_id: 'segment-1',
        sequence: 1,
        start_ms: 0,
        type: 'segment_final',
      }),
    )
    socket.message(
      JSON.stringify({
        text: '重点句仍然分发。',
        type: 'key_sentence_update',
      }),
    )
    socket.message(
      JSON.stringify({
        items: [
          {
            id: 'timeline-1',
            item_type: 'segment_final',
            segment_id: 'segment-1',
            text: '时间线仍然分发。',
            timestamp_ms: 3200,
          },
        ],
        type: 'timeline_update',
      }),
    )

    expect(onError).not.toHaveBeenCalled()
    expect(onTranslationInterim).toHaveBeenCalledWith({
      text: '后续中文临时理解仍然分发。',
      type: 'translation_interim',
    })
    expect(onSegmentFinal).toHaveBeenCalledWith(
      expect.objectContaining({
        chinese_text_final: '正式中文仍然分发。',
      }),
    )
    expect(onKeySentenceUpdate).toHaveBeenCalledWith({
      text: '重点句仍然分发。',
      type: 'key_sentence_update',
    })
    expect(onTimelineUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        items: [
          expect.objectContaining({
            text: '时间线仍然分发。',
          }),
        ],
      }),
    )
  })

  it('sends session_stop and closes on stop', async () => {
    FakeWebSocket.instances = []
    const connection = connectMeetingWebSocket({
      WebSocketCtor,
      captureMode: 'system_audio',
      clientId: '11111111-1111-4111-8111-111111111111',
      sourcePlatform: 'unknown',
      url: 'ws://localhost/ws',
    })
    const socket = FakeWebSocket.instances[0]
    socket.open()
    socket.message(
      JSON.stringify({
        archive_token: 'archive-token',
        archive_url: '/archive/session-1?token=archive-token',
        provider_status: providerStatus,
        remaining_seconds_today: 2400,
        session_id: 'session-1',
        type: 'session_started',
      }),
    )
    const client = await connection

    client.stop()

    expect(JSON.parse(socket.sent.at(-1) as string)).toEqual({
      session_id: 'session-1',
      type: 'session_stop',
    })
    expect(socket.readyState).toBe(3)
  })

  it('preserves server error codes for user-facing notices', async () => {
    FakeWebSocket.instances = []
    const onError = vi.fn()
    const connection = connectMeetingWebSocket({
      WebSocketCtor,
      captureMode: 'tab_audio',
      clientId: '11111111-1111-4111-8111-111111111111',
      onError,
      sourcePlatform: 'unknown',
      url: 'ws://localhost/ws',
    })
    const socket = FakeWebSocket.instances[0]
    socket.open()
    socket.message(
      JSON.stringify({
        archive_token: 'archive-token',
        archive_url: '/archive/session-1?token=archive-token',
        provider_status: providerStatus,
        remaining_seconds_today: 2400,
        session_id: 'session-1',
        type: 'session_started',
      }),
    )
    await connection

    socket.message(
      JSON.stringify({
        code: 'budget_fuse_triggered',
        message: 'Budget fuse triggered',
        type: 'error',
      }),
    )

    expect(onError).toHaveBeenCalledOnce()
    const error = onError.mock.calls[0][0] as MeetingWebSocketError
    expect(error).toBeInstanceOf(MeetingWebSocketError)
    expect(error.code).toBe('budget_fuse_triggered')
    expect(error.serverMessage).toMatchObject({
      code: 'budget_fuse_triggered',
      type: 'error',
    })
  })

  it('rejects when the websocket closes before session_started', async () => {
    FakeWebSocket.instances = []
    const connection = connectMeetingWebSocket({
      WebSocketCtor,
      captureMode: 'tab_audio',
      clientId: '11111111-1111-4111-8111-111111111111',
      sourcePlatform: 'unknown',
      url: 'ws://localhost/ws',
    })
    const socket = FakeWebSocket.instances[0]

    socket.failBeforeStart()

    await expect(connection).rejects.toThrow('WebSocket connection failed')
  })
})
