import { expect, test } from '@playwright/test'

test('renders archive page from session id and token', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async (text: string) => {
          window.localStorage.setItem('copied-archive-text', text)
        },
      },
    })
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/exports')) {
        const body = String(init?.body ?? '')
        if (body.includes('archive-token')) {
          return new Response('unsafe export body', { status: 400 })
        }
        return new Response(
          JSON.stringify({
            created_at: '2026-05-16T10:09:00Z',
            download_url: 'https://cos.example.test/private-download',
            download_url_expires_at: '2026-05-16T11:09:00Z',
            export_id: '44444444-4444-4444-8444-444444444444',
            format: body.includes('json') ? 'json' : 'markdown',
            retention_expires_at: '2026-06-15T10:00:00Z',
            session_id: '11111111-1111-4111-8111-111111111111',
          }),
          {
            headers: { 'content-type': 'application/json' },
            status: 201,
          },
        )
      }
      if (url.includes('/events')) {
        const body = String(init?.body ?? '')
        if (body.includes('archive-token')) {
          return new Response('unsafe event body', { status: 400 })
        }
        return new Response(null, { status: 204 })
      }
      return new Response(
        JSON.stringify({
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
            {
              chinese_text_final: '预算审查会在明天完成。',
              end_ms: 7200,
              english_text_final: 'The budget review will finish tomorrow.',
              is_key_sentence: false,
              segment_id: '33333333-3333-4333-8333-333333333333',
              sequence: 2,
              speaker_label: null,
              start_ms: 4100,
              translation_status: 'completed',
            },
          ],
          session_id: '11111111-1111-4111-8111-111111111111',
          source_platform: 'google_meet',
          started_at: '2026-05-16T10:00:00Z',
          status: 'ended',
        }),
        {
          headers: { 'content-type': 'application/json' },
          status: 200,
        },
      )
    }
  })
  await page.setViewportSize({ width: 1366, height: 900 })
  await page.goto('/archive/11111111-1111-4111-8111-111111111111?token=archive-token')

  await expect(page.getByRole('heading', { name: '会议归档' })).toBeVisible()
  await expect(page.getByText('正常结束')).toBeVisible()
  await expect(
    page.getByRole('article', { name: '片段 1' }).getByText(
      'We need to align on the launch timeline before Friday.',
    ),
  ).toBeVisible()
  await expect(
    page.getByRole('article', { name: '片段 1' }).getByText(
      '我们需要在周五前对齐上线时间。',
    ),
  ).toBeVisible()
  await page.getByLabel('搜索归档片段').fill('budget')
  await expect(
    page.getByText('We need to align on the launch timeline before Friday.'),
  ).toBeHidden()
  await expect(page.getByText('The budget review will finish tomorrow.')).toBeVisible()

  await page.getByRole('button', { name: '复制片段 2' }).click()
  await expect(page.getByText('已复制')).toBeVisible()
  await expect
    .poll(() => page.evaluate(() => window.localStorage.getItem('copied-archive-text')))
    .toContain('时间：0:04 - 0:07')

  await page.getByRole('button', { name: '导出 JSON' }).click()
  await expect(page.getByText('导出已生成')).toBeVisible()
  await expect(page.getByRole('link', { name: '下载 JSON' })).toHaveAttribute(
    'href',
    'https://cos.example.test/private-download',
  )

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalOverflow).toBe(false)
})
