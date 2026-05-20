import { create } from 'zustand'

import {
  syncAnonymousClient,
  type AnonymousClientSyncResult,
} from '@/api/anonymous-clients'
import {
  getOrCreateAnonymousClientId,
  type AnonymousClientStorageError,
} from '@/lib/anonymous-client'
import {
  requestDisplayMediaCapture,
  stopMediaStream,
  type CaptureFailureCode,
  type DisplayMediaCaptureResult,
} from '@/lib/audio-capture'
import {
  AudioProcessingUnsupportedError,
  startAudioProcessing,
  type AudioLevelState,
  type AudioProcessingController,
  type StartAudioProcessingOptions,
} from '@/lib/audio-processing'
import {
  connectMeetingWebSocket,
  type ConnectMeetingWebSocketOptions,
  type MeetingWebSocketClient,
  type WebSocketStatus,
} from '@/lib/meeting-websocket'
import {
  noticeFromAudioPipelineError,
  noticeFromCaptureFailure,
  noticeFromCode,
  noticeFromSessionClosedReason,
  noticeFromWarningMessage,
  noticeFromWebSocketError,
  type SessionNotice,
} from '@/lib/session-notices'
import type { ProviderStatus, ServerMessage } from '@/protocol/websocket-messages'

export type { WebSocketStatus } from '@/lib/meeting-websocket'

export type CaptureMode = 'tab_audio' | 'system_audio'
export type SourcePlatform =
  | 'google_meet'
  | 'teams_web'
  | 'zoom_web'
  | 'tencent_meeting_web'
  | 'unknown'
export type SessionStatus = 'idle' | 'capturing'
export type AnonymousClientStatus = 'idle' | 'ready' | 'error'
export type ServerSyncStatus = 'idle' | 'syncing' | 'synced' | 'error'
export type CaptureStatus =
  | 'idle'
  | 'requesting'
  | 'ready'
  | 'denied'
  | 'no_audio'
  | 'unsupported'
  | 'failed'
export type AudioProcessingStatus =
  | 'idle'
  | 'starting'
  | 'running'
  | 'silent'
  | 'unsupported'
  | 'failed'
export type AudioPipelineErrorCode =
  | 'identity_not_ready'
  | 'websocket_failed'
  | 'audio_processing_unsupported'
  | 'audio_processing_failed'
  | 'audio_silent_timeout'
export type BrowserName = 'chrome' | 'edge' | 'other'
export type CaptureAuthorizationResult =
  | 'granted'
  | 'denied'
  | 'no_audio'
  | 'unsupported'
  | 'failed'
export type FinalSegment = Extract<ServerMessage, { type: 'segment_final' }>
export type AsrFinalSegment = Extract<ServerMessage, { type: 'asr_final' }>
export type TimelineItem = Extract<
  ServerMessage,
  { type: 'timeline_update' }
>['items'][number]

export type CaptureAttempt = {
  attemptedAt: string
  authorizationResult: CaptureAuthorizationResult
  browserName: BrowserName
  captureMode: CaptureMode
  failureCode: CaptureFailureCode | null
  sourcePlatform: SourcePlatform
}

type InitializeAnonymousClientOptions = {
  storage?: Pick<Storage, 'getItem' | 'setItem'>
  cryptoSource?: Pick<Crypto, 'randomUUID'>
  syncClient?: (clientId: string) => Promise<AnonymousClientSyncResult>
}

type CaptureService = (options: {
  mode: CaptureMode
}) => Promise<DisplayMediaCaptureResult>

type MeetingWebSocketConnector = (
  options: ConnectMeetingWebSocketOptions,
) => Promise<MeetingWebSocketClient>

type AudioProcessorStarter = (
  options: StartAudioProcessingOptions,
) => Promise<AudioProcessingController>

type BeginCaptureOptions = {
  captureService?: CaptureService
  connectMeetingWebSocket?: MeetingWebSocketConnector
  now?: () => Date
  startAudioProcessing?: AudioProcessorStarter
  userAgent?: string
}

