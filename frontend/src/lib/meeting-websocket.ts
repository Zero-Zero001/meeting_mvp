import { publicConfig } from '@/config/public-config'
import { parseServerMessage, type ServerMessage } from '@/protocol/websocket-messages'
import type { CaptureMode, SourcePlatform } from '@/stores/session-store'

import { AUDIO_FORMAT } from './audio-frames'

export type WebSocketStatus =
  | 'idle'
  | 'connecting'
  | 'started'
  | 'closing'
  | 'closed'
  | 'error'

type MeetingWebSocketLike = {
  binaryType: BinaryType
  close: () => void
  onclose: ((event: CloseEvent) => void) | null
  onerror: ((event: Event) => void) | null
  onmessage: ((event: MessageEvent) => void) | null
  onopen: ((event: Event) => void) | null
  readyState: number
  send: (data: ArrayBuffer | string) => void
}

export type MeetingWebSocketConstructor = new (
  url: string,
) => MeetingWebSocketLike

export type MeetingWebSocketClient = {
  archiveUrl: string
  sendAudioFrame: (frame: ArrayBuffer) => void
  sessionId: string
  stop: () => void
}

export type ConnectMeetingWebSocketOptions = {
  WebSocketCtor?: MeetingWebSocketConstructor
  captureMode: CaptureMode
  clientId: string
  onAudioStatus?: (message: Extract<ServerMessage, { type: 'audio_status' }>) => void
  onClosed?: (message: Extract<ServerMessage, { type: 'session_closed' }>) => void
  onError?: (error: Error) => void
  onQuotaUpdate?: (message: Extract<ServerMessage, { type: 'quota_update' }>) => void
  onSessionStarted?: (
    message: Extract<ServerMessage, { type: 'session_started' }>,
  ) => void
  onStatusChange?: (status: WebSocketStatus) => void
  sourcePlatform: SourcePlatform
  url?: string
}

const OPEN_READY_STATE = 1
const CONNECTING_READY_STATE = 0

export function resolveWebSocketUrl(
  wsBaseUrl = publicConfig.wsBaseUrl,
  locationLike: Pick<Location, 'host' | 'protocol'> =
    typeof window === 'undefined'
      ? ({ host: '', protocol: 'http:' } as Pick<Location, 'host' | 'protocol'>)
      : window.location,
): string {
  const trimmedUrl = wsBaseUrl.trim()
  if (trimmedUrl !== '') {
    return trimmedUrl
  }

  const protocol = locationLike.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${locationLike.host}/ws`
}

function websocketFailure(message = 'WebSocket connection failed'): Error {
  return new Error(message)
}

export function connectMeetingWebSocket({
  WebSocketCtor = WebSocket as unknown as MeetingWebSocketConstructor,
  captureMode,
  clientId,
  onAudioStatus,
  onClosed,
  onError,
  onQuotaUpdate,
  onSessionStarted,
  onStatusChange,
  sourcePlatform,
  url = resolveWebSocketUrl(),
}: ConnectMeetingWebSocketOptions): Promise<MeetingWebSocketClient> {
  onStatusChange?.('connecting')

  return new Promise((resolve, reject) => {
    let settled = false
    let currentSessionId: string | null = null
    let currentArchiveUrl: string | null = null
    let socket: MeetingWebSocketLike

    function fail(error: Error) {
      onError?.(error)
      onStatusChange?.('error')
      if (!settled) {
        settled = true
        reject(error)
      }
    }

    function sendJson(payload: unknown) {
      socket.send(JSON.stringify(payload))
    }

    function createClient(): MeetingWebSocketClient {
      return {
        archiveUrl: currentArchiveUrl ?? '',
        sendAudioFrame(frame) {
          if (socket.readyState === OPEN_READY_STATE) {
            socket.send(frame)
          }
        },
        sessionId: currentSessionId ?? '',
        stop() {
          if (socket.readyState === OPEN_READY_STATE && currentSessionId) {
            onStatusChange?.('closing')
            sendJson({
              session_id: currentSessionId,
              type: 'session_stop',
            })
          }

          if (
            socket.readyState === OPEN_READY_STATE ||
            socket.readyState === CONNECTING_READY_STATE
          ) {
            socket.close()
          }
        },
      }
    }

    try {
      socket = new WebSocketCtor(url)
    } catch (error) {
      fail(error instanceof Error ? error : websocketFailure())
      return
    }

    socket.binaryType = 'arraybuffer'

    socket.onopen = () => {
      sendJson({
        audio_format: AUDIO_FORMAT,
        capture_mode: captureMode,
        client_id: clientId,
        source_platform: sourcePlatform,
        type: 'session_start',
      })
    }

    socket.onmessage = (event) => {
      let message: ServerMessage
      try {
        message = parseServerMessage(JSON.parse(String(event.data)))
      } catch {
        fail(websocketFailure('Invalid WebSocket message'))
        return
      }

      switch (message.type) {
        case 'session_started':
          currentSessionId = message.session_id
          currentArchiveUrl = message.archive_url
          onSessionStarted?.(message)
          onStatusChange?.('started')
          if (!settled) {
            settled = true
            resolve(createClient())
          }
          break
        case 'quota_update':
          onQuotaUpdate?.(message)
          break
        case 'audio_status':
          onAudioStatus?.(message)
          break
        case 'error':
          fail(websocketFailure(message.message ?? message.code))
          break
        case 'session_closed':
          onClosed?.(message)
          onStatusChange?.('closed')
          break
        case 'asr_interim':
        case 'translation_interim':
        case 'segment_final':
        case 'key_sentence_update':
        case 'timeline_update':
        case 'warning':
          break
      }
    }

    socket.onerror = () => {
      fail(websocketFailure())
    }

    socket.onclose = () => {
      if (!settled) {
        fail(websocketFailure())
        return
      }
      onStatusChange?.('closed')
    }
  })
}
