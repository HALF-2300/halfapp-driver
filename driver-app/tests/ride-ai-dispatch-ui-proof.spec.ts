/**
 * UI proof — ride AI dispatch panel through cockpit lifecycle (manual mode OK without ENGINEERING_ASSISTANT_ENABLED).
 * Self-contained: npx playwright test -c playwright.ride-ai-dispatch.config.js
 * Or manual: backend :8000 + HALFAPP_ENABLE_RIDE_SIMULATION=1, then default config.
 */
import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

import {
  buildFlowUsers,
  ensureDriverApproved,
  loginUser,
  registerDriver,
  setDriverAvailable,
} from './helpers/rideFlowApi.ts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const screenshotDir = path.join(__dirname, '..', 'test-results', 'ride-ai-dispatch-ui-proof')

async function loginAsDriver(page: import('@playwright/test').Page, token: string) {
  await page.addInitScript(
    ({ driverToken, base }) => {
      sessionStorage.setItem('halfapp_api_base_override', base)
      localStorage.setItem('driver_token', driverToken)
      localStorage.setItem('driver_role', 'driver')
    },
    { driverToken: token, base: '/api' },
  )
  await page.context().grantPermissions(['geolocation'])
  await page.context().setGeolocation({ latitude: 45.5152, longitude: -122.6784 })
  await page.goto('/#/driver')
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 30_000 })
}

async function ensureOnlineIdle(page: import('@playwright/test').Page) {
  await expect(page.getByTestId('cockpit-skeleton')).toBeHidden({ timeout: 30_000 }).catch(() => {})
  const idle = page.getByTestId('sheet-online-idle')
  const simBtn = page.getByTestId('dev-demo-ride-btn')
  if (await idle.isVisible().catch(() => false)) return
  if (await simBtn.isVisible().catch(() => false)) return
  const goOffline = page.getByRole('button', { name: /go offline/i })
  if (await goOffline.first().isVisible().catch(() => false)) return
  const goOnline = page.getByTestId('go-online-btn')
  if (await goOnline.isVisible().catch(() => false)) {
    await goOnline.click({ force: true, timeout: 5_000 }).catch(() => {})
  }
  await expect
    .poll(
      async () => {
        if (await idle.isVisible().catch(() => false)) return true
        if (await simBtn.isVisible().catch(() => false)) return true
        return false
      },
      { timeout: 45_000 },
    )
    .toBe(true)
}

test.describe.configure({ mode: 'serial' })

test.describe('RIDE_AI_DISPATCH_UI_PROOF_01', () => {
  test('simulation ride shows AI panel through match → accept → start → complete', async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000)

    const stamp = Date.now()
    const users = buildFlowUsers(stamp)
    await registerDriver(request, users.driver)
    await ensureDriverApproved(request, users.driver, users.admin)
    const driverToken = await loginUser(request, users.driver.email, users.driver.password)
    await setDriverAvailable(request, driverToken)

    await loginAsDriver(page, driverToken)
    await ensureOnlineIdle(page)

    const simBtn = page.getByTestId('dev-demo-ride-btn')
    if (await simBtn.isVisible().catch(() => false)) {
      await expect(simBtn).toBeEnabled({ timeout: 30_000 })
      await simBtn.click({ timeout: 15_000 })
    } else {
      test.skip(true, 'Simulation controls not visible — set HALFAPP_ENABLE_RIDE_SIMULATION=1')
    }

    await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByTestId('ride-ai-dispatch-panel')).toBeVisible({ timeout: 20_000 })
    const stateEl = page.getByTestId('ride-ai-dispatch-state')
    await expect(stateEl).toContainText(/matched|manual/i)

    await page.screenshot({
      path: path.join(screenshotDir, '01-incoming-match.png'),
      fullPage: true,
    })

    await page.getByTestId('accept-ride-btn').click()
    await expect(stateEl).toContainText(/accepted|manual/i, { timeout: 15_000 })
    const advisory = page.getByTestId('ride-ai-route-advisory-label')
    const groundedMeta = page.getByTestId('ride-ai-meta')
    if (await advisory.isVisible().catch(() => false)) {
      await expect(advisory).toContainText('NOT LIVE TRAFFIC')
    } else if (await groundedMeta.isVisible().catch(() => false)) {
      await expect(groundedMeta).toContainText(/grounded/i)
    }
    await page.screenshot({
      path: path.join(screenshotDir, '02-accepted-route.png'),
      fullPage: true,
    })

    await page.getByTestId('advance-accepted_to_pickup').click()
    await page.getByTestId('advance-arrived_pickup').click()
    await page.getByTestId('advance-in_progress').click()
    await expect(stateEl).toContainText(/complete|in_trip|manual/i, { timeout: 30_000 })
    await page.screenshot({
      path: path.join(screenshotDir, '03-complete.png'),
      fullPage: true,
    })
  })

  test('decline moves AI state off matched without stacking', async ({ page, request }) => {
    test.setTimeout(60_000)
    const stamp = Date.now() + 1
    const users = buildFlowUsers(stamp)
    await registerDriver(request, users.driver)
    await ensureDriverApproved(request, users.driver, users.admin)
    const driverToken = await loginUser(request, users.driver.email, users.driver.password)
    await setDriverAvailable(request, driverToken)

    await loginAsDriver(page, driverToken)
    await ensureOnlineIdle(page)
    const simBtn = page.getByTestId('dev-demo-ride-btn')
    if (!(await simBtn.isVisible().catch(() => false))) {
      test.skip(true, 'Simulation not enabled')
    }
    await expect(simBtn).toBeEnabled({ timeout: 30_000 })
    await simBtn.click({ timeout: 15_000 })
    await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByTestId('ride-ai-dispatch-panel')).toBeVisible({ timeout: 20_000 })

    const stateEl = page.getByTestId('ride-ai-dispatch-state')
    await expect(stateEl).toContainText(/matched|manual/i, { timeout: 10_000 })

    await page.getByTestId('decline-ride-btn').click()
    // AI state flips before the incoming sheet unmounts; do not assert on stateEl after idle.
    await expect
      .poll(async () => (await stateEl.textContent().catch(() => '')) ?? '', { timeout: 8_000 })
      .toMatch(/declined|redispatching/i)

    const idleSheet = page.getByTestId('sheet-online-idle')
    await expect(idleSheet).toBeVisible({ timeout: 20_000 })
    await expect(idleSheet.getByTestId('backend-hide-notice')).toContainText(/Offer declined/i, {
      timeout: 10_000,
    })
    await expect(page.getByTestId('sheet-request-incoming')).toBeHidden()
  })
})
