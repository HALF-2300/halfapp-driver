import { test, expect } from '@playwright/test'
import {
  buildFlowUsers,
  completeRideViaApi,
  loginUser,
  rideFlowApiBase,
  seedUsers,
} from './helpers/rideFlowApi.ts'

test.describe('RIDER_FLOW_UI_PROOF', () => {
  test('rider UI shows trip complete after driver completes via API', async ({ page, request }) => {
    test.setTimeout(120_000)

    const stamp = Date.now()
    const users = buildFlowUsers(stamp)
    await seedUsers(request, users)
    const riderToken = await loginUser(request, users.rider.email, users.rider.password)
    const driverToken = await loginUser(request, users.driver.email, users.driver.password)

    const rideId = await completeRideViaApi(request, riderToken, driverToken)

    await page.addInitScript(
      ({ token, base }) => {
        localStorage.setItem('rider_token', token)
        localStorage.setItem('rider_role', 'customer')
        sessionStorage.setItem('halfapp_api_base_override', base)
      },
      { token: riderToken, base: '/api' },
    )

    await page.goto(`/#/ride/${rideId}`)
    await expect(page.getByText('Trip complete')).toBeVisible({ timeout: 45_000 })
    await expect(page.getByText(users.driver.name)).toBeVisible()
  })

  test('rider can register, mock geocode, and request ride', async ({ page, request }) => {
    test.setTimeout(120_000)

    const stamp = Date.now()
    const email = `rider_ui_${stamp}@example.com`
    const password = 'RiderUiProof1!'

    await page.route('https://nominatim.openstreetmap.org/**', async (route) => {
      const url = route.request().url()
      const isPickup = url.includes('Pickup')
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            lat: isPickup ? '45.5152' : '45.4871',
            lon: isPickup ? '-122.6784' : '-122.8037',
            display_name: isPickup ? 'Mock Pickup, Portland' : 'Mock Dropoff, Portland',
          },
        ]),
      })
    })

    await page.goto('/#/register')
    await page.locator('input:not([type="password"]):not([type="email"])').first().fill('UI Proof Rider')
    await page.locator('input[type="email"]').fill(email)
    await page.locator('input[type="password"]').fill(password)
    await page.getByRole('button', { name: /create account/i }).click()
    await expect(page.getByText('Get a ride')).toBeVisible({ timeout: 30_000 })

    await page.getByPlaceholder('Enter pickup address').fill('Mock Pickup Portland')
    await page.getByPlaceholder('Enter destination').fill('Mock Dropoff Portland')
    await page.getByRole('button', { name: /confirm addresses/i }).click()
    await expect(page.getByTestId('fare-estimate')).toBeVisible({ timeout: 20_000 })

    const createRes = page.waitForResponse(
      (res) =>
        res.url().includes('/rides/') &&
        res.request().method() === 'POST' &&
        res.status() === 200,
      { timeout: 30_000 },
    )
    await page.getByTestId('request-ride-btn').click()
    await createRes

    await expect(page.getByText(/finding your driver/i)).toBeVisible({ timeout: 20_000 })

    const health = await request.get(`${rideFlowApiBase()}/health`)
    expect(health.ok()).toBeTruthy()
  })
})
