import { test, expect } from '@playwright/test'
import { loginDriver } from './helpers/driverLogin.ts'

test.use({ storageState: { cookies: [], origins: [] } })

const VERBOSE_PROOF = [
  /not backend dispatch truth/i,
  /No ETA guarantee/i,
  /No route guarantee/i,
  /Backend-owned/i,
  /Device location on map only/i,
]

test.describe('Driver cockpit real-product pass', () => {
  test('primary idle surface hides verbose developer proof labels', async ({ page }) => {
    await loginDriver(page)
    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('sheet-online-idle')).toBeVisible()

    await expect(page.getByTestId('diagnostics-drawer')).toHaveCount(0)
    const primary = page.getByTestId('map-region').or(page.getByTestId('marketplace-bottom-sheet'))
    for (const pattern of VERBOSE_PROOF) {
      await expect(primary.getByText(pattern, { exact: false })).toHaveCount(0)
    }
    await expect(page.getByTestId('cockpit-truth-labels')).toHaveCount(0)
    await expect(page.getByTestId('location-status')).toContainText(
      /location active|finding your location|location unavailable/i
    )
  })

  test('diagnostics drawer contains backend truth and proof labels', async ({ page }) => {
    await loginDriver(page)
    await page.getByTestId('diagnostics-toggle').click()
    await expect(page.getByTestId('diagnostics-drawer')).toBeVisible()
    await expect(page.getByTestId('cockpit-truth-labels')).toBeVisible()
    await expect(page.getByTestId('truth-label-backend_owned')).toBeVisible()
    await expect(page.getByTestId('diagnostics-location-copy')).toContainText(
      /map only|dispatch truth|DEV FALLBACK/i
    )
    await expect(page.getByTestId('truth-label-no_fare_quote')).toBeVisible()
    await expect(page.getByTestId('truth-label-no_route_snapshot')).toBeVisible()
  })

  test('offline then reload stays offline from backend', async ({ page }) => {
    await loginDriver(page)
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Offline/i)
    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Online/i)
    await page.getByTestId('go-offline-btn').click()
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Offline/i)
    await page.reload()
    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Offline/i)
    await expect(page.getByTestId('sheet-offline')).toBeVisible()
  })

  test('online then reload stays online from backend', async ({ page }) => {
    await loginDriver(page)
    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Online/i)
    await page.reload()
    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Online/i)
    await expect(page.getByTestId('sheet-online-idle')).toBeVisible()
  })

  test('offline action sheet uses driver-simple copy', async ({ page }) => {
    await loginDriver(page)
    await expect(page.getByTestId('driver-action-sheet')).toBeVisible()
    await expect(page.getByText('Go online to start receiving requests.')).toBeVisible()
    await expect(page.getByTestId('go-online-btn')).toBeVisible()
  })

  test('online idle action sheet offers go offline', async ({ page }) => {
    await loginDriver(page)
    await page.getByTestId('go-online-btn').click()
    await expect(page.getByText('Waiting for requests nearby.')).toBeVisible()
    await expect(page.getByTestId('go-offline-btn')).toBeVisible()
  })
})
