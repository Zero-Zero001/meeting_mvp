import { z } from 'zod'

import { publicConfig } from '@/config/public-config'

const archiveSegmentSchema = z.object({
  segment_id: z.string(),
  sequence: z.number(),
  start_ms: z.number(),
  end_ms: z.number(),
  speaker_label: z.string().nullable(),
  english_text_final: z.string(),
  chinese_text_final: z.string(),
  translation_status: z.enum(['completed', 'failed', 'retrying']),
  is_key_sentence: z.boolean(),
})

const archiveResponseSchema = z.object({
  session_id: z.string(),
  source_platform: z.enum([
    'google_meet',
    'teams_web',
    'zoom_web',
    'tencent_meeting_web',
    'unknown',
  ]),
  capture_mode: z.enum(['tab_audio', 'system_audio']),
  status: z.enum(['pending_audio', 'active', 'ended', 'quota_stopped', 'error']),
  end_reason: z.string(),
  started_at: z.string().nullable(),
  ended_at: z.string().nullable(),
  duration_seconds: z.number(),
  quota_seconds_consumed: z.number(),
  retention_expires_at: z.string(),
  segments: z.array(archiveSegmentSchema),
})

const archiveExportResponseSchema = z.object({
  export_id: z.string(),
  session_id: z.string(),
  format: z.enum(['markdown', 'json']),
  download_url: z.string(),
  download_url_expires_at: z.string(),
  retention_expires_at: z.string(),
  created_at: z.string(),
})

export type ArchiveSegment = z.infer<typeof archiveSegmentSchema>
export type ArchiveResponse = z.infer<typeof archiveResponseSchema>
export type ArchiveExportResponse = z.infer<typeof archiveExportResponseSchema>
export type ArchiveExportFormat = ArchiveExportResponse['format']
export type ArchiveSearchEvent = {
  event_type: 'archive_searched'
  query_length: number
  matched_segment_count: number
  total_segment_count: number
}
export type ArchiveSegmentCopiedEvent = {
  event_type: 'segment_copied'
  segment_id: string
}
export type ArchiveEvent = ArchiveSearchEvent | ArchiveSegmentCopiedEvent

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>

export class ArchiveAccessError extends Error {
  status: number

  constructor({ message, status }: { message: string; status: number }) {
    super(message)
    this.name = 'ArchiveAccessError'
    this.status = status
  }
}

export function buildArchiveApiUrl({
  apiBaseUrl = publicConfig.apiBaseUrl,
  sessionId,
  token,
}: {
  apiBaseUrl?: string
  sessionId: string
  token: string
}): string {
  const archivePath = `/api/archives/${encodeURIComponent(
    sessionId,
  )}?token=${encodeURIComponent(token)}`
  if (apiBaseUrl.trim() === '') {
    return archivePath
  }
  return `${apiBaseUrl.replace(/\/$/, '')}${archivePath}`
}

export function buildArchiveEventApiUrl({
  apiBaseUrl = publicConfig.apiBaseUrl,
  sessionId,
  token,
}: {
  apiBaseUrl?: string
  sessionId: string
  token: string
}): string {
  const archivePath = `/api/archives/${encodeURIComponent(
    sessionId,
  )}/events?token=${encodeURIComponent(token)}`
  if (apiBaseUrl.trim() === '') {
    return archivePath
  }
  return `${apiBaseUrl.replace(/\/$/, '')}${archivePath}`
}

export function buildArchiveExportApiUrl({
  apiBaseUrl = publicConfig.apiBaseUrl,
  sessionId,
  token,
}: {
  apiBaseUrl?: string
  sessionId: string
  token: string
}): string {
  const archivePath = `/api/archives/${encodeURIComponent(
    sessionId,
  )}/exports?token=${encodeURIComponent(token)}`
  if (apiBaseUrl.trim() === '') {
    return archivePath
  }
  return `${apiBaseUrl.replace(/\/$/, '')}${archivePath}`
}

export async function fetchArchive({
  apiBaseUrl = publicConfig.apiBaseUrl,
  fetchFn = fetch,
  sessionId,
  token,
}: {
  apiBaseUrl?: string
  fetchFn?: FetchLike
  sessionId: string
  token: string
}): Promise<ArchiveResponse> {
  const response = await fetchFn(
    buildArchiveApiUrl({ apiBaseUrl, sessionId, token }),
  )

  if (!response.ok) {
    throw new ArchiveAccessError({
      message: await responseErrorMessage(response),
      status: response.status,
    })
  }

  return archiveResponseSchema.parse(await response.json())
}

export async function createArchiveExport({
  apiBaseUrl = publicConfig.apiBaseUrl,
  fetchFn = fetch,
  format,
  sessionId,
  token,
}: {
  apiBaseUrl?: string
  fetchFn?: FetchLike
  format: ArchiveExportFormat
  sessionId: string
  token: string
}): Promise<ArchiveExportResponse> {
  const response = await fetchFn(
    buildArchiveExportApiUrl({ apiBaseUrl, sessionId, token }),
    {
      body: JSON.stringify({ format }),
      headers: { 'content-type': 'application/json' },
      method: 'POST',
    },
  )

  if (!response.ok) {
    throw new ArchiveAccessError({
      message: await responseErrorMessage(response),
      status: response.status,
    })
  }

  return archiveExportResponseSchema.parse(await response.json())
}

export async function recordArchiveEvent({
  apiBaseUrl = publicConfig.apiBaseUrl,
  event,
  fetchFn = fetch,
  sessionId,
  token,
}: {
  apiBaseUrl?: string
  event: ArchiveEvent
  fetchFn?: FetchLike
  sessionId: string
  token: string
}): Promise<void> {
  const response = await fetchFn(
    buildArchiveEventApiUrl({ apiBaseUrl, sessionId, token }),
    {
      body: JSON.stringify(event),
      headers: { 'content-type': 'application/json' },
      method: 'POST',
    },
  )

  if (!response.ok) {
    throw new ArchiveAccessError({
      message: await responseErrorMessage(response),
      status: response.status,
    })
  }
}

async function responseErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown }
    if (typeof payload.detail === 'string' && payload.detail.trim() !== '') {
      return payload.detail
    }
  } catch {
    // Fall through to the generic HTTP status message.
  }
  return `archive request failed with HTTP ${response.status}`
}
