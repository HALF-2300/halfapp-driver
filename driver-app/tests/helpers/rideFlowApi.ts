import { expect, type APIRequestContext } from '@playwright/test'

export function rideFlowApiBase() {
  const port = process.env.PLAYWRIGHT_RIDE_FLOW_BACKEND_PORT || '8011'
  return `http://127.0.0.1:${port}`
}

export function buildFlowUsers(stamp: number) {
  return {
    driver: {
      name: 'Flow Driver',
      email: `flowdriver+${stamp}@example.com`,
      password: 'FlowDriver1!',
      license_no: `FLD${String(stamp).slice(-8)}`,
      role: 'driver',
    },
    rider: {
      name: 'Flow Rider',
      email: `flowrider+${stamp}@example.com`,
      password: 'FlowRider1!',
      role: 'customer',
    },
    admin: {
      name: 'Flow Admin',
      email: `flowadmin+${stamp}@example.com`,
      password: 'FlowAdmin1!',
      role: 'admin',
    },
  }
}

export async function registerDriver(request: APIRequestContext, user: Record<string, string>) {
  const res = await request.post(`${rideFlowApiBase()}/internal/test-users`, {
    data: {
      email: user.email,
      password: user.password,
      name: user.name,
      role: 'driver',
      license_no: user.license_no,
      driver_approval_status: 'approved',
    },
  })
  expect(res.ok(), await res.text()).toBeTruthy()
}

export async function registerAdmin(request: APIRequestContext, user: Record<string, string>) {
  const res = await request.post(`${rideFlowApiBase()}/internal/test-users`, {
    data: {
      email: user.email,
      password: user.password,
      name: user.name,
      role: 'admin',
    },
  })
  expect(res.ok(), await res.text()).toBeTruthy()
}

/** Rider accounts are created via internal test helper (driver app blocks customer register). */
export async function registerRiderViaInternal(
  request: APIRequestContext,
  user: { email: string; password: string; name: string }
) {
  const res = await request.post(`${rideFlowApiBase()}/internal/test-users`, {
    data: {
      email: user.email,
      password: user.password,
      name: user.name,
      role: 'customer',
    },
  })
  expect(res.ok(), await res.text()).toBeTruthy()
}

export async function loginUser(request: APIRequestContext, email: string, password: string) {
  const res = await request.post(`${rideFlowApiBase()}/internal/test-login`, {
    data: { email, password },
  })
  expect(res.ok(), await res.text()).toBeTruthy()
  const body = await res.json()
  return body.access_token as string
}

async function approveDriverViaAdmin(
  request: APIRequestContext,
  adminToken: string,
  driverEmail: string
) {
  const headers = { Authorization: `Bearer ${adminToken}` }
  const listRes = await request.get(`${rideFlowApiBase()}/admin/drivers`, { headers })
  expect(listRes.ok(), await listRes.text()).toBeTruthy()
  const drivers = (await listRes.json()) as Array<{ id: number; email: string }>
  const driver = drivers.find((row) => row.email === driverEmail)
  expect(driver, `driver ${driverEmail} not found for approval`).toBeTruthy()
  const patchRes = await request.patch(
    `${rideFlowApiBase()}/admin/drivers/${driver!.id}/approval`,
    {
      headers,
      data: { status: 'approved', reason: 'ride_flow_e2e' },
    }
  )
  expect(patchRes.ok(), await patchRes.text()).toBeTruthy()
}

/** Ensure DRIVER-002 approval before presence / dispatch E2E steps. */
export async function ensureDriverApproved(
  request: APIRequestContext,
  driver: Record<string, string>,
  admin: Record<string, string>
) {
  await registerAdmin(request, admin)
  const adminToken = await loginUser(request, admin.email, admin.password)
  await approveDriverViaAdmin(request, adminToken, driver.email)
}