type SessionState = {
  anonymousClientError: string | null
  anonymousClientStatus: AnonymousClientStatus
  archiveToken: string | null
  archiveUrl: string | null
  activeNotice: SessionNotice | null
  audioLevel: number
  audioPipelineErrorCode: AudioPipelineErrorCode | null
  audioProcessingStatus: AudioProcessingStatus
  audioProcessor: AudioProcessingController | null
  captureErrorCode: CaptureFailureCode | null
  captureErrorMessage: string | null
  captureMode: CaptureMode
  captureStatus: CaptureStatus
  clientId: string | null
  englishInterimText: string | null
  englishFinalSegments: AsrFinalSegment[]
  finalSegments: FinalSegment[]
  hasEffectiveAudio: boolean
  keySentenceText: string | null
  lastClosedReason: string | null
  lastCaptureAttempt: CaptureAttempt | null
  mediaStream: MediaStream | null
  meetingWebSocket: MeetingWebSocketClient | null
  providerStatus: ProviderStatus | null
  remainingSecondsToday: number
  serverSyncError: string | null
  serverSyncStatus: ServerSyncStatus
  sessionId: string | null
  silenceWarning: boolean
  sourcePlatform: SourcePlatform
  status: SessionStatus
  timelineItems: TimelineItem[]
  translationInterimText: string | null
  webSocketStatus: WebSocketStatus
  beginCapture: (mode: CaptureMode, options?: BeginCaptureOptions) => Promise<void>
  endSession: () => Promise<void>
  initializeAnonymousClient: (
    options?: InitializeAnonymousClientOptions,
  ) => Promise<void>
  setCaptureMode: (mode: CaptureMode) => void
  setSourcePlatform: (platform: SourcePlatform) => void
}

export const initialSessionState = {
  anonymousClientError: null,
  anonymousClientStatus: 'idle' as AnonymousClientStatus,
  archiveToken: null as string | null,
  archiveUrl: null as string | null,
  activeNotice: null as SessionNotice | null,
  audioLevel: 0,
  audioPipelineErrorCode: null as AudioPipelineErrorCode | null,
  audioProcessingStatus: 'idle' as AudioProcessingStatus,
  audioProcessor: null as AudioProcessingController | null,
  captureErrorCode: null as CaptureFailureCode | null,
  captureErrorMessage: null as string | null,
  captureMode: 'tab_audio' as CaptureMode,
  captureStatus: 'idle' as CaptureStatus,
  clientId: null,
  englishInterimText: null as string | null,
  englishFinalSegments: [] as AsrFinalSegment[],
  finalSegments: [] as FinalSegment[],
  hasEffectiveAudio: false,
  keySentenceText: null as string | null,
  lastClosedReason: null as string | null,
  lastCaptureAttempt: null as CaptureAttempt | null,
  mediaStream: null as MediaStream | null,
  meetingWebSocket: null as MeetingWebSocketClient | null,
  providerStatus: null as ProviderStatus | null,
  remainingSecondsToday: 40 * 60,
  serverSyncError: null,
  serverSyncStatus: 'idle' as ServerSyncStatus,
  sessionId: null as string | null,
  silenceWarning: false,
  sourcePlatform: 'unknown' as SourcePlatform,
  status: 'idle' as SessionStatus,
  timelineItems: [] as TimelineItem[],
  translationInterimText: null as string | null,
  webSocketStatus: 'idle' as WebSocketStatus,
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'unknown error'
}

function browserNameFromUserAgent(userAgent: string): BrowserName {
  if (/\bEdg\//.test(userAgent)) {
    return 'edge'
  }

  if (/\bChrome\//.test(userAgent) || /\bChromium\//.test(userAgent)) {
    return 'chrome'
  }

  return 'other'
}

function captureStatusFromErrorCode(errorCode: CaptureFailureCode): CaptureStatus {
  switch (errorCode) {
    case 'permission_denied':
      return 'denied'
    case 'no_audio_track':
      return 'no_audio'
    case 'not_supported':
      return 'unsupported'
    case 'capture_failed':
      return 'failed'
  }
}

function authorizationResultFromErrorCode(
  errorCode: CaptureFailureCode,
): CaptureAuthorizationResult {
  switch (errorCode) {
    case 'permission_denied':
      return 'denied'
    case 'no_audio_track':
      return 'no_audio'
    case 'not_supported':
      return 'unsupported'
    case 'capture_failed':
      return 'failed'
  }
}

async function stopAudioProcessor(
  audioProcessor: AudioProcessingController | null,
) {
  try {
    await audioProcessor?.stop()
  } catch {
    // Cleanup is best-effort because the user is already leaving the pipeline.
  }
}

