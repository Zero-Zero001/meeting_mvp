import { publicConfig } from '@/config/public-config'

export type AnonymousClientSyncResult = {
  clientId: string
  dailyFreeSeconds: number
  remainingSecondsToday: number
  isNew: boolean
}

type AnonymousClientApiResponse = {
  client_id: string
  daily_free_seconds: number
  remaining_seconds_today: number
  is_new: boolean
}

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

type SyncAnonymousClientOptions = {
  apiBaseUrl?: string
  fetchFn?: FetchLike
}

function anonymousClientsUrl(apiBaseUrl: string): string {
  if (apiBaseUrl.trim() === '') {
    return '/api/anonymous-clients'
  }
  return `${apiBaseUrl.replace(/\/$/, '')}/api/anonymous-clients`
}

export async function syncAnonymousClient(
  clientId: string,
  options: SyncAnonymousClientOptions = {},
): Promise<AnonymousClientSyncResult> {
  const fetchFn = options.fetchFn ?? fetch
  const response = await fetchFn(
    anonymousClientsUrl(options.apiBaseUrl ?? publicConfig.apiBaseUrl),
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({ client_id: clientId }),
    },
  )

  if (!response.ok) {
    throw new Error(`anonymous client sync failed with HTTP ${response.status}`)
  }

  const payload = (await response.json()) as AnonymousClientApiResponse
  return {
    clientId: payload.client_id,
    dailyFreeSeconds: payload.daily_free_seconds,
    remainingSecondsToday: payload.remaining_seconds_today,
    isNew: payload.is_new,
  }
}
