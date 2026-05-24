import { expect, test } from '@playwright/test'

import {
  buildFlowUsers,
  createRiderTrip,
  ensureDriverApproved,
  loginUser,
  registerDriver,
  registerRiderViaInternal,
  rideFlowApiBase,
  setDriverAvailable,
} from './helpers/rideFlowApi'

test.describe('SSE ride pool + cockpit session recovery', () => {
  async function ensureOnlineIdle(page: import('@playwright/test').Page) {
    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 30_000 })
    const idle = page.getByTestId('sheet-online-idle')
    if (await idle.isVisible().catch(() => false)) return
    const goOnline = page.getByTestId('go-online-btn')
    if (await goOnline.isVisible().catch(() => false)) {
      await goOnline.click({ force: true })
    }
    await expect
      .poll(
        async () => {
          if (await idle.isVisible().catch(() => false)) return true
          if (await page.getByTestId('sheet-request-incoming').isVisible().catch(() => false)) return true
          return false
        },
        { timeout: 45_000 }
      )
      .toBe(true)
  }

  test('two windows receive new ride quickly via SSE', async ({ browser, request }) => {
    test.setTimeout(120_000)
    const stamp = Date.now()
    const users = buildFlowUsers(stamp)

    await registerDriver(request, users.driver)
    await registerRiderViaInternal(request, users.rider)
    await ensureDriverApproved(request, users.driver, users.admin)
    const driverToken = await loginUser(request, users.driver.email, users.driver.password)
    const riderToken = await loginUser(request, users.rider.email, users.rider.password)
    await setDriverAvailable(request, driverToken)

    const context = await browser.newContext({
      geolocation: { latitude: 45.5152, longitude: -122.6784 },
      permissions: ['geolocation'],
    })
    const pageA = await context.newPage()
    const pageB = await context.newPage()

    for (const page of [pageA, pageB]) {
      await page.addInitScript(
        ({ token, base }) => {
          sessionStorage.setItem('halfapp_api_base_override', base)
          localStorage.setItem('driver_token', token)
          localStorage.setItem('driver_role', 'driver')
        },
        { token: driverToken, base: '/api' }
      )
      await page.goto('/#/driver')
      await ensureOnlineIdle(page)
    }

    const start = Date.now()
    const created = await createRiderTrip(request, riderToken, 'SSE Rider')
    expect(created.ride.status).toBe('requested')

    await Promise.all([
      expect(pageA.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 }),
      expect(pageB.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 }),
    ])
    const elapsed = Date.now() - start
    expect(elapsed).toBeLessThan(15_000)

    await context.close()
  })

  test('hard refresh restores active ride stage', async ({ page, request }) => {
    test.setTimeout(120_000)
    const stamp = Date.now() + 1000
    const users = buildFlowUsers(stamp)

    await registerDriver(request, users.driver)
    await registerRiderViaInternal(request, users.rider)
    await ensureDriverApproved(request, users.driver, users.admin)
    const driverToken = await loginUser(request, users.driver.email, users.driver.password)
    const riderToken = await loginUser(request, users.rider.email, users.rider.password)
    await setDriverAvailable(request, driverToken)

    await page.context().grantPermissions(['geolocation'])
    await page.context().setGeolocation({ latitude: 45.5152, longitude: -122.6784 })
    await page.addInitScript(
      ({ token, base }) => {
        sessionStorage.setItem('halfapp_api_base_override', base)
        localStorage.setItem('driver_token', token)
        localStorage.setItem('driver_role', 'driver')
      },
      { token: driverToken, base: '/api' }
    )

    await page.goto('/#/driver')
    await ensureOnlineIdle(page)

    const created = await createRiderTrip(request, riderToken, 'Recovery Rider')
    const rideId = created.ride.id as number
    expect(rideId).toBeGreaterThan(0)

    await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('accept-ride-btn').click()
    await expect(page.getByTestId('sheet-accepted_to_pickup')).toBeVisible({ timeout: 20_000 })

    await page.reload()
    await expect(page.getByTestId('sheet-accepted_to_pickup')).toBeVisible({ timeout: 20_000 })
    await expect(page.getByTestId('cockpit-resume-notice')).toBeVisible({ timeout: 20_000 })

    await page.getByTestId('advance-accepted_to_pickup').click()
    await expect(page.getByTestId('sheet-arrived_pickup')).toBeVisible({ timeout: 20_000 })
    await page.reload()
    await expect(page.getByTestId('sheet-arrived_pickup')).toBeVisible({ timeout: 20_000 })

    await page.getByTestId('advance-arrived_pickup').click()
    await expect(page.getByTestId('sheet-in_progress')).toBeVisible({ timeout: 20_000 })
    await page.reload()
    await expect(page.getByTestId('sheet-in_progress')).toBeVisible({ timeout: 20_000 })

    const health = await request.get(`${rideFlowApiBase()}/health`)
    expect(health.ok()).toBeTruthy()
  })
})
