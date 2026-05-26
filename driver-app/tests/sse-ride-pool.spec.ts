import { expect, test } from '@playwright/test'

import {
  buildFlowUsers,
  claimTestRide,
  createRiderTrip,
  ensureDriverApproved,
  loginUser,
  registerDriver,
  registerRiderViaInternal,
  setDriverAvailable,
} from './helpers/rideFlowApi'

test.describe('SSE ride pool latency', () => {
  async function ensureOnlineIdle(page: import('@playwright/test').Page) {
    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 30_000 })
    const idle = page.getByTestId('sheet-online-idle')
    for (let attempt = 0; attempt < 4; attempt += 1) {
      if (await idle.isVisible().catch(() => false)) return
      if (!(await page.getByTestId('sheet-request-incoming').isVisible().catch(() => false))) break
      await page.getByTestId('decline-ride-btn').click()
      await page.waitForTimeout(500)
    }
    const goOnline = page.getByTestId('go-online-btn')
    if (await goOnline.isVisible().catch(() => false)) {
      await goOnline.click()
    }
    await expect(page.getByTestId('ride-pool')).toBeVisible({ timeout: 45_000 })
    await expect(page.getByTestId('sheet-online-idle')).toBeVisible({ timeout: 45_000 })
  }

  test('ride appears in cockpit via SSE within 2s of creation', async ({ browser, request }) => {
    test.setTimeout(120_000)
    const stamp = Date.now()
    const users = buildFlowUsers(stamp)
    const users2 = buildFlowUsers(stamp + 1)

    await registerDriver(request, users.driver)
    await registerDriver(request, users2.driver)
    await registerRiderViaInternal(request, users.rider)
    await ensureDriverApproved(request, users.driver, users.admin)
    await ensureDriverApproved(request, users2.driver, users2.admin)

    const driverToken = await loginUser(request, users.driver.email, users.driver.password)
    const driver2Token = await loginUser(request, users2.driver.email, users2.driver.password)
    const riderToken = await loginUser(request, users.rider.email, users.rider.password)
    await setDriverAvailable(request, driverToken)
    await setDriverAvailable(request, driver2Token)

    const context = await browser.newContext({
      geolocation: { latitude: 45.5152, longitude: -122.6784 },
      permissions: ['geolocation'],
    })
    const driverPage = await context.newPage()
    await driverPage.addInitScript(
      ({ token, base }) => {
        sessionStorage.setItem('halfapp_api_base_override', base)
        localStorage.setItem('driver_token', token)
        localStorage.setItem('driver_role', 'driver')
      },
      { token: driverToken, base: '/api' }
    )
    await driverPage.goto('/#/driver')
    await ensureOnlineIdle(driverPage)

    const start = Date.now()
    const created = await createRiderTrip(request, riderToken, 'SSE Pool Rider')
    const rideId = created.ride.id as number

    await expect(driverPage.locator(`[data-ride-id="${rideId}"]`)).toBeVisible({ timeout: 2_000 })
    const elapsed = Date.now() - start
    expect(elapsed).toBeLessThan(2_000)

    await claimTestRide(request, rideId, driver2Token)
    await expect(driverPage.locator(`[data-ride-id="${rideId}"]`)).not.toBeVisible({ timeout: 2_000 })

    await context.close()
  })
})
