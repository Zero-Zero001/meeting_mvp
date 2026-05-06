import { beforeEach, describe, expect, it, vi } from 'vitest'

import { initialSessionState, useSessionStore } from './session-store'

describe('anonymous client session state', () => {
  beforeEach(() => {
    localStorage.clear()
    useSessionStore.setState(initialSessionState)
  })

  it('initializes a local client id and syncs remaining quota from the backend', async () => {
    const syncClient = vi.fn().mockResolvedValue({
      clientId: '77777777-7777-4777-8777-777777777777',
      dailyFreeSeconds: 2400,
      remainingSecondsToday: 1800,
      isNew: true,
    })

    await useSessionStore.getState().initializeAnonymousClient({
      cryptoSource: {
        randomUUID: () => '77777777-7777-4777-8777-777777777777',
      } as Crypto,
      syncClient,
    })

    expect(useSessionStore.getState()).toMatchObject({
      anonymousClientStatus: 'ready',
      clientId: '77777777-7777-4777-8777-777777777777',
      remainingSecondsToday: 1800,
      serverSyncStatus: 'synced',
      serverSyncError: null,
    })
    expect(syncClient).toHaveBeenCalledWith(
      '77777777-7777-4777-8777-777777777777',
    )
  })

  it('keeps the local client id when backend sync fails', async () => {
    const syncClient = vi.fn().mockRejectedValue(new Error('backend unavailable'))

    await useSessionStore.getState().initializeAnonymousClient({
      cryptoSource: {
        randomUUID: () => '88888888-8888-4888-8888-888888888888',
      } as Crypto,
      syncClient,
    })

    expect(useSessionStore.getState()).toMatchObject({
      anonymousClientStatus: 'ready',
      clientId: '88888888-8888-4888-8888-888888888888',
      remainingSecondsToday: 2400,
      serverSyncStatus: 'error',
      serverSyncError: 'backend unavailable',
    })
  })

  it('marks anonymous client initialization as failed when storage is unavailable', async () => {
    const unavailableStorage = {
      getItem: () => {
        throw new Error('storage blocked')
      },
      setItem: () => {
        throw new Error('storage blocked')
      },
    }

    await useSessionStore.getState().initializeAnonymousClient({
      storage: unavailableStorage,
      cryptoSource: {
        randomUUID: () => '99999999-9999-4999-8999-999999999999',
      } as Crypto,
      syncClient: vi.fn(),
    })

    expect(useSessionStore.getState()).toMatchObject({
      anonymousClientStatus: 'error',
      clientId: null,
      serverSyncStatus: 'idle',
    })
  })
})
