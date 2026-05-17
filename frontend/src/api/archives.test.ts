import { describe, expect, it, vi } from 'vitest'

import {
  ArchiveAccessError,
  buildArchiveApiUrl,
  buildArchiveEventApiUrl,
  buildArchiveExportApiUrl,
  buildArchiveSegmentKeySentenceApiUrl,
  createArchiveExport,
  fetchArchive,
  recordArchiveEvent,
  updateArchiveSegmentKeySentence,
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
  timeline_items: [
    {
      id: 'segment-final-22222222-2222-4222-8222-222222222222',
      item_type: 'segment_final',
      segment_id: '22222222-2222-4222-8222-222222222222',
      text: '我们需要在周五前对齐上线时间线。',
      timestamp_ms: 3200,
    },
    {
      id: 'export-created-44444444-4444-4444-8444-444444444444',
      item_type: 'export_created',
      text: '已生成 Markdown 导出',
      timestamp_ms: 540000,
    },
  ],
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
    expect(archive.segments[0].translation_retry_attempts).toBe(0)
    expect(archive.segments[0].translation_retry_exhausted).toBe(false)
    expect(archive.timeline_items).toHaveLength(2)
    expect(archive.timeline_items[0].item_type).toBe('segment_final')
    expect(archive.timeline_items[1].segment_id).toBeUndefined()
  })

  it('defaults archive timeline items to an empty list for older API responses', async () => {
    const legacyPayload = Object.fromEntries(
      Object.entries(archivePayload).filter(([key]) => key !== 'timeline_items'),
    )
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(legacyPayload), {
        headers: { 'content-type': 'application/json' },
        status: 200,
      }),
    )

    const archive = await fetchArchive({
      fetchFn,
      sessionId: '11111111-1111-4111-8111-111111111111',
      token: 'archive-token',
    })

    expect(archive.timeline_items).toEqual([])
  })

  it('parses retry metadata when backend reports background translation status', async () => {
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          ...archivePayload,
          segments: [
            {
              ...archivePayload.segments[0],
              chinese_text_final: '',
              translation_retry_attempts: 2,
              translation_retry_exhausted: true,
              translation_status: 'failed',
            },
          ],
        }),
        {
          headers: { 'content-type': 'application/json' },
          status: 200,
        },
      ),
    )

    const archive = await fetchArchive({
      fetchFn,
      sessionId: '11111111-1111-4111-8111-111111111111',
      token: 'archive-token',
    })

    expect(archive.segments[0].translation_status).toBe('failed')
    expect(archive.segments[0].translation_retry_attempts).toBe(2)
    expect(archive.segments[0].translation_retry_exhausted).toBe(true)
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

  it('builds archive export URLs from public API base and encoded token', () => {
    expect(
      buildArchiveExportApiUrl({
        apiBaseUrl: 'https://api.example.test/',
        sessionId: '11111111-1111-4111-8111-111111111111',
        token: 'token with spaces',
      }),
    ).toBe(
      'https://api.example.test/api/archives/11111111-1111-4111-8111-111111111111/exports?token=token%20with%20spaces',
    )
  })

  it('creates archive exports without token or archive text in the POST body', async () => {
    const exportPayload = {
      created_at: '2026-05-16T10:09:00Z',
      download_url: 'https://cos.example.test/private-download',
      download_url_expires_at: '2026-05-16T11:09:00Z',
      export_id: '44444444-4444-4444-8444-444444444444',
      format: 'markdown',
      retention_expires_at: '2026-06-15T10:00:00Z',
      session_id: '11111111-1111-4111-8111-111111111111',
    }
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(exportPayload), {
        headers: { 'content-type': 'application/json' },
        status: 201,
      }),
    )

    const result = await createArchiveExport({
      apiBaseUrl: '',
      fetchFn,
      format: 'markdown',
      sessionId: '11111111-1111-4111-8111-111111111111',
      token: 'archive-token',
    })

    expect(result.download_url).toBe(exportPayload.download_url)
    expect(fetchFn).toHaveBeenCalledWith(
      '/api/archives/11111111-1111-4111-8111-111111111111/exports?token=archive-token',
      expect.objectContaining({
        body: JSON.stringify({ format: 'markdown' }),
        method: 'POST',
      }),
    )
    const [, init] = fetchFn.mock.calls[0]
    expect(String(init.body)).not.toContain('archive-token')
    expect(String(init.body)).not.toContain('launch timeline')
  })

  it('reports export HTTP errors as typed archive access errors', async () => {
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Archive export is temporarily unavailable' }), {
        headers: { 'content-type': 'application/json' },
        status: 503,
      }),
    )

    await expect(
      createArchiveExport({
        fetchFn,
        format: 'json',
        sessionId: '11111111-1111-4111-8111-111111111111',
        token: 'archive-token',
      }),
    ).rejects.toMatchObject(
      new ArchiveAccessError({
        message: 'Archive export is temporarily unavailable',
        status: 503,
      }),
    )
  })

  it('builds segment key sentence URLs from public API base and encoded token', () => {
    expect(
      buildArchiveSegmentKeySentenceApiUrl({
        apiBaseUrl: 'https://api.example.test/',
        segmentId: '22222222-2222-4222-8222-222222222222',
        sessionId: '11111111-1111-4111-8111-111111111111',
        token: 'token with spaces',
      }),
    ).toBe(
      'https://api.example.test/api/archives/11111111-1111-4111-8111-111111111111/segments/22222222-2222-4222-8222-222222222222/key-sentence?token=token%20with%20spaces',
    )
  })

  it('updates segment key sentence state without token or archive text in the body', async () => {
    const updatedSegment = {
      ...archivePayload.segments[0],
      is_key_sentence: true,
    }
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(updatedSegment), {
        headers: { 'content-type': 'application/json' },
        status: 200,
      }),
    )

    const result = await updateArchiveSegmentKeySentence({
      apiBaseUrl: '',
      fetchFn,
      isKeySentence: true,
      segmentId: '22222222-2222-4222-8222-222222222222',
      sessionId: '11111111-1111-4111-8111-111111111111',
      token: 'archive-token',
    })

    expect(result.is_key_sentence).toBe(true)
    expect(fetchFn).toHaveBeenCalledWith(
      '/api/archives/11111111-1111-4111-8111-111111111111/segments/22222222-2222-4222-8222-222222222222/key-sentence?token=archive-token',
      expect.objectContaining({
        body: JSON.stringify({ is_key_sentence: true }),
        method: 'PATCH',
      }),
    )
    const [, init] = fetchFn.mock.calls[0]
    expect(String(init.body)).not.toContain('archive-token')
    expect(String(init.body)).not.toContain('launch timeline')
  })

  it('reports key sentence update HTTP errors as typed archive access errors', async () => {
    const fetchFn = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Archive not found or expired' }), {
        headers: { 'content-type': 'application/json' },
        status: 404,
      }),
    )

    await expect(
      updateArchiveSegmentKeySentence({
        fetchFn,
        isKeySentence: false,
        segmentId: '22222222-2222-4222-8222-222222222222',
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
