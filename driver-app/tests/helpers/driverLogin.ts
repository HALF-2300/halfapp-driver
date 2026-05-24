import { expect, type Page } from '@playwright/test'

/** Log in as demo driver through the Driver Portal auth panel. */
export async function loginDriver(page: Page) {
  await page.goto('/#/')
  await page.evaluate(() => {
    try {
      localStorage.clear()
      sessionStorage.clear()
    } catch {
      /* ignore */
    }
  })
  await page.reload()
  await page.waitForLoadState('domcontentloaded')
  await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 })
  await page.getByTestId('auth-tab-signin').click()
  await page.getByPlaceholder('Email Address').fill('driver1@example.com')
  await page.getByPlaceholder('Password').fill('driver123')
  await page.getByTestId('login-submit-btn').click()
  await expect(page).toHaveURL(/\/driver/, { timeout: 15_000 })
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 25_000 })
}
