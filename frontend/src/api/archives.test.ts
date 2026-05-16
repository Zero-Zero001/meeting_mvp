import { describe, expect, it, vi } from 'vitest'

import {
  ArchiveAccessError,
  buildArchiveApiUrl,
  buildArchiveEventApiUrl,
  fetchArchive,
  recordArchiveEvent,
} from './archives'

const archivePayload = {
  capture_mode: 'tab_audio',
  duration_seconds: 420,
  end_reason: 'user_stopped',
  ended_at: '2026-05-16T10:07:00Z',
  quota_seconds_consumed: 420,
  retention_expires_at: '2026-06-15T10:00:00Z',
  segments: [
    {
      chinese_text_final: '我们需要在周五前对齐上线时间。',
      end_ms: 3200,
      english_text_final:
        'We need to align on the launch timeline before Friday.',
      is_key_sentence: true,
      segment_id: '22222222-2222-4222-8222-222222222222',
      sequence: 1,
      speaker_label: null,
      start_ms: 0,
      translation_status: 'completed',
    },
  ],
  session_id: '11111111-1111-4111-8111-111111111111',
  source_platform: 'google_meet',
  started_at: '2026-05-16T10:00:00Z',
  status: 'ended',
}

describe('archives API', () => {
  it('builds archive URLs from public API base and encoded token', () => {
    expect(
      buildArchiveApiUrl({
        apiBaseUrl: 'https://api.example.test/',
        sessionId: '11111111-1111-4111-8111-111111111111',
        token: 'token with spaces',
      }),
    ).toBe(
      'https://api.example.test/api/archives/11111111-1111-4111-8111-111111111111?token=token%20with%20spaces',
    )
  })

  it('fetches and validates an archive response', async () => {
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(archivePayload), {
        headers: { 'content-type': 'application/json' },
        status: 200,
      }),
    )

    const archive = await fetchArchive({
      apiBaseUrl: '',
      fetchFn,
      sessionId: '11111111-1111-4111-8111-111111111111',
      token: 'archive-token',
    })

    expect(fetchFn).toHaveBeenCalledWith(
      '/api/archives/11111111-1111-4111-8111-111111111111?token=archive-token',
    )
    expect(archive.session_id).toBe('11111111-1111-4111-8111-111111111111')
    expect(archive.segments[0].sequence).toBe(1)
    expect(archive.segments[0].english_text_final).toContain('launch timeline')
  })

  it('throws a typed access error for non-2xx responses', async () => {
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Archive not found or expired' }), {
        headers: { 'content-type': 'application/json' },
        status: 404,
      }),
    )

    await expect(
      fetchArchive({
        fetchFn,
        sessionId: '11111111-1111-4111-8111-111111111111',
        token: 'wrong-token',
      }),
    ).rejects.toMatchObject(
      new ArchiveAccessError({
        message: 'Archive not found or expired',
        status: 404,
      }),
    )
  })

  it('builds archive event URLs from public API base and encoded token', () => {
    expect(
      buildArchiveEventApiUrl({
        apiBaseUrl: 'https://api.example.test/',
        sessionId: '11111111-1111-4111-8111-111111111111',
        token: 'token with spaces',
      }),
    ).toBe(
      'https://api.example.test/api/archives/11111111-1111-4111-8111-111111111111/events?token=token%20with%20spaces',
    )
  })

  it('records archive search events without raw query or token in the body', async () => {
    const fetchFn = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))

    await recordArchiveEvent({
      apiBaseUrl: '',
      event: {
        event_type: 'archive_searched',
        matched_segment_count: 1,
        query_length: 15,
        total_segment_count: 2,
      },
      fetchFn,
      sessionId: '11111111-1111-4111-8111-111111111111',
      token: 'archive-token',
    })

    expect(fetchFn).toHaveBeenCalledWith(
      '/api/archives/11111111-1111-4111-8111-111111111111/events?token=archive-token',
      expect.objectContaining({
        body: JSON.stringify({
          event_type: 'archive_searched',
          matched_segment_count: 1,
          query_length: 15,
          total_segment_count: 2,
        }),
        method: 'POST',
      }),
    )
    const [, init] = fetchFn.mock.calls[0]
    expect(String(init.body)).not.toContain('launch timeline')
    expect(String(init.body)).not.toContain('archive-token')
  })

  it('records segment copied events and reports HTTP errors', async () => {
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Archive not found or expired' }), {
        headers: { 'content-type': 'application/json' },
        status: 404,
      }),
    )

    await expect(
      recordArchiveEvent({
        event: {
          event_type: 'segment_copied',
          segment_id: '22222222-2222-4222-8222-222222222222',
        },
        fetchFn,
        sessionId: '11111111-1111-4111-8111-111111111111',
        token: 'wrong-token',
      }),
    ).rejects.toMatchObject(
      new ArchiveAccessError({
        message: 'Archive not found or expired',
        status: 404,
      }),
    )
  })
})
