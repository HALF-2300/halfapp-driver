import { expect, type APIRequestContext } from '@playwright/test'

export function rideFlowApiBase() {
  const port = process.env.PLAYWRIGHT_RIDER_FLOW_BACKEND_PORT || '8012'
  return `http://127.0.0.1:${port}`
}

export function buildFlowUsers(stamp: number) {
  return {
    driver: {
      name: 'Rider Flow Driver',
      email: `rflowdriver+${stamp}@example.com`,
      password: 'RiderFlowDriver1!',
      license_no: `RFD${String(stamp).slice(-8)}`,
    },
    rider: {
      name: 'Rider Flow Customer',
      email: `rflowrider+${stamp}@example.com`,
      password: 'RiderFlowRider1!',
    },
    admin: {
      name: 'Rider Flow Admin',
      email: `rflowadmin+${stamp}@example.com`,
      password: 'RiderFlowAdmin1!',
    },
  }
}

export async function seedUsers(request: APIRequestContext, users: ReturnType<typeof buildFlowUsers>) {
  for (const payload of [
    { ...users.driver, role: 'driver', driver_approval_status: 'approved' },
    { ...users.rider, role: 'customer' },
    { ...users.admin, role: 'admin' },
  ]) {
    const res = await request.post(`${rideFlowApiBase()}/internal/test-users`, { data: payload })
    expect(res.ok(), await res.text()).toBeTruthy()
  }
}

export async function loginUser(request: APIRequestContext, email: string, password: string) {
  const res = await request.post(`${rideFlowApiBase()}/internal/test-login`, {
    data: { email, password },
  })
  expect(res.ok(), await res.text()).toBeTruthy()
  return (await res.json()).access_token as string
}

export async function setDriverAvailable(request: APIRequestContext, driverToken: string) {
  const headers = { Authorization: `Bearer ${driverToken}` }
  await request.patch(`${rideFlowApiBase()}/drivers/me/status`, {
    headers,
    data: { online: true, lat: 45.5152, lng: -122.6784 },
  })
  await request.put(`${rideFlowApiBase()}/drivers/presence`, {
    headers,
    data: { state: 'available' },
  })
  await request.post(`${rideFlowApiBase()}/drivers/heartbeat`, { headers })
}

export async function completeRideViaApi(
  request: APIRequestContext,
  riderToken: string,
  driverToken: string,
) {
  await setDriverAvailable(request, driverToken)
  const created = await request.post(`${rideFlowApiBase()}/rides/`, {
    headers: { Authorization: `Bearer ${riderToken}` },
    data: {
      customer_name: 'Rider E2E',
      pickup_location: 'E2E Pickup',
      dropoff_location: 'E2E Dropoff',
      pickup_latitude: 45.5152,
      pickup_longitude: -122.6784,
      dropoff_latitude: 45.4871,
      dropoff_longitude: -122.8037,
    },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const rideId = (await created.json()).ride.id as number
  const headers = { Authorization: `Bearer ${driverToken}` }
  for (const path of [
    `/drivers/accept-ride/${rideId}`,
    `/drivers/arrive-pickup/${rideId}`,
    `/drivers/start-ride/${rideId}`,
  ]) {
    const step = await request.post(`${rideFlowApiBase()}${path}`, { headers })
    expect(step.ok(), await step.text()).toBeTruthy()
  }
  const done = await request.post(`${rideFlowApiBase()}/drivers/complete-ride/${rideId}`, {
    headers,
    data: { tip_cents: 0, toll_cents: 0, city_fee_cents: 0 },
  })
  expect(done.ok(), await done.text()).toBeTruthy()
  return rideId
}
