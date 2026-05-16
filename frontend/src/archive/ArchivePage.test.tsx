import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ArchivePage from './ArchivePage'
import { ArchiveAccessError, type ArchiveResponse } from '@/api/archives'

const archiveResponse: ArchiveResponse = {
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

describe('ArchivePage', () => {
  it('renders bilingual final archive segments', async () => {
    const fetchArchiveFn = vi.fn().mockResolvedValue(archiveResponse)

    render(
      <ArchivePage
        fetchArchiveFn={fetchArchiveFn}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=archive-token',
        }}
      />,
    )

    expect(await screen.findByRole('heading', { name: '会议归档' })).toBeInTheDocument()
    expect(fetchArchiveFn).toHaveBeenCalledWith({
      sessionId: '11111111-1111-4111-8111-111111111111',
      token: 'archive-token',
    })
    expect(screen.getByText('正常结束')).toBeInTheDocument()
    expect(screen.getByText('Google Meet')).toBeInTheDocument()
    const segment = screen.getByRole('article', { name: '片段 1' })
    expect(
      within(segment).getByText(
        'We need to align on the launch timeline before Friday.',
      ),
    ).toBeInTheDocument()
    expect(
      within(segment).getByText('我们需要在周五前对齐上线时间。'),
    ).toBeInTheDocument()
    expect(within(segment).getByText('重点句')).toBeInTheDocument()
  })

  it('renders an empty archive state', async () => {
    const fetchArchiveFn = vi.fn().mockResolvedValue({
      ...archiveResponse,
      segments: [],
    } satisfies ArchiveResponse)

    render(
      <ArchivePage
        fetchArchiveFn={fetchArchiveFn}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=archive-token',
        }}
      />,
    )

    expect(await screen.findByText('暂无 final 片段')).toBeInTheDocument()
  })

  it('shows clear guidance when token is missing', () => {
    render(
      <ArchivePage
        fetchArchiveFn={vi.fn()}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '',
        }}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('归档访问链接无效')
  })

  it('shows access error for wrong or expired archive links', async () => {
    const fetchArchiveFn = vi.fn().mockRejectedValue(
      new ArchiveAccessError({
        message: 'Archive not found or expired',
        status: 404,
      }),
    )

    render(
      <ArchivePage
        fetchArchiveFn={fetchArchiveFn}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=wrong-token',
        }}
      />,
    )

    expect(
      await screen.findByText('归档不存在或访问链接已失效'),
    ).toBeInTheDocument()
  })

  it('renders abnormal end reason for provider and disconnect sessions', async () => {
    const fetchArchiveFn = vi.fn().mockResolvedValue({
      ...archiveResponse,
      end_reason: 'browser_disconnected',
      status: 'error',
    } satisfies ArchiveResponse)

    render(
      <ArchivePage
        fetchArchiveFn={fetchArchiveFn}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=archive-token',
        }}
      />,
    )

    expect(await screen.findByText('浏览器断开')).toBeInTheDocument()
  })
})