export async function claimTestRide(
  request: APIRequestContext,
  rideId: number,
  driverToken: string
) {
  const res = await request.post(`${rideFlowApiBase()}/drivers/accept-ride/${rideId}`, {
    headers: { Authorization: `Bearer ${driverToken}` },
  })
  expect(res.ok(), await res.text()).toBeTruthy()
}

export async function createRiderTrip(
  request: APIRequestContext,
  riderToken: string,
  customerName = 'UI Flow Rider'
) {
  const res = await request.post(`${rideFlowApiBase()}/rides/`, {
    headers: { Authorization: `Bearer ${riderToken}` },
    data: {
      customer_name: customerName,
      pickup_location: 'Flow Pickup Ave',
      dropoff_location: 'Flow Destination Blvd',
      pickup_latitude: 45.5152,
      pickup_longitude: -122.6784,
      dropoff_latitude: 45.4871,
      dropoff_longitude: -122.8037,
      distance_km: 3.2,
      duration_minutes: 11,
    },
  })
  expect(res.ok()).toBeTruthy()
  return await res.json()
}

export async function fetchRouteSnapshots(
  request: APIRequestContext,
  driverToken: string,
  rideId: number
) {
  const res = await request.get(`${rideFlowApiBase()}/drivers/rides/${rideId}/route-snapshots`, {
    headers: { Authorization: `Bearer ${driverToken}` },
  })
  expect(res.ok(), await res.text()).toBeTruthy()
  return (await res.json()) as {
    ride_id: number
    route_truth: {
      used_fallback?: boolean
      osrm_runtime_claim?: string
      production_routing_claim?: string
    }
    snapshots: Array<{
      id: number
      geometry_hash?: string | null
      created_at?: string
    }>
    copy?: { routing_label?: string }
  }
}

/** Full accept → complete flow via API (for audit / route-truth E2E setup). */
export async function completeRideViaApi(
  request: APIRequestContext,
  riderToken: string,
  driverToken: string,
  options: { tip_cents?: number; toll_cents?: number } = {}
) {
  await setDriverAvailable(request, driverToken)
  const created = await createRiderTrip(request, riderToken)
  const rideId = created.ride.id as number
  const headers = { Authorization: `Bearer ${driverToken}` }
  const accept = await request.post(`${rideFlowApiBase()}/drivers/accept-ride/${rideId}`, { headers })
  expect(accept.ok(), await accept.text()).toBeTruthy()
  const arrive = await request.post(`${rideFlowApiBase()}/drivers/arrive-pickup/${rideId}`, { headers })
  expect(arrive.ok(), await arrive.text()).toBeTruthy()
  const start = await request.post(`${rideFlowApiBase()}/drivers/start-ride/${rideId}`, { headers })
  expect(start.ok(), await start.text()).toBeTruthy()
  const done = await request.post(`${rideFlowApiBase()}/drivers/complete-ride/${rideId}`, {
    headers,
    data: {
      tip_cents: options.tip_cents ?? 300,
      toll_cents: options.toll_cents ?? 100,
      city_fee_cents: 0,
    },
  })
  expect(done.ok(), await done.text()).toBeTruthy()
  return rideId
}

export async function setDriverAvailable(
  request: APIRequestContext,
  driverToken: string,
  coords: { lat: number; lng: number } = { lat: 45.5152, lng: -122.6784 }
) {
  const headers = { Authorization: `Bearer ${driverToken}` }
  const online = await request.patch(`${rideFlowApiBase()}/drivers/me/status`, {
    headers,
    data: { online: true, lat: coords.lat, lng: coords.lng },
  })
  expect(online.ok(), await online.text()).toBeTruthy()
  const res = await request.put(`${rideFlowApiBase()}/drivers/presence`, {
    headers,
    data: { state: 'available' },
  })
  expect(res.ok(), await res.text()).toBeTruthy()
  const heartbeat = await request.post(`${rideFlowApiBase()}/drivers/heartbeat`, { headers })
  expect(heartbeat.ok(), await heartbeat.text()).toBeTruthy()
}