function stopMeetingWebSocket(meetingWebSocket: MeetingWebSocketClient | null) {
  try {
    meetingWebSocket?.stop()
  } catch {
    // Cleanup is best-effort because the user is already leaving the pipeline.
  }
}

function isIdentityReady(state: SessionState): state is SessionState & {
  clientId: string
} {
  return (
    state.anonymousClientStatus === 'ready' &&
    state.serverSyncStatus === 'synced' &&
    state.clientId !== null
  )
}

export const useSessionStore = create<SessionState>((set, get) => ({
  ...initialSessionState,
  beginCapture: async (mode, options = {}) => {
    const currentState = get()

    if (!isIdentityReady(currentState)) {
      set({
        activeNotice: noticeFromAudioPipelineError('identity_not_ready', {
          captureMode: mode,
          sourcePlatform: currentState.sourcePlatform,
        }),
        audioPipelineErrorCode: 'identity_not_ready',
        captureErrorCode: null,
        captureErrorMessage: '匿名身份尚未同步，稍后再开始捕获。',
        captureStatus: 'idle',
        status: 'idle',
        webSocketStatus: 'error',
      })
      return
    }

    await stopAudioProcessor(currentState.audioProcessor)
    stopMeetingWebSocket(currentState.meetingWebSocket)
    stopMediaStream(currentState.mediaStream)

    set({
      activeNotice: null,
      archiveToken: null,
      archiveUrl: null,
      audioLevel: 0,
      audioPipelineErrorCode: null,
      audioProcessingStatus: 'idle',
      audioProcessor: null,
      captureErrorCode: null,
      captureErrorMessage: null,
      captureMode: mode,
      captureStatus: 'requesting',
      englishInterimText: null,
      englishFinalSegments: [],
      finalSegments: [],
      hasEffectiveAudio: false,
      keySentenceText: null,
      lastClosedReason: null,
      mediaStream: null,
      meetingWebSocket: null,
      providerStatus: null,
      sessionId: null,
      silenceWarning: false,
      status: 'idle',
      timelineItems: [],
      translationInterimText: null,
      webSocketStatus: 'idle',
    })

    const captureService: CaptureService =
      options.captureService ?? requestDisplayMediaCapture
    const userAgent =
      options.userAgent ??
      (typeof navigator === 'undefined' ? '' : navigator.userAgent)
    const attemptedAt = (options.now ?? (() => new Date()))().toISOString()
    const sourcePlatform = get().sourcePlatform

    let result: DisplayMediaCaptureResult
    try {
      result = await captureService({ mode })
    } catch {
      result = {
        errorCode: 'capture_failed',
        message: '捕获会议音频失败。',
        ok: false,
      }
    }

    const lastCaptureAttemptBase = {
      attemptedAt,
      browserName: browserNameFromUserAgent(userAgent),
      captureMode: mode,
      sourcePlatform,
    }

    if (!result.ok) {
      set({
        activeNotice: noticeFromCaptureFailure(result.errorCode, {
          captureMode: mode,
          sourcePlatform,
        }),
        captureErrorCode: result.errorCode,
        captureErrorMessage: result.message,
        captureStatus: captureStatusFromErrorCode(result.errorCode),
        lastCaptureAttempt: {
          ...lastCaptureAttemptBase,
          authorizationResult: authorizationResultFromErrorCode(result.errorCode),
          failureCode: result.errorCode,
        },
        mediaStream: null,
        status: 'idle',
      })
      return
    }

    set({
      activeNotice: null,
      captureErrorCode: null,
      captureErrorMessage: null,
      captureStatus: 'ready',
      lastCaptureAttempt: {
        ...lastCaptureAttemptBase,
        authorizationResult: 'granted',
        failureCode: null,
      },
      mediaStream: result.stream,
      status: 'capturing',
      webSocketStatus: 'connecting',
    })

    const connect = options.connectMeetingWebSocket ?? connectMeetingWebSocket
    let meetingWebSocket: MeetingWebSocketClient
    try {
      meetingWebSocket = await connect({
        captureMode: mode,
        clientId: currentState.clientId,
        onAudioStatus: (message) => {
          set({
            audioLevel: message.level ?? get().audioLevel,
            hasEffectiveAudio: message.has_audio,
          })
        },
        onAsrInterim: (message) => {
          set({
            englishInterimText: message.text,
          })
        },
        onAsrFinal: (message) => {
          set((state) => ({
            englishFinalSegments: [...state.englishFinalSegments, message],
          }))
        },
        onClosed: (message) => {
          set((state) => ({
            activeNotice:
              noticeFromSessionClosedReason(message.reason) ?? state.activeNotice,
            lastClosedReason: message.reason,
            webSocketStatus: 'closed',
          }))
        },
        onError: (error) => {
          const state = get()
          void stopAudioProcessor(state.audioProcessor)
          stopMediaStream(state.mediaStream)
          set({
            activeNotice: noticeFromWebSocketError(error),
            audioLevel: 0,
            audioPipelineErrorCode: 'websocket_failed',
            audioProcessingStatus: 'idle',
            audioProcessor: null,
            hasEffectiveAudio: false,
            mediaStream: null,
            status: 'idle',
            silenceWarning: false,
            webSocketStatus: 'error',
          })
        },
        onKeySentenceUpdate: (message) => {
          set({
            keySentenceText: message.text,
          })
        },
        onQuotaUpdate: (message) => {
          set({
            remainingSecondsToday: message.remaining_seconds_today,
          })
        },
        onSegmentFinal: (message) => {
          set((state) => ({
            englishFinalSegments: state.englishFinalSegments.filter(
              (segment) => segment.sequence !== message.sequence,
            ),
            finalSegments: state.finalSegments.some(
              (segment) =>
                segment.segment_id === message.segment_id ||
                segment.sequence === message.sequence,
            )
              ? state.finalSegments
              : [...state.finalSegments, message],
          }))
        },
        onSessionStarted: (message) => {
          set({
            archiveToken: message.archive_token,
            archiveUrl: message.archive_url,
            providerStatus: message.provider_status,
            remainingSecondsToday: message.remaining_seconds_today,
            sessionId: message.session_id,
          })
        },
        onStatusChange: (webSocketStatus) => {
          set((state) => ({
            activeNotice:
              webSocketStatus === 'connecting' &&
              state.webSocketStatus === 'started' &&
              state.sessionId !== null
                ? noticeFromCode('websocket_reconnecting', 'warning')
                : state.activeNotice,
            webSocketStatus,
          }))
        },
        onTimelineUpdate: (message) => {
          set({
            timelineItems: message.items,
          })
        },
        onTranslationInterim: (message) => {
          set({
            translationInterimText: message.text,
          })
        },
        onWarning: (message) => {
          set({
            activeNotice: noticeFromWarningMessage(message),
          })
        },
        sourcePlatform,
      })
    } catch (error) {
      stopMediaStream(result.stream)
      set({
        activeNotice: noticeFromWebSocketError(
          error instanceof Error ? error : new Error('WebSocket connection failed'),
        ),
        audioPipelineErrorCode: 'websocket_failed',
        captureErrorCode: 'capture_failed',
        captureErrorMessage: 'WebSocket 连接失败，请稍后重试。',
        captureStatus: 'failed',
        mediaStream: null,
        status: 'idle',
        webSocketStatus: 'error',
      })
      return
    }

    set({
      archiveToken: meetingWebSocket.archiveToken,
      archiveUrl: meetingWebSocket.archiveUrl,
      audioProcessingStatus: 'starting',
      meetingWebSocket,
      sessionId: meetingWebSocket.sessionId,
      webSocketStatus: 'started',
    })

    const startProcessor = options.startAudioProcessing ?? startAudioProcessing
    try {
      const audioProcessor = await startProcessor({
        onFrame: (frame: ArrayBuffer) => {
          meetingWebSocket.sendAudioFrame(frame)
        },
        onLevel: (levelState: AudioLevelState) => {
          set((state) => ({
            activeNotice: levelState.silenceWarning
              ? noticeFromAudioPipelineError('audio_silent_timeout', {
                  captureMode: state.captureMode,
                  sourcePlatform: state.sourcePlatform,
                })
              : state.activeNotice?.code === 'audio_silent_timeout'
                ? null
                : state.activeNotice,
            audioLevel: levelState.level,
            audioPipelineErrorCode: levelState.silenceWarning
              ? 'audio_silent_timeout'
              : state.audioPipelineErrorCode === 'audio_silent_timeout'
                ? null
                : state.audioPipelineErrorCode,
            audioProcessingStatus: levelState.silenceWarning
              ? 'silent'
              : 'running',
            hasEffectiveAudio: levelState.hasEffectiveAudio,
            silenceWarning: levelState.silenceWarning,
          }))
        },
        onSilenceWarning: () => {
          const state = get()
          set({
            activeNotice: noticeFromAudioPipelineError('audio_silent_timeout', {
              captureMode: state.captureMode,
              sourcePlatform: state.sourcePlatform,
            }),
            audioPipelineErrorCode: 'audio_silent_timeout',
            audioProcessingStatus: 'silent',
            hasEffectiveAudio: false,
            silenceWarning: true,
          })
        },
        stream: result.stream,
      })

      set((state) => ({
        audioProcessingStatus:
          state.audioProcessingStatus === 'silent' ? 'silent' : 'running',
        audioProcessor,
      }))
    } catch (error) {
      stopMeetingWebSocket(meetingWebSocket)
      stopMediaStream(result.stream)
      const isUnsupported = error instanceof AudioProcessingUnsupportedError
      const noticeCode = isUnsupported
        ? 'audio_processing_unsupported'
        : 'audio_processing_failed'
      set({
        activeNotice: noticeFromAudioPipelineError(noticeCode, {
          captureMode: mode,
          sourcePlatform,
        }),
        audioPipelineErrorCode: isUnsupported
          ? 'audio_processing_unsupported'
          : 'audio_processing_failed',
        audioProcessingStatus: isUnsupported ? 'unsupported' : 'failed',
        captureErrorCode: 'capture_failed',
        captureErrorMessage: isUnsupported
          ? '当前浏览器不支持 AudioWorklet 音频处理。'
          : '音频处理启动失败，请重新捕获。',
        captureStatus: 'failed',
        mediaStream: null,
        meetingWebSocket: null,
        sessionId: null,
        status: 'idle',
        webSocketStatus: 'closed',
      })
    }
  },
  endSession: async () => {
    const state = get()
    set({
      webSocketStatus: state.meetingWebSocket ? 'closing' : state.webSocketStatus,
    })
    await stopAudioProcessor(state.audioProcessor)
    stopMeetingWebSocket(state.meetingWebSocket)
    stopMediaStream(state.mediaStream)

    set({
      activeNotice: null,
      archiveUrl: null,
      archiveToken: null,
      audioLevel: 0,
      audioPipelineErrorCode: null,
      audioProcessingStatus: 'idle',
      audioProcessor: null,
      captureErrorCode: null,
      captureErrorMessage: null,
      captureStatus: 'idle',
      hasEffectiveAudio: false,
      lastClosedReason: null,
      mediaStream: null,
      meetingWebSocket: null,
      providerStatus: null,
      sessionId: null,
      silenceWarning: false,
      status: 'idle',
      webSocketStatus: 'closed',
    })
  },
  initializeAnonymousClient: async (options = {}) => {
    const currentState = get()
    if (
      currentState.anonymousClientStatus === 'ready' &&
      currentState.clientId !== null
    ) {
      return
    }

    let clientId: string
    try {
      clientId = getOrCreateAnonymousClientId({
        storage: options.storage,
        cryptoSource: options.cryptoSource,
      })
    } catch (error: unknown) {
      const storageError = error as AnonymousClientStorageError
      set({
        anonymousClientError: storageError.message,
        anonymousClientStatus: 'error',
        clientId: null,
        serverSyncError: null,
        serverSyncStatus: 'idle',
      })
      return
    }

    set({
      anonymousClientError: null,
      anonymousClientStatus: 'ready',
      clientId,
      serverSyncError: null,
      serverSyncStatus: 'syncing',
    })

    try {
      const syncResult = await (options.syncClient ?? syncAnonymousClient)(clientId)
      set({
        remainingSecondsToday: syncResult.remainingSecondsToday,
        serverSyncError: null,
        serverSyncStatus: 'synced',
      })
    } catch (error: unknown) {
      set({
        serverSyncError: errorMessage(error),
        serverSyncStatus: 'error',
      })
    }
  },
  setCaptureMode: (mode) =>
    set({
      captureMode: mode,
    }),
  setSourcePlatform: (platform) =>
    set({
      sourcePlatform: platform,
    }),
}))
