import { test, expect, type Page } from '@playwright/test'

test.use({ storageState: { cookies: [], origins: [] } })

/** Offline mock user seeded in `src/utils/api.js` when VITE_ALLOW_OFFLINE_MOCK=true */
async function loginAsMockDriver(page: Page) {
  await page.goto('/#/login')
  await page.evaluate(() => {
    try {
      localStorage.clear()
      sessionStorage.clear()
    } catch {
      /* ignore */
    }
  })
  await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 })
  const signIn = page.getByRole('button', { name: 'Sign In' }).first()
  if (await signIn.isVisible()) await signIn.click()
  await page.getByPlaceholder('Email Address').fill('driver1@example.com')
  await page.getByPlaceholder('Password').fill('driver123')
  await page.getByTestId('login-submit-btn').click()
  await page.waitForURL(/\/driver/, { timeout: 15_000 })
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })
}

test('bottom nav: Home → Earnings → Trips → Account', async ({ page }) => {
  await loginAsMockDriver(page)

  await expect(page).toHaveURL(/\/driver/)

  await expect(page.getByTestId('map-home')).toBeVisible()

  await expect(page.getByTestId('tab-home')).toBeVisible()
  await expect(page.getByTestId('tab-earnings')).toBeVisible()
  await expect(page.getByTestId('tab-trips')).toBeVisible()
  await expect(page.getByTestId('tab-account')).toBeVisible()

  await page.getByTestId('tab-earnings').click()
  await expect(page.getByTestId('earnings-screen')).toBeVisible({ timeout: 5_000 })

  await page.getByTestId('tab-trips').click()
  await expect(page.getByTestId('trips-screen')).toBeVisible({ timeout: 5_000 })

  await page.getByTestId('tab-account').click()
  await expect(page).toHaveURL(/\/driver\/profile/, { timeout: 5_000 })
  await expect(page.getByTestId('account-screen')).toBeVisible({ timeout: 5_000 })
  await expect(page.getByTestId('account-profile-panel')).toBeVisible()
})
