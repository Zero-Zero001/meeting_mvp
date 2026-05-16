import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import ArchivePage from './ArchivePage'
import {
  ArchiveAccessError,
  type ArchiveExportResponse,
  type ArchiveResponse,
  type ArchiveSegment,
} from '@/api/archives'

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

const secondSegment: ArchiveSegment = {
  chinese_text_final: '预算审查会在明天完成。',
  end_ms: 7200,
  english_text_final: 'The budget review will finish tomorrow.',
  is_key_sentence: false,
  segment_id: '33333333-3333-4333-8333-333333333333',
  sequence: 2,
  speaker_label: null,
  start_ms: 4100,
  translation_status: 'completed',
}

const exportResponse: ArchiveExportResponse = {
  created_at: '2026-05-16T10:09:00Z',
  download_url: 'https://cos.example.test/private-download',
  download_url_expires_at: '2026-05-16T11:09:00Z',
  export_id: '44444444-4444-4444-8444-444444444444',
  format: 'markdown',
  retention_expires_at: '2026-06-15T10:00:00Z',
  session_id: '11111111-1111-4111-8111-111111111111',
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
    expect(screen.getByRole('button', { name: '导出 Markdown' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '导出 JSON' })).toBeDisabled()
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

  it('filters archive segments by English, Chinese, and timestamp matches', async () => {
    const user = userEvent.setup()
    const fetchArchiveFn = vi.fn().mockResolvedValue({
      ...archiveResponse,
      segments: [...archiveResponse.segments, secondSegment],
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

    const searchInput = await screen.findByLabelText('搜索归档片段')
    await user.type(searchInput, 'BUDGET')
    expect(screen.queryByText('We need to align on the launch timeline before Friday.')).not.toBeInTheDocument()
    expect(screen.getByText('The budget review will finish tomorrow.')).toBeInTheDocument()

    await user.clear(searchInput)
    await user.type(searchInput, '周五')
    expect(screen.getByText('我们需要在周五前对齐上线时间。')).toBeInTheDocument()
    expect(screen.queryByText('The budget review will finish tomorrow.')).not.toBeInTheDocument()

    await user.clear(searchInput)
    await user.type(searchInput, '0:04')
    expect(screen.queryByText('We need to align on the launch timeline before Friday.')).not.toBeInTheDocument()
    expect(screen.getByText('The budget review will finish tomorrow.')).toBeInTheDocument()
  })

  it('renders a no results state and records debounced search metadata only', async () => {
    const user = userEvent.setup()
    const recordArchiveEventFn = vi.fn().mockResolvedValue(undefined)

    render(
      <ArchivePage
        fetchArchiveFn={vi.fn().mockResolvedValue({
          ...archiveResponse,
          segments: [...archiveResponse.segments, secondSegment],
        } satisfies ArchiveResponse)}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=archive-token',
        }}
        recordArchiveEventFn={recordArchiveEventFn}
      />,
    )

    await user.type(await screen.findByLabelText('搜索归档片段'), 'missing phrase')

    expect(await screen.findByText('未找到匹配片段')).toBeInTheDocument()
    await waitFor(() => {
      expect(recordArchiveEventFn).toHaveBeenCalledWith({
        event: {
          event_type: 'archive_searched',
          matched_segment_count: 0,
          query_length: 14,
          total_segment_count: 2,
        },
        sessionId: '11111111-1111-4111-8111-111111111111',
        token: 'archive-token',
      })
    })
    expect(JSON.stringify(recordArchiveEventFn.mock.calls[0][0].event)).not.toContain(
      'missing phrase',
    )
    expect(JSON.stringify(recordArchiveEventFn.mock.calls[0][0].event)).not.toContain(
      'archive-token',
    )
  })

  it('copies a segment with time, English, and Chinese text, then records copy metadata', async () => {
    const user = userEvent.setup()
    const writeClipboardTextFn = vi.fn().mockResolvedValue(undefined)
    const recordArchiveEventFn = vi.fn().mockResolvedValue(undefined)

    render(
      <ArchivePage
        fetchArchiveFn={vi.fn().mockResolvedValue(archiveResponse)}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=archive-token',
        }}
        recordArchiveEventFn={recordArchiveEventFn}
        writeClipboardTextFn={writeClipboardTextFn}
      />,
    )

    await user.click(await screen.findByRole('button', { name: '复制片段 1' }))

    expect(writeClipboardTextFn).toHaveBeenCalledWith(
      [
        '时间：0:00 - 0:03',
        '英文：We need to align on the launch timeline before Friday.',
        '中文：我们需要在周五前对齐上线时间。',
      ].join('\n'),
    )
    expect(await screen.findByText('已复制')).toBeInTheDocument()
    expect(recordArchiveEventFn).toHaveBeenCalledWith({
      event: {
        event_type: 'segment_copied',
        segment_id: '22222222-2222-4222-8222-222222222222',
      },
      sessionId: '11111111-1111-4111-8111-111111111111',
      token: 'archive-token',
    })
  })

  it('shows a clipboard failure notice without clearing archive content', async () => {
    const user = userEvent.setup()

    render(
      <ArchivePage
        fetchArchiveFn={vi.fn().mockResolvedValue(archiveResponse)}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=archive-token',
        }}
        writeClipboardTextFn={vi.fn().mockRejectedValue(new Error('denied'))}
      />,
    )

    await user.click(await screen.findByRole('button', { name: '复制片段 1' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '复制失败，请手动选择文本复制',
    )
    expect(
      screen.getByText('We need to align on the launch timeline before Friday.'),
    ).toBeInTheDocument()
  })

  it('creates a Markdown export and shows a short-lived download link', async () => {
    const user = userEvent.setup()
    const createArchiveExportFn = vi.fn().mockResolvedValue(exportResponse)

    render(
      <ArchivePage
        createArchiveExportFn={createArchiveExportFn}
        fetchArchiveFn={vi.fn().mockResolvedValue(archiveResponse)}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=archive-token',
        }}
      />,
    )

    await user.click(await screen.findByRole('button', { name: '导出 Markdown' }))

    expect(createArchiveExportFn).toHaveBeenCalledWith({
      format: 'markdown',
      sessionId: '11111111-1111-4111-8111-111111111111',
      token: 'archive-token',
    })
    const downloadLink = await screen.findByRole('link', { name: '下载 Markdown' })
    expect(downloadLink).toHaveAttribute(
      'href',
      'https://cos.example.test/private-download',
    )
    expect(screen.getByText('导出已生成')).toBeInTheDocument()
  })

  it('shows export failure guidance without clearing archive content', async () => {
    const user = userEvent.setup()

    render(
      <ArchivePage
        createArchiveExportFn={vi.fn().mockRejectedValue(
          new ArchiveAccessError({
            message: 'Archive export is temporarily unavailable',
            status: 503,
          }),
        )}
        fetchArchiveFn={vi.fn().mockResolvedValue(archiveResponse)}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=archive-token',
        }}
      />,
    )

    await user.click(await screen.findByRole('button', { name: '导出 JSON' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '导出暂时不可用，请稍后重试',
    )
    expect(
      screen.getByText('We need to align on the launch timeline before Friday.'),
    ).toBeInTheDocument()
  })

  it('shows empty export rejection guidance without clearing archive content', async () => {
    const user = userEvent.setup()

    render(
      <ArchivePage
        createArchiveExportFn={vi.fn().mockRejectedValue(
          new ArchiveAccessError({
            message: 'Archive has no exportable final segments',
            status: 409,
          }),
        )}
        fetchArchiveFn={vi.fn().mockResolvedValue(archiveResponse)}
        location={{
          pathname: '/archive/11111111-1111-4111-8111-111111111111',
          search: '?token=archive-token',
        }}
      />,
    )

    await user.click(await screen.findByRole('button', { name: '导出 JSON' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '暂无可导出的 final 片段',
    )
    expect(screen.getByText('我们需要在周五前对齐上线时间。')).toBeInTheDocument()
  })
})
