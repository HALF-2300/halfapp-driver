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

async function waitForSessionHydration(page: import('@playwright/test').Page) {
  await expect(page.getByTestId('cockpit-skeleton')).toBeHidden({ timeout: 30_000 }).catch(() => {})
}

async function ensureOnlineIdle(page: import('@playwright/test').Page) {
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 30_000 })
  await waitForSessionHydration(page)
  const idle = page.getByTestId('sheet-online-idle')
  if (await idle.isVisible().catch(() => false)) return
  const goOnline = page.getByTestId('go-online-btn')
  // The Go-online button may re-render once or twice while the cockpit settles
  // after hydration (readiness check, marketplace refresh). Retry the click a
  // few times to ride out DOM-detach races without losing test signal.
  for (let attempt = 0; attempt < 4; attempt += 1) {
    if (await idle.isVisible().catch(() => false)) break
    if (!(await goOnline.isVisible().catch(() => false))) break
    try {
      await goOnline.click({ force: true, timeout: 4_000 })
      break
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      if (!/detached|timeout|not attached/i.test(msg)) throw err
      // Re-locate next loop and retry.
      await page.waitForTimeout(250)
    }
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

async function expectActiveSheet(
  page: import('@playwright/test').Page,
  state: (typeof STATES)[number],
  rideId: number
) {
  const sheet = page.getByTestId(SHEET_TEST_ID[state])
  await expect(sheet).toBeVisible({ timeout: 20_000 })
  await expect(sheet).toHaveAttribute('data-cockpit-state', COCKPIT_STATE[state])
  await expect(sheet).toHaveAttribute('data-ride-id', String(rideId))
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
  await expect
    .poll(async () => page.getByTestId('sheet-accepted_to_pickup').isVisible().catch(() => false), {
      timeout: 30_000,
    })
    .toBe(true)
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

      await expectActiveSheet(page, state, ride.id)

      await page.reload()
      await waitForSessionHydration(page)
      await expectActiveSheet(page, state, ride.id)
      await expect(page.getByTestId('cockpit-resume-notice')).toBeVisible({ timeout: 20_000 })
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

    await loginAsDriver(page, driverToken)
    await ensureOnlineIdle(page)
    const ride = await setupRideInState(page, request, 'in_progress', riderToken)

    await page.route('**/drivers/me/active-ride', async (route) => {
      await new Promise((r) => setTimeout(r, 2500))
      await route.continue()
    })

    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect
      .poll(async () => page.getByTestId('cockpit-skeleton').isVisible().catch(() => false), {
        timeout: 5000,
      })
      .toBe(true)
    await expectActiveSheet(page, 'in_progress', ride.id)

    const health = await request.get(`${rideFlowApiBase()}/health`)
    expect(health.ok()).toBeTruthy()
  })
})
