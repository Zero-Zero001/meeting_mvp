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
  archiveToken: string
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
  onAsrFinal?: (message: Extract<ServerMessage, { type: 'asr_final' }>) => void
  onAsrInterim?: (message: Extract<ServerMessage, { type: 'asr_interim' }>) => void
  onClosed?: (message: Extract<ServerMessage, { type: 'session_closed' }>) => void
  onError?: (error: Error) => void
  onKeySentenceUpdate?: (
    message: Extract<ServerMessage, { type: 'key_sentence_update' }>,
  ) => void
  onQuotaUpdate?: (message: Extract<ServerMessage, { type: 'quota_update' }>) => void
  onSegmentFinal?: (
    message: Extract<ServerMessage, { type: 'segment_final' }>,
  ) => void
  onSessionStarted?: (
    message: Extract<ServerMessage, { type: 'session_started' }>,
  ) => void
  onStatusChange?: (status: WebSocketStatus) => void
  onTimelineUpdate?: (
    message: Extract<ServerMessage, { type: 'timeline_update' }>,
  ) => void
  onTranslationInterim?: (
    message: Extract<ServerMessage, { type: 'translation_interim' }>,
  ) => void
  onWarning?: (message: Extract<ServerMessage, { type: 'warning' }>) => void
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
  onAsrFinal,
  onAsrInterim,
  onClosed,
  onError,
  onKeySentenceUpdate,
  onQuotaUpdate,
  onSegmentFinal,
  onSessionStarted,
  onStatusChange,
  onTimelineUpdate,
  onTranslationInterim,
  onWarning,
  sourcePlatform,
  url = resolveWebSocketUrl(),
}: ConnectMeetingWebSocketOptions): Promise<MeetingWebSocketClient> {
  onStatusChange?.('connecting')

  return new Promise((resolve, reject) => {
    let settled = false
    let stopping = false
    let currentArchiveToken: string | null = null
    let currentSessionId: string | null = null
    let currentArchiveUrl: string | null = null
    let socket: MeetingWebSocketLike

    function fail(error: Error) {
      stopping = true
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
        archiveToken: currentArchiveToken ?? '',
        archiveUrl: currentArchiveUrl ?? '',
        sendAudioFrame(frame) {
          if (socket.readyState === OPEN_READY_STATE) {
            socket.send(frame)
          }
        },
        sessionId: currentSessionId ?? '',
        stop() {
          stopping = true
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

    function attachSocketHandlers(mode: 'start' | 'resume') {
      socket.binaryType = 'arraybuffer'

      socket.onopen = () => {
        if (mode === 'resume' && currentSessionId && currentArchiveToken) {
          sendJson({
            archive_token: currentArchiveToken,
            audio_format: AUDIO_FORMAT,
            client_id: clientId,
            session_id: currentSessionId,
            type: 'session_resume',
          })
          return
        }

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
            currentArchiveToken = message.archive_token
            currentSessionId = message.session_id
            currentArchiveUrl = message.archive_url
            onSessionStarted?.(message)
            onStatusChange?.('started')
            if (!settled) {
              settled = true
              resolve(createClient())
            }
            break
          case 'session_resumed':
            currentSessionId = message.session_id
            currentArchiveUrl = message.archive_url
            onStatusChange?.('started')
            break
          case 'quota_update':
            onQuotaUpdate?.(message)
            break
          case 'audio_status':
            onAudioStatus?.(message)
            break
          case 'asr_interim':
            onAsrInterim?.(message)
            break
          case 'asr_final':
            onAsrFinal?.(message)
            break
          case 'translation_interim':
            onTranslationInterim?.(message)
            break
          case 'segment_final':
            onSegmentFinal?.(message)
            break
          case 'key_sentence_update':
            onKeySentenceUpdate?.(message)
            break
          case 'timeline_update':
            onTimelineUpdate?.(message)
            break
          case 'warning':
            onWarning?.(message)
            break
          case 'error':
            fail(websocketFailure(message.message ?? message.code))
            break
          case 'session_closed':
            stopping = true
            onClosed?.(message)
            onStatusChange?.('closed')
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
        if (!stopping && currentSessionId && currentArchiveToken) {
          openSocket('resume')
          return
        }
        onStatusChange?.('closed')
      }
    }

    function openSocket(mode: 'start' | 'resume') {
      onStatusChange?.('connecting')
      try {
        socket = new WebSocketCtor(url)
      } catch (error) {
        fail(error instanceof Error ? error : websocketFailure())
        return
      }
      attachSocketHandlers(mode)
    }

    openSocket('start')
  })
}
