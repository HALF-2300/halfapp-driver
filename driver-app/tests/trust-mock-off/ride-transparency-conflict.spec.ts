import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

const trustBackendPort = process.env.PLAYWRIGHT_TRUST_BACKEND_PORT || '8010'
const trustApiOrigin = `http://127.0.0.1:${trustBackendPort}`

function buildUser(suffix: string) {
  const stamp = `${Date.now()}${suffix}`
  return {
    name: `Trust Driver ${suffix}`,
    email: `trust${suffix}${stamp}@example.com`,
    password: 'PWtest123',
    license_no: `DL${stamp}`.slice(0, 16),
  }
}

async function registerDriverViaApi(request: APIRequestContext, user: ReturnType<typeof buildUser>) {
  const reg = await request.post(`${trustApiOrigin}/auth/register`, {
    data: {
      email: user.email,
      name: user.name,
      password: user.password,
      role: 'driver',
      license_no: user.license_no,
    },
  })
  expect(reg.ok(), await reg.text()).toBeTruthy()
  const body = await reg.json()
  expect(body.access_token).toBeTruthy()
  return body.access_token as string
}

async function openCockpitWithToken(page: Page, token: string) {
  await page.addInitScript((accessToken) => {
    localStorage.setItem('driver_token', accessToken)
    localStorage.setItem('driver_role', 'driver')
  }, token)

  const meResponse = page.waitForResponse(
    (res) => res.url().includes('/auth/me') && res.status() === 200,
    { timeout: 30_000 }
  )
  await page.goto('/#/driver')
  await meResponse
  await expect(page.getByTestId('driver-shell')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 30_000 })
  await expect(page.getByTestId('go-online-btn')).toBeVisible({ timeout: 15_000 })
}

async function seedRide(request: APIRequestContext, token: string) {
  const res = await request.post(`${trustApiOrigin}/drivers/simulate-ride`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      customer_name: 'Two Driver Conflict Rider',
      pickup_location: 'Trust Pickup',
      destination: 'Trust Dropoff',
      pickup_latitude: 45.501,
      pickup_longitude: -122.681,
      dropoff_latitude: 45.551,
      dropoff_longitude: -122.611,
      distance_km: 5,
      duration_minutes: 12,
    },
  })
  expect(res.ok()).toBeTruthy()
  return await res.json()
}

test.describe('Ride transparency and 409 conflict (trust lane)', () => {
  test.describe.configure({ timeout: 120_000, retries: 1 })

  test('driver A sees transparency then loses claim with 409 conflict UI', async ({
    page,
    request,
  }) => {
    const userA = buildUser('A')
    const userB = buildUser('B')
    const tokenA = await registerDriverViaApi(request, userA)
    const tokenB = await registerDriverViaApi(request, userB)

    const created = await seedRide(request, tokenB)
    const rideId = created.ride.id

    await openCockpitWithToken(page, tokenA)

    await page.getByTestId('go-online-btn').click()
    await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Two Driver Conflict Rider')).toBeVisible({ timeout: 10_000 })
    await page.getByTestId('ride-transparency-toggle').click()
    await expect(page.getByTestId('ride-transparency-body')).toBeVisible()
    await expect(page.getByText(/Visibility source/i)).toBeVisible({ timeout: 10_000 })

    await request.put(`${trustApiOrigin}/drivers/presence`, {
      headers: { Authorization: `Bearer ${tokenB}` },
      data: { state: 'available' },
    })
    await request.post(`${trustApiOrigin}/drivers/heartbeat`, {
      headers: { Authorization: `Bearer ${tokenB}` },
    })

    const winnerClaim = await request.post(`${trustApiOrigin}/drivers/accept-ride/${rideId}`, {
      headers: { Authorization: `Bearer ${tokenB}` },
    })
    expect(winnerClaim.ok(), await winnerClaim.text()).toBeTruthy()

    const acceptResponse = page.waitForResponse(
      (res) =>
        res.request().method() === 'POST' &&
        res.url().includes(`/accept-ride/${rideId}`) &&
        res.status() === 409,
      { timeout: 15_000 }
    )
    await page.getByTestId('accept-ride-btn').click()
    const conflictResponse = await acceptResponse
    const conflictBody = await conflictResponse.json()
    expect(conflictBody.detail.claim_result).toBe('lost')
    expect(conflictBody.detail.truth_status).toBe('backend_conflict')
    expect(conflictBody.detail.ride_id).toBe(rideId)

    await expect(page.getByTestId('claim-conflict-notice')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByTestId('claim-conflict-notice')).toHaveAttribute('data-claim-result', 'lost')
    await expect(page.getByTestId('claim-conflict-notice')).toHaveAttribute(
      'data-truth-status',
      'backend_conflict'
    )
    await expect(page.getByText('Job already claimed')).toBeVisible()
    await expect(page.getByText('Another driver accepted this job first.')).toBeVisible()
    await expect(page.getByTestId('sheet-request-incoming')).toHaveCount(0)
  })
})
