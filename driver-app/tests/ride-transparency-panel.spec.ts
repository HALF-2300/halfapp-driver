import { test, expect } from '@playwright/test'

test.use({ storageState: { cookies: [], origins: [] } })

test('incoming ride sheet exposes backend transparency panel', async ({ page }) => {
  test.setTimeout(60_000)
  await page.goto('/#/login')
  await page.fill('input[name="email"]', 'driver1@example.com')
  await page.fill('input[name="password"]', 'driver123')
  await page.getByTestId('login-submit-btn').click()
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })

  await page.getByTestId('go-online-btn').click()
  await page.getByTestId('dev-demo-ride-btn').click()
  await expect(page.getByTestId('sheet-request-incoming')).toBeVisible()

  await expect(page.getByTestId('ride-transparency-toggle')).toHaveText(/Why am I seeing this/i)
  await page.getByTestId('ride-transparency-toggle').click()
  await expect(page.getByTestId('ride-transparency-body')).toBeVisible()
  await expect(page.getByText(/Visibility source/i)).toBeVisible()
  await expect(page.getByTestId('ride-transparency-truth-labels')).toBeVisible()
})

test('mock accept conflict surfaces claim conflict notice', async ({ page }) => {
  test.setTimeout(60_000)
  await page.goto('/#/login')
  await page.fill('input[name="email"]', 'driver1@example.com')
  await page.fill('input[name="password"]', 'driver123')
  await page.getByTestId('login-submit-btn').click()
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })

  await page.route('**/drivers/accept-ride/999', async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: {
          detail: 'Ride already claimed',
          ride_id: 999,
          claim_result: 'lost',
          truth_status: 'backend_conflict',
        },
      }),
    })
  })
  const stubRide = {
    id: 999,
    customer_name: 'Conflict Panel Rider',
    status: 'requested',
    pickup_location: 'Mock Pickup',
    destination: 'Mock Dropoff',
    pickup_latitude: 45.501,
    pickup_longitude: -122.681,
    dropoff_latitude: 45.551,
    dropoff_longitude: -122.611,
    fare_amount: 12.5,
    distance_km: 4,
    duration_minutes: 10,
    created_at: null,
    accepted_at: null,
    arrived_pickup_at: null,
    started_at: null,
    completed_at: null,
    cancelled_at: null,
    lifecycle_reason: null,
  }
  await page.route('**/drivers/available-rides', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([stubRide]),
    })
  })
  await page.route('**/drivers/my-rides', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
  await page.route('**/drivers/earnings', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        earnings_summary: {
          today_earnings: 0,
          today_rides: 0,
          total_rides_completed: 0,
        },
      }),
    })
  })

  await page.route('**/drivers/rides/999/transparency', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ride_id: '999',
        driver_id: '1',
        visibility: {
          visible: true,
          source: 'open_board',
          policy_name: 'Ranked Open Board v1',
          reason_codes: ['requested_unassigned_open_board'],
        },
        claim: {
          claimable: false,
          current_status: 'accepted',
          last_claim_result: 'lost',
          truth_status: 'backend_conflict',
          claimed_by_driver_id: '2',
        },
        dismissal: { hidden_for_this_driver: false },
        audit: { ledger_event_ids: ['501', '502'], correlation_id: 'corr-mock' },
        truth_labels: ['BACKEND_OWNED', 'CLAIM_CONFLICT_PROOF'],
      }),
    })
  })

  await page.reload()
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })
  await page.getByTestId('go-online-btn').click()
  await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 })
  await page.getByTestId('accept-ride-btn').click()
  await expect(page.getByTestId('sheet-request-incoming')).toHaveCount(0)
  await expect(page.getByTestId('sheet-online-idle')).toBeVisible({ timeout: 15_000 })
  await expect(page.getByTestId('claim-conflict-notice')).toBeVisible()
  await expect(page.getByTestId('conflict-transparency-memory')).toBeVisible()
  await expect(page.getByText('last_claim_result')).toBeVisible()
  await expect(page.getByText('lost')).toBeVisible()
  await expect(page.getByText('backend_conflict')).toBeVisible()
  await expect(page.getByText('CLAIM_CONFLICT_PROOF')).toBeVisible()
  await expect(page.getByTestId('accept-ride-btn')).toHaveCount(0)
})

test('409 conflict shows honest fallback when transparency fetch fails', async ({ page }) => {
  test.setTimeout(60_000)
  await page.goto('/#/login')
  await page.fill('input[name="email"]', 'driver1@example.com')
  await page.fill('input[name="password"]', 'driver123')
  await page.getByTestId('login-submit-btn').click()
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })

  await page.route('**/drivers/accept-ride/888', async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: {
          detail: 'Ride already claimed',
          ride_id: 888,
          claim_result: 'lost',
          truth_status: 'backend_conflict',
        },
      }),
    })
  })
  await page.route('**/drivers/rides/888/transparency', async (route) => {
    await route.fulfill({ status: 403, contentType: 'application/json', body: '{}' })
  })
  const stubRide = {
    id: 888,
    customer_name: 'Unavailable Transparency Rider',
    status: 'requested',
    pickup_location: 'Mock Pickup',
    destination: 'Mock Dropoff',
    pickup_latitude: 45.501,
    pickup_longitude: -122.681,
    dropoff_latitude: 45.551,
    dropoff_longitude: -122.611,
    fare_amount: null,
    distance_km: 4,
    duration_minutes: 10,
  }
  await page.route('**/drivers/available-rides', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([stubRide]),
    })
  })
  await page.route('**/drivers/my-rides', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
  await page.route('**/drivers/earnings', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        earnings_summary: { today_earnings: 0, today_rides: 0, total_rides_completed: 0 },
      }),
    })
  })

  await page.reload()
  await page.getByTestId('go-online-btn').click()
  await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 })
  await page.getByTestId('accept-ride-btn').click()
  const unavailable = page.getByTestId('conflict-transparency-unavailable')
  await expect(unavailable).toBeVisible({ timeout: 15_000 })
  await expect(unavailable).toContainText('Conflict recorded by backend')
  await expect(unavailable).toContainText('Transparency details unavailable')
})
