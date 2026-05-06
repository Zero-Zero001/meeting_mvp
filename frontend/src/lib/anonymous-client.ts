export const ANONYMOUS_CLIENT_ID_STORAGE_KEY = 'meeting_mvp.client_id'

export class AnonymousClientStorageError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AnonymousClientStorageError'
  }
}

type AnonymousClientStorage = Pick<Storage, 'getItem' | 'setItem'>

type AnonymousClientCrypto = Pick<Crypto, 'randomUUID'>

type GetOrCreateAnonymousClientIdOptions = {
  storage?: AnonymousClientStorage
  cryptoSource?: AnonymousClientCrypto
}

function getDefaultStorage(): AnonymousClientStorage {
  return window.localStorage
}

function getDefaultCrypto(): AnonymousClientCrypto {
  return window.crypto
}

export function getOrCreateAnonymousClientId(
  options: GetOrCreateAnonymousClientIdOptions = {},
): string {
  const storage = options.storage ?? getDefaultStorage()
  const cryptoSource = options.cryptoSource ?? getDefaultCrypto()

  try {
    const existingClientId = storage.getItem(ANONYMOUS_CLIENT_ID_STORAGE_KEY)
    if (existingClientId) {
      return existingClientId
    }

    const clientId = cryptoSource.randomUUID()
    storage.setItem(ANONYMOUS_CLIENT_ID_STORAGE_KEY, clientId)
    return clientId
  } catch (error) {
    throw new AnonymousClientStorageError(
      error instanceof Error
        ? error.message
        : 'anonymous client storage is unavailable',
    )
  }
}
