import { expect, test } from '@playwright/test'

test('renders archive page from session id and token', async ({ page }) => {
  await page.addInitScript(() => {
    window.fetch = async () =>
      new Response(
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

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalOverflow).toBe(false)
})
