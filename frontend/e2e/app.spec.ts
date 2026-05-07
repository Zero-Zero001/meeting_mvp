import { expect, test } from '@playwright/test'

test('renders the desktop workspace shell', async ({ page }) => {
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

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalOverflow).toBe(false)
})

test('renders the mobile workspace without horizontal overflow', async ({ page }) => {
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
