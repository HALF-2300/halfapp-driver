import { test, expect } from '@playwright/test'
import { loginDriver } from './helpers/driverLogin.ts'

test.use({ storageState: { cookies: [], origins: [] } })

test.describe('App shell consistency', () => {
  test('logged out root renders HalfApp landing', async ({ page }) => {
    await page.goto('/#/')
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('driver-portal-nav').getByText('HalfApp')).toBeVisible()
    await expect(page.getByTestId('driver-auth-panel')).toBeVisible()
  })

  test('authenticated user reaches cockpit from landing', async ({ page }) => {
    await loginDriver(page)
    await expect(page.getByTestId('map-home')).toBeVisible()
  })

  test('earnings screen uses unified HalfApp shell', async ({ page }) => {
    await loginDriver(page)
    await page.goto('/#/driver/earnings')
    await expect(page.getByTestId('earnings-screen')).toBeVisible()
    await expect(page.getByText('HalfApp Driver').first()).toBeVisible()
    await expect(page.getByTestId('earnings-hero-card')).toBeVisible()
    await expect(page.getByTestId('bottom-nav-dock')).toBeVisible()
    await expect(page.getByText(/ETA/i)).toHaveCount(0)
  })

  test('trips screen uses unified HalfApp shell', async ({ page }) => {
    await loginDriver(page)
    await page.goto('/#/driver/trips')
    await expect(page.getByTestId('trips-screen')).toBeVisible()
    await expect(page.getByText('HalfApp Driver').first()).toBeVisible()
    await expect(page.getByTestId('bottom-nav-dock')).toBeVisible()
  })

  test('account screen uses unified HalfApp shell', async ({ page }) => {
    await loginDriver(page)
    await page.goto('/#/driver/profile')
    await expect(page.getByTestId('account-screen')).toBeVisible()
    await expect(page.getByTestId('account-tab-profile')).toBeVisible()
    await expect(page.getByTestId('bottom-nav-dock')).toBeVisible()
    await expect(page.locator('.min-h-screen.bg-gray-50')).toHaveCount(0)
  })

  test('cockpit map still renders after shell work', async ({ page }) => {
    await loginDriver(page)
    await page.goto('/#/driver')
    await expect(page.getByTestId('map-home')).toBeVisible()
    await expect(page.getByTestId('map-view')).toBeVisible()
    await expect(page.getByTestId('bottom-nav-dock')).toBeVisible()
  })
})
