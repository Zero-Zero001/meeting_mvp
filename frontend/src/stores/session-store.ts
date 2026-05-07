import { create } from 'zustand'

import {
  syncAnonymousClient,
  type AnonymousClientSyncResult,
} from '@/api/anonymous-clients'
import {
  getOrCreateAnonymousClientId,
  type AnonymousClientStorageError,
} from '@/lib/anonymous-client'

export type CaptureMode = 'tab_audio' | 'system_audio'
export type SessionStatus = 'idle' | 'capturing'
export type AnonymousClientStatus = 'idle' | 'ready' | 'error'
export type ServerSyncStatus = 'idle' | 'syncing' | 'synced' | 'error'

type InitializeAnonymousClientOptions = {
  storage?: Pick<Storage, 'getItem' | 'setItem'>
  cryptoSource?: Pick<Crypto, 'randomUUID'>
  syncClient?: (clientId: string) => Promise<AnonymousClientSyncResult>
}

type SessionState = {
  anonymousClientError: string | null
  anonymousClientStatus: AnonymousClientStatus
  captureMode: CaptureMode
  clientId: string | null
  remainingSecondsToday: number
  serverSyncError: string | null
  serverSyncStatus: ServerSyncStatus
  status: SessionStatus
  beginCapture: (mode: CaptureMode) => void
  endSession: () => void
  initializeAnonymousClient: (
    options?: InitializeAnonymousClientOptions,
  ) => Promise<void>
  setCaptureMode: (mode: CaptureMode) => void
}

export const initialSessionState = {
  anonymousClientError: null,
  anonymousClientStatus: 'idle' as AnonymousClientStatus,
  captureMode: 'tab_audio' as CaptureMode,
  clientId: null,
  remainingSecondsToday: 40 * 60,
  serverSyncError: null,
  serverSyncStatus: 'idle' as ServerSyncStatus,
  status: 'idle' as SessionStatus,
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'unknown error'
}

export const useSessionStore = create<SessionState>((set, get) => ({
  ...initialSessionState,
  beginCapture: (mode) =>
    set({
      captureMode: mode,
      status: 'capturing',
    }),
  endSession: () =>
    set({
      status: 'idle',
    }),
  setCaptureMode: (mode) =>
    set({
      captureMode: mode,
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
}))
