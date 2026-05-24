import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

const trustBackendPort = process.env.PLAYWRIGHT_TRUST_BACKEND_PORT || '8010'
const trustApiOrigin = `http://127.0.0.1:${trustBackendPort}`

function buildUser() {
  const stamp = Date.now()
  return {
    name: 'MockOffUser',
    email: `mockoff+${stamp}@example.com`,
    password: 'PWtest123',
    license_no: `DL${String(stamp).slice(-8)}`,
  }
}

async function registerAndLogin(page: Page) {
  const user = buildUser()
  await page.goto('/#/login')
  await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 })
  await expect(page.getByTestId('mock-mode-banner')).toHaveCount(0)

  await page.getByTestId('auth-tab-signup').click()
  await page.getByPlaceholder('Full Name').fill(user.name)
  await page.getByPlaceholder(/license number/i).fill(user.license_no)
  await page.getByPlaceholder('Email Address').fill(user.email)
  await page.getByPlaceholder('Password').fill(user.password)
  await page.getByTestId('login-submit-btn').click()
  await page.waitForURL(/\/driver/, { timeout: 20_000 })
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })
  return user
}

async function getDriverToken(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem('driver_token'))
  expect(token).toBeTruthy()
  return token as string
}

async function createBackendSimulationRide(request: APIRequestContext, token: string, riderName = 'Trust Simulation Rider') {
  const res = await request.post(`${trustApiOrigin}/drivers/simulate-ride`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      customer_name: riderName,
      pickup_location: 'Backend Seed Pickup',
      destination: 'Backend Seed Dropoff',
      pickup_latitude: 45.501,
      pickup_longitude: -122.681,
      dropoff_latitude: 45.551,
      dropoff_longitude: -122.611,
      distance_km: 6,
      duration_minutes: 14,
    },
  })
  expect(res.ok()).toBeTruthy()
  return await res.json()
}

