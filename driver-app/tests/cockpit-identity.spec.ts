import { test, expect } from '@playwright/test'
import { loginDriver } from './helpers/driverLogin.ts'

test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Cockpit identity pass', () => {
  test('map owns the screen with overlay shell', async ({ page }) => {
    await loginDriver(page)
    await expect(page.getByTestId('experimental-map-panel')).toBeVisible()
    await expect(page.getByTestId('map-view')).toBeVisible()
    const mapBox = await page.getByTestId('experimental-map-panel').boundingBox()
    const homeBox = await page.getByTestId('map-home').boundingBox()
    expect(mapBox?.height).toBeGreaterThan((homeBox?.height ?? 0) * 0.85)
  })

  test('availability is compact action sheet, not dashboard slab', async ({ page }) => {
    await loginDriver(page)
    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('sheet-online-idle')).toBeVisible()
    await expect(page.getByTestId('availability-title')).toHaveText('Available')
    await expect(page.getByTestId('driver-action-sheet')).toBeVisible()
    await expect(page.getByText('Waiting for requests nearby.')).toBeVisible()
    const card = await page.getByTestId('marketplace-bottom-sheet').boundingBox()
    const viewport = page.viewportSize()
    expect(card?.height ?? 9999).toBeLessThan((viewport?.height ?? 800) * 0.35)
    await expect(page.getByText('Driver is available')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Refresh marketplace truth/i })).toHaveCount(0)
  })

  test('bottom nav is floating dock overlay', async ({ page }) => {
    await loginDriver(page)
    const dock = page.getByTestId('bottom-nav-dock')
    await expect(dock).toBeVisible()
    const box = await dock.boundingBox()
    expect(box?.height).toBeLessThan(72)
    expect(box?.width).toBeLessThan(700)
  })

  test('dev ride action is compact and dev-labeled', async ({ page }) => {
    await loginDriver(page)
    await page.getByTestId('go-online-btn').click()
    const devBtn = page.getByTestId('dev-demo-ride-btn')
    await expect(devBtn).toBeVisible()
    await expect(devBtn).toContainText(/DEV/i)
    await expect(devBtn).toContainText(/Create ride/i)
    const btnBox = await devBtn.boundingBox()
    const sheetBox = await page.getByTestId('marketplace-bottom-sheet').boundingBox()
    expect(btnBox?.height ?? 999).toBeLessThan(56)
    expect(btnBox?.width ?? 999).toBeLessThan((sheetBox?.width ?? 400) * 0.55)
    await expect(page.getByRole('button', { name: /Create backend simulation ride/i })).toHaveCount(0)
  })

  test('diagnostics hide noisy truth labels from primary surface', async ({ page }) => {
    await loginDriver(page)
    await expect(page.getByTestId('cockpit-truth-labels')).toHaveCount(0)
    await page.getByTestId('diagnostics-toggle').click()
    await expect(page.getByTestId('diagnostics-drawer')).toBeVisible()
    await expect(page.getByTestId('cockpit-truth-labels')).toBeVisible()
    await expect(page.getByTestId('truth-label-experimental')).toBeVisible()
  })

  test('sync control lives in diagnostics without dominating UI', async ({ page }) => {
    await loginDriver(page)
    await page.getByTestId('go-online-btn').click()
    await page.getByTestId('diagnostics-toggle').click()
    const sync = page.getByTestId('sync-marketplace-btn').first()
    await expect(sync).toBeVisible()
    await expect(sync).toContainText(/sync/i)
  })

  test('no ETA or route guarantee on primary idle surface', async ({ page }) => {
    await loginDriver(page)
    await page.getByTestId('go-online-btn').click()
    await expect(page.getByText(/ETA guarantee/i)).toHaveCount(0)
    await expect(page.getByText(/route guarantee/i)).toHaveCount(0)
  })

  test('backend presence toggle still works', async ({ page }) => {
    await loginDriver(page)
    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('availability-pill')).toContainText(/online/i)
    await expect(page.getByTestId('sheet-online-idle')).toBeVisible()
  })

  test('agent brief generator only in diagnostics when dev', async ({ page }) => {
    await loginDriver(page)
    await expect(page.getByTestId('agent-brief-generator')).toHaveCount(0)
    await page.getByTestId('diagnostics-toggle').click()
    const brief = page.getByTestId('agent-brief-generator')
    if (await brief.count()) {
      await expect(brief).toContainText(/DEV ONLY/i)
    }
  })
})
