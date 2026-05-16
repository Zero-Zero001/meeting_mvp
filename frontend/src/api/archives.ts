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

export type ArchiveSegment = z.infer<typeof archiveSegmentSchema>
export type ArchiveResponse = z.infer<typeof archiveResponseSchema>

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
