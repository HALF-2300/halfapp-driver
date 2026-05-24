import { test, expect } from '@playwright/test'
import { loginDriver } from './helpers/driverLogin.ts'

test('external Google Maps buttons open directions URL without embedding maps', async ({ page }) => {
  test.setTimeout(60_000)

  const openedUrls: string[] = []
  await page.exposeFunction('recordOpenedUrl', (url: string) => {
    openedUrls.push(url)
  })
  await page.addInitScript(() => {
    window.open = ((url: string | URL | undefined) => {
      const href = typeof url === 'string' ? url : url?.toString() ?? ''
      ;(window as unknown as { recordOpenedUrl?: (u: string) => void }).recordOpenedUrl?.(href)
      return null
    }) as typeof window.open
  })

  await loginDriver(page)
  await page.getByTestId('go-online-btn').click()
  await page.getByTestId('dev-demo-ride-btn').click()
  await expect(page.getByTestId('sheet-request-incoming')).toBeVisible()

  await expect(page.getByTestId('open-pickup-google-maps')).toBeVisible()
  await expect(page.getByTestId('open-destination-google-maps')).toBeVisible()
  await expect(page.getByTestId('map-view')).toBeVisible()
  await expect(page.locator('iframe[src*="google"]')).toHaveCount(0)

  await page.getByTestId('open-pickup-google-maps').click()
  await expect.poll(() => openedUrls.length).toBeGreaterThan(0)
  const pickupUrl = openedUrls[openedUrls.length - 1]
  expect(pickupUrl).toMatch(/^https:\/\/www\.google\.com\/maps\/dir\/\?api=1&destination=/)
  expect(pickupUrl).not.toContain('maps.googleapis.com/maps/api')

  await page.getByTestId('accept-ride-btn').click()
  await expect(page.getByTestId('sheet-accepted_to_pickup')).toBeVisible()
  await expect(page.getByTestId('open-pickup-google-maps')).toBeVisible()
  await expect(page.getByTestId('open-destination-google-maps')).toBeVisible()
})