test.describe('Mock-off + live API contract', () => {
  test('GET /health responds', async ({ request }) => {
    const res = await request.get(`${trustApiOrigin}/health`)
    expect(res.ok()).toBeTruthy()
    const j = await res.json()
    expect(j).toMatchObject({ status: 'ok', service: 'halfapp-backend' })
  })

  test('login screen has no offline mock banner', async ({ page }) => {
    await page.goto('/#/login')
    await expect(page.getByTestId('mock-mode-banner')).toHaveCount(0)
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible()
  })

  test('real register + dashboard shows empty ride pool (no silent mock data)', async ({ page }) => {
    await registerAndLogin(page)
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Offline/i)
    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('sheet-online-idle')).toBeVisible()
    await expect(page.getByTestId('availability-title')).toHaveText(/Available/i)
    await expect(page.getByText('Waiting for requests nearby.')).toBeVisible()
    await expect(page.getByTestId('sheet-request-incoming')).toHaveCount(0)
    await expect(page.getByTestId('mock-mode-banner')).toHaveCount(0)
  })

  test('driver presence is backend-backed and survives reload', async ({ page, request }) => {
    await registerAndLogin(page)
    const token = await getDriverToken(page)
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Offline/i)

    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Online/i)
    const onlinePresence = await request.get(`${trustApiOrigin}/drivers/presence`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(onlinePresence.ok()).toBeTruthy()
    expect((await onlinePresence.json()).state).toBe('available')

    await page.reload()
    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Online/i)

    await page.getByTestId('online-toggle').click()
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Offline/i)
    const offlinePresence = await request.get(`${trustApiOrigin}/drivers/presence`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(offlinePresence.ok()).toBeTruthy()
    expect((await offlinePresence.json()).state).toBe('offline')

    await page.reload()
    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/Offline/i)
  })

  test('cockpit completes a backend-seeded ride and backend trips/earnings update', async ({ page, request }) => {
    await registerAndLogin(page)
    const token = await getDriverToken(page)
    await createBackendSimulationRide(request, token, 'Trust Lifecycle Rider')

    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Trust Lifecycle Rider')).toBeVisible()
    await page.getByTestId('diagnostics-toggle').click()
    await expect(page.getByTestId('truth-label-experimental')).toBeVisible()
    await expect(page.getByTestId('truth-label-dispatch_backend_owned')).toBeVisible()
    await expect(page.getByTestId('ride-sheet-truth-labels')).toHaveCount(0)
    await expect(page.getByTestId('cockpit-truth-labels')).toBeVisible()

    await page.getByTestId('accept-ride-btn').click()
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/To pickup/i)
    await page.getByTestId('advance-accepted_to_pickup').click()
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/At pickup/i)
    await page.getByTestId('advance-arrived_pickup').click()
    await expect(page.getByTestId('driver-state-badge')).toHaveText(/In progress/i)
    await page.getByTestId('advance-in_progress').click()
    await expect(page.getByTestId('completed-flash')).toBeVisible()

    await page.getByTestId('tab-trips').click()
    await expect(page.getByText('Backend completed trips')).toBeVisible()
    await expect(page.getByText('Trust Lifecycle Rider')).toBeVisible()

    await page.getByTestId('tab-earnings').click()
    await expect(page.getByTestId('earnings-total-display')).not.toHaveText('$0.00')
  })

  test('incoming request dismiss is persisted by the backend for that driver', async ({ page, request }) => {
    await registerAndLogin(page)
    const token = await getDriverToken(page)
    const created = await createBackendSimulationRide(request, token, 'Trust Hide Rider')

    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('decline-ride-btn')).toHaveText(/Hide for this driver/i)

    await page.getByTestId('decline-ride-btn').click()
    await expect(page.getByTestId('backend-hide-notice')).toContainText('Dismissed by the backend')
    await expect(page.getByTestId('sheet-request-incoming')).toHaveCount(0)

    await page.getByTestId('sync-marketplace-btn').first().click()
    await expect(page.getByTestId('sheet-request-incoming')).toHaveCount(0)

    const availableAfterHide = await request.get(`${trustApiOrigin}/drivers/available-rides`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(availableAfterHide.ok()).toBeTruthy()
    const hiddenIds = (await availableAfterHide.json()).map((ride: { id: number }) => ride.id)
    expect(hiddenIds).not.toContain(created.ride.id)
  })

  test('localStorage completed trips are not product truth', async ({ page }) => {
    await registerAndLogin(page)
    await page.evaluate(() => {
      localStorage.setItem(
        'halfapp_trips',
        JSON.stringify([
          {
            riderName: 'Fake LocalStorage Rider',
            estimatedFare: 9999,
            completedAt: new Date().toISOString(),
          },
        ]),
      )
    })

    await page.getByTestId('tab-trips').click()
    await expect(page.getByText('No trips yet.')).toBeVisible()
    await expect(page.getByText('Fake LocalStorage Rider')).toHaveCount(0)

    await page.getByTestId('tab-earnings').click()
    await expect(page.getByTestId('earnings-total-display')).toContainText('$0.00')
    await expect(page.getByText('9999')).toHaveCount(0)
  })

  test('earnings shows API-backed zero when no completed rides', async ({ page }) => {
    await registerAndLogin(page)
    await page.getByTestId('tab-earnings').click()
    await expect(page.getByTestId('earnings-screen')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('earnings-total-display')).toContainText('$0.00')
    await expect(page.getByText('$12,458')).toHaveCount(0)
  })

  test('inbox notifications: empty list from API (no fake system cards)', async ({ page }) => {
    await registerAndLogin(page)
    await page.goto('/#/notifications')
    await expect(page.getByRole('heading', { name: 'Inbox' })).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('notifications-empty')).toBeVisible()
    await expect(page.getByText('System Update')).toHaveCount(0)
  })

  test('accept ride failure shows visible error (network stub, not offline mock)', async ({ page }) => {
    await registerAndLogin(page)
    await page.route('**/drivers/available-rides', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 999,
            customer_name: 'ContractTest',
            status: 'requested',
            pickup_location: null,
            destination: null,
            pickup_latitude: 45.501,
            pickup_longitude: -122.681,
            dropoff_latitude: 45.551,
            dropoff_longitude: -122.611,
            fare_amount: null,
            distance_km: null,
            duration_minutes: null,
            created_at: null,
            accepted_at: null,
            arrived_pickup_at: null,
            started_at: null,
            completed_at: null,
            cancelled_at: null,
            lifecycle_reason: null,
          },
        ]),
      })
    })
    await page.route('**/drivers/accept-ride/999', async (route) => {
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Ride already claimed' }),
      })
    })
    await page.reload()
    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('accept-ride-btn').click()
    await expect(page.getByTestId('accept-ride-error')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByTestId('accept-ride-error')).toContainText('Ride already claimed')
  })

  test('messages tab remains explicitly demo', async ({ page }) => {
    await registerAndLogin(page)
    await page.goto('/#/notifications')
    await page.getByTestId('tab-messages').click()
    await expect(page.getByTestId('inbox-messages-demo')).toBeVisible()
  })
})
