import { describe, expect, it, vi } from 'vitest'

import { AUDIO_FORMAT } from './audio-frames'
import {
  connectMeetingWebSocket,
  resolveWebSocketUrl,
  type MeetingWebSocketConstructor,
} from './meeting-websocket'

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
        remaining_seconds_today: 2400,
        session_id: 'session-1',
        type: 'session_started',
      }),
    )

    const client = await connection
    expect(client.sessionId).toBe('session-1')
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
