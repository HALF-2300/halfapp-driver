import { test, expect } from '@playwright/test'
import { loginDriver } from './helpers/driverLogin.ts'

/**
 * Smoke test for the driver MVP loop. Verifies one full pass:
 * login → map home → go online → demo ride → accept → arrive → start → complete → trip recorded.
 * Mock auth is used via VITE_ALLOW_OFFLINE_MOCK=true (set by playwright.config.js).
 */
test('driver MVP demo loop end-to-end', async ({ page }) => {
  test.setTimeout(60_000)
  // Only uncaught page errors should fail the suite. The api.js layer emits
  // console.error when the backend is unreachable, which is expected in this
  // offline-mock dev run; those are not real bugs.
  const pageErrors: string[] = []
  page.on('pageerror', (err) => pageErrors.push(`pageerror: ${err.message}`))

  await loginDriver(page)
  await expect(page.getByTestId('driver-state-badge')).toHaveText(/Offline/i)

  // Go online.
  await page.getByTestId('go-online-btn').click()
  await expect(page.getByTestId('driver-state-badge')).toHaveText(/Online/i)

  // Generate demo ride via the dev button.
  await expect(page.getByTestId('dev-demo-ride-btn')).toBeVisible()
  await page.getByTestId('dev-demo-ride-btn').click()
  await expect(page.getByTestId('sheet-request-incoming')).toBeVisible()
  await expect(page.getByTestId('driver-state-badge')).toHaveText(/Incoming/i)
  await expect(page.getByTestId('decline-ride-btn')).toHaveText(/Hide for this driver/i)

  await page.getByTestId('accept-ride-btn').click()
  await expect(page.getByTestId('driver-state-badge')).toHaveText(/To pickup/i)

  await page.getByTestId('advance-accepted_to_pickup').click()
  await expect(page.getByTestId('driver-state-badge')).toHaveText(/At pickup/i)

  await page.getByTestId('advance-arrived_pickup').click()
  await expect(page.getByTestId('driver-state-badge')).toHaveText(/In progress/i)

  await page.getByTestId('advance-in_progress').click()
  await expect(page.getByTestId('completed-flash')).toBeVisible({ timeout: 15_000 })
  await expect(page.getByTestId('driver-state-badge')).toHaveText(/Online/i, { timeout: 15_000 })

  // Trip should appear in Trips list.
  await page.getByTestId('tab-trips').click()
  await expect(page.getByText('Backend completed trips')).toBeVisible()
  await expect(page.getByText('Simulation Rider')).toBeVisible()

  // Earnings should reflect the trip.
  await page.getByTestId('tab-earnings').click()
  await expect(page.getByTestId('earnings-total-display')).not.toHaveText('$0.00', { timeout: 15_000 })

  // Reload should not break the app — should still authed (token in localStorage).
  await page.reload()
  await expect(
    page.getByTestId('map-home').or(page.getByTestId('earnings-screen')).or(page.getByTestId('trips-screen'))
  ).toBeVisible({ timeout: 10_000 })

  expect(pageErrors, pageErrors.join('\n')).toEqual([])
})
