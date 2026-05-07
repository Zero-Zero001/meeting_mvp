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
export type BrowserName = 'chrome' | 'edge' | 'other'
export type CaptureAuthorizationResult =
  | 'granted'
  | 'denied'
  | 'no_audio'
  | 'unsupported'
  | 'failed'

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

type BeginCaptureOptions = {
  captureService?: CaptureService
  now?: () => Date
  userAgent?: string
}

type SessionState = {
  anonymousClientError: string | null
  anonymousClientStatus: AnonymousClientStatus
  captureErrorCode: CaptureFailureCode | null
  captureErrorMessage: string | null
  captureMode: CaptureMode
  captureStatus: CaptureStatus
  clientId: string | null
  lastCaptureAttempt: CaptureAttempt | null
  mediaStream: MediaStream | null
  remainingSecondsToday: number
  serverSyncError: string | null
  serverSyncStatus: ServerSyncStatus
  sourcePlatform: SourcePlatform
  status: SessionStatus
  beginCapture: (mode: CaptureMode, options?: BeginCaptureOptions) => Promise<void>
  endSession: () => void
  initializeAnonymousClient: (
    options?: InitializeAnonymousClientOptions,
  ) => Promise<void>
  setCaptureMode: (mode: CaptureMode) => void
  setSourcePlatform: (platform: SourcePlatform) => void
}

export const initialSessionState = {
  anonymousClientError: null,
  anonymousClientStatus: 'idle' as AnonymousClientStatus,
  captureErrorCode: null as CaptureFailureCode | null,
  captureErrorMessage: null as string | null,
  captureMode: 'tab_audio' as CaptureMode,
  captureStatus: 'idle' as CaptureStatus,
  clientId: null,
  lastCaptureAttempt: null as CaptureAttempt | null,
  mediaStream: null as MediaStream | null,
  remainingSecondsToday: 40 * 60,
  serverSyncError: null,
  serverSyncStatus: 'idle' as ServerSyncStatus,
  sourcePlatform: 'unknown' as SourcePlatform,
  status: 'idle' as SessionStatus,
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

export const useSessionStore = create<SessionState>((set, get) => ({
  ...initialSessionState,
  beginCapture: async (mode, options = {}) => {
    stopMediaStream(get().mediaStream)

    set({
      captureErrorCode: null,
      captureErrorMessage: null,
      captureMode: mode,
      captureStatus: 'requesting',
      mediaStream: null,
      status: 'idle',
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

    if (result.ok) {
      set({
        captureErrorCode: null,
        captureErrorMessage: null,
        captureStatus: 'ready',
        lastCaptureAttempt: {
          attemptedAt,
          authorizationResult: 'granted',
          browserName: browserNameFromUserAgent(userAgent),
          captureMode: mode,
          failureCode: null,
          sourcePlatform,
        },
        mediaStream: result.stream,
        status: 'capturing',
      })
      return
    }

    set({
      captureErrorCode: result.errorCode,
      captureErrorMessage: result.message,
      captureStatus: captureStatusFromErrorCode(result.errorCode),
      lastCaptureAttempt: {
        attemptedAt,
        authorizationResult: authorizationResultFromErrorCode(result.errorCode),
        browserName: browserNameFromUserAgent(userAgent),
        captureMode: mode,
        failureCode: result.errorCode,
        sourcePlatform,
      },
      mediaStream: null,
      status: 'idle',
    })
  },
  endSession: () =>
    set((state) => {
      stopMediaStream(state.mediaStream)
      return {
        captureErrorCode: null,
        captureErrorMessage: null,
        captureStatus: 'idle',
        mediaStream: null,
        status: 'idle',
      }
    }),
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
