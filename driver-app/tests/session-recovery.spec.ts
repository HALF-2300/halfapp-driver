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

const STATES = ['accepted', 'driver_arrived', 'in_progress'] as const

const COCKPIT_STATE: Record<(typeof STATES)[number], string> = {
  accepted: 'accepted',
  driver_arrived: 'driver_arrived',
  in_progress: 'in_progress',
}

const SHEET_TEST_ID: Record<(typeof STATES)[number], string> = {
  accepted: 'sheet-accepted_to_pickup',
  driver_arrived: 'sheet-arrived_pickup',
  in_progress: 'sheet-in_progress',
}

async function loginAsDriver(page: import('@playwright/test').Page, token: string) {
  await page.addInitScript(
    ({ driverToken, base }) => {
      sessionStorage.setItem('halfapp_api_base_override', base)
      localStorage.setItem('driver_token', driverToken)
      localStorage.setItem('driver_role', 'driver')
    },
    { driverToken: token, base: '/api' }
  )
  await page.goto('/#/driver')
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 30_000 })
}

async function ensureOnlineIdle(page: import('@playwright/test').Page) {
  const idle = page.getByTestId('sheet-online-idle')
  if (await idle.isVisible().catch(() => false)) return
  const goOnline = page.getByTestId('go-online-btn')
  if (await goOnline.isVisible().catch(() => false)) {
    await goOnline.click()
  }
  await expect(idle).toBeVisible({ timeout: 45_000 })
}

async function setupRideInState(
  page: import('@playwright/test').Page,
  request: import('@playwright/test').APIRequestContext,
  state: (typeof STATES)[number],
  riderToken: string
) {
  const created = await createRiderTrip(request, riderToken, `Recovery ${state}`)
  const rideId = created.ride.id as number
  await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 20_000 })
  await page.getByTestId('accept-ride-btn').click()
  await expect(page.getByTestId('sheet-accepted_to_pickup')).toBeVisible({ timeout: 20_000 })
  if (state === 'accepted') {
    return { id: rideId }
  }
  await page.getByTestId('advance-accepted_to_pickup').click()
  await expect(page.getByTestId('sheet-arrived_pickup')).toBeVisible({ timeout: 20_000 })
  if (state === 'driver_arrived') {
    return { id: rideId }
  }
  await page.getByTestId('advance-arrived_pickup').click()
  await expect(page.getByTestId('sheet-in_progress')).toBeVisible({ timeout: 20_000 })
  return { id: rideId }
}

test.describe('Cockpit session recovery', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().grantPermissions(['geolocation'])
    await page.context().setGeolocation({ latitude: 45.5152, longitude: -122.6784 })
  })

  for (const state of STATES) {
    test(`cockpit recovers from refresh when ride is in ${state}`, async ({ page, request }) => {
      test.setTimeout(120_000)
      const stamp = Date.now() + STATES.indexOf(state) * 17
      const users = buildFlowUsers(stamp)
      await registerDriver(request, users.driver)
      await registerRiderViaInternal(request, users.rider)
      await ensureDriverApproved(request, users.driver, users.admin)
      const driverToken = await loginUser(request, users.driver.email, users.driver.password)
      const riderToken = await loginUser(request, users.rider.email, users.rider.password)
      await setDriverAvailable(request, driverToken)

      await loginAsDriver(page, driverToken)
      await ensureOnlineIdle(page)
      const ride = await setupRideInState(page, request, state, riderToken)

      await expect(page.locator(`[data-cockpit-state="${COCKPIT_STATE[state]}"]`)).toBeVisible()
      await expect(page.locator(`[data-ride-id="${ride.id}"]`)).toBeVisible()

      await page.reload({ waitUntil: 'networkidle' })

      await expect(page.locator(`[data-cockpit-state="${COCKPIT_STATE[state]}"]`)).toBeVisible({
        timeout: 10_000,
      })
      await expect(page.locator(`[data-ride-id="${ride.id}"]`)).toBeVisible()
      await expect(page.getByTestId(SHEET_TEST_ID[state])).toBeVisible()
    })
  }

  test('cockpit shows skeleton then ride during network delay', async ({ page, request }) => {
    test.setTimeout(120_000)
    const stamp = Date.now() + 5000
    const users = buildFlowUsers(stamp)
    await registerDriver(request, users.driver)
    await registerRiderViaInternal(request, users.rider)
    await ensureDriverApproved(request, users.driver, users.admin)
    const driverToken = await loginUser(request, users.driver.email, users.driver.password)
    const riderToken = await loginUser(request, users.rider.email, users.rider.password)
    await setDriverAvailable(request, driverToken)

    await page.route('**/drivers/me/active-ride', async (route) => {
      await new Promise((r) => setTimeout(r, 1500))
      await route.continue()
    })

    await loginAsDriver(page, driverToken)
    await ensureOnlineIdle(page)
    await setupRideInState(page, request, 'in_progress', riderToken)

    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect(page.getByTestId('cockpit-skeleton')).toBeVisible()
    await expect(page.locator('[data-cockpit-state="in_progress"]')).toBeVisible({ timeout: 10_000 })

    const health = await request.get(`${rideFlowApiBase()}/health`)
    expect(health.ok()).toBeTruthy()
  })
})
