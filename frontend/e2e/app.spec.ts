import { expect, test, type Page } from '@playwright/test'

type CaptureMockMode = 'success' | 'denied' | 'no_audio'

async function mockDisplayMedia(page: Page, mode: CaptureMockMode) {
  await page.addInitScript((captureMode) => {
    function createTrack(kind: 'audio' | 'video') {
      return {
        kind,
        stop() {},
      }
    }

    function createStream(audioTrackCount: number) {
      const audioTracks = Array.from({ length: audioTrackCount }, () =>
        createTrack('audio'),
      )
      const tracks = [...audioTracks, createTrack('video')]

      return {
        getAudioTracks: () => audioTracks,
        getTracks: () => tracks,
      }
    }

    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getDisplayMedia: async () => {
          if (captureMode === 'denied') {
            throw new DOMException('Permission denied', 'NotAllowedError')
          }

          return createStream(captureMode === 'no_audio' ? 0 : 1)
        },
      },
    })
  }, mode)
}

test('renders the desktop workspace shell', async ({ page }) => {
  await mockDisplayMedia(page, 'success')
  await page.setViewportSize({ width: 1366, height: 900 })
  await page.goto('/')

  await expect(
    page.getByRole('heading', { name: '实时会议工作台' }),
  ).toBeVisible()
  const statusBar = page.getByRole('banner', { name: '会议状态栏' })
  await expect(statusBar).toBeVisible()
  await expect(page.getByRole('region', { name: '英文原文区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '中文翻译区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '当前重点句区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '会议时间线区' })).toBeVisible()
  await expect(page.getByRole('button', { name: '开始捕获' })).toBeVisible()
  await expect(page.getByRole('button', { name: '标签页音频' })).toBeVisible()
  await expect(page.getByRole('button', { name: '系统音频' })).toBeVisible()
  await expect(statusBar.getByText('ASR')).toBeVisible()
  await expect(statusBar.getByText('翻译')).toBeVisible()
  await expect(page.getByRole('combobox', { name: '会议平台' })).toBeVisible()

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalOverflow).toBe(false)
})

test('renders the mobile workspace without horizontal overflow', async ({ page }) => {
  await mockDisplayMedia(page, 'success')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')

  const statusBar = page.getByRole('banner', { name: '会议状态栏' })
  await expect(statusBar).toBeVisible()
  await expect(page.getByRole('region', { name: '英文原文区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '中文翻译区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '当前重点句区' })).toBeVisible()
  await expect(page.getByRole('region', { name: '会议时间线区' })).toBeVisible()

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalOverflow).toBe(false)
})

test('captures display audio through the browser picker', async ({ page }) => {
  await mockDisplayMedia(page, 'success')
  await page.goto('/')

  await page.getByRole('button', { name: '开始捕获' }).click()

  await expect(
    page.getByRole('banner', { name: '会议状态栏' }).getByText('已捕获音频'),
  ).toBeVisible()
})

test('shows retry guidance when display capture is denied', async ({ page }) => {
  await mockDisplayMedia(page, 'denied')
  await page.goto('/')

  await page.getByRole('button', { name: '开始捕获' }).click()

  await expect(page.getByText('浏览器拒绝了捕获授权。')).toBeVisible()
  await expect(page.getByRole('button', { name: '重新授权' })).toBeVisible()
})

test('shows system audio fallback guidance when capture has no audio track', async ({
  page,
}) => {
  await mockDisplayMedia(page, 'no_audio')
  await page.goto('/')

  await page.getByRole('button', { name: '开始捕获' }).click()

  await expect(page.getByText('请切换系统音频模式后重新捕获。')).toBeVisible()
})
