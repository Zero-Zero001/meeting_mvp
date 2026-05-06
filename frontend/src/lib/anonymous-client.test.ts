import { beforeEach, describe, expect, it } from 'vitest'

import {
  ANONYMOUS_CLIENT_ID_STORAGE_KEY,
  AnonymousClientStorageError,
  getOrCreateAnonymousClientId,
} from './anonymous-client'

function createCryptoWithId(id: string): Crypto {
  return {
    randomUUID: () => id,
  } as Crypto
}

describe('anonymous client identity', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('creates and stores a new client id on first access', () => {
    const clientId = getOrCreateAnonymousClientId({
      cryptoSource: createCryptoWithId('11111111-1111-4111-8111-111111111111'),
    })

    expect(clientId).toBe('11111111-1111-4111-8111-111111111111')
    expect(localStorage.getItem(ANONYMOUS_CLIENT_ID_STORAGE_KEY)).toBe(clientId)
  })

  it('reuses an existing client id on later access', () => {
    localStorage.setItem(
      ANONYMOUS_CLIENT_ID_STORAGE_KEY,
      '22222222-2222-4222-8222-222222222222',
    )

    const clientId = getOrCreateAnonymousClientId({
      cryptoSource: createCryptoWithId('33333333-3333-4333-8333-333333333333'),
    })

    expect(clientId).toBe('22222222-2222-4222-8222-222222222222')
  })

  it('creates a new client id after local storage is cleared', () => {
    const firstClientId = getOrCreateAnonymousClientId({
      cryptoSource: createCryptoWithId('44444444-4444-4444-8444-444444444444'),
    })
    localStorage.clear()

    const secondClientId = getOrCreateAnonymousClientId({
      cryptoSource: createCryptoWithId('55555555-5555-4555-8555-555555555555'),
    })

    expect(firstClientId).not.toBe(secondClientId)
    expect(secondClientId).toBe('55555555-5555-4555-8555-555555555555')
  })

  it('reports a storage error when browser storage is unavailable', () => {
    const unavailableStorage = {
      getItem: () => {
        throw new Error('storage blocked')
      },
      setItem: () => {
        throw new Error('storage blocked')
      },
    }

    expect(() =>
      getOrCreateAnonymousClientId({
        storage: unavailableStorage,
        cryptoSource: createCryptoWithId('66666666-6666-4666-8666-666666666666'),
      }),
    ).toThrow(AnonymousClientStorageError)
  })
})
