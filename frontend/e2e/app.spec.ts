import { expect, test } from '@playwright/test'

test('renders the frontend workspace shell', async ({ page }) => {
  await page.goto('/')

  await expect(
    page.getByRole('heading', { name: '实时会议工作台' }),
  ).toBeVisible()
  await expect(page.getByText('英文原文区')).toBeVisible()
  await expect(page.getByRole('button', { name: '开始捕获' })).toBeVisible()
})
