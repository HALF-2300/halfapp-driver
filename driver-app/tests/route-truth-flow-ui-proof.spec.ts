import { test, expect } from '@playwright/test'

import {
  buildFlowUsers,
  completeRideViaApi,
  ensureDriverApproved,
  fetchRouteSnapshots,
  loginUser,
  registerDriver,
  registerRiderViaInternal,
} from './helpers/rideFlowApi.ts'

const FORBIDDEN_ROUTING_PHRASES = [
  'production osrm',
  'road-accurate',
  'road accurate',
  'live road network proof',
  'nearest driver',
  'nearest-driver',
]

test.describe('ROUTE_TRUTH_FLOW_UI_PROOF_V0_1', () => {
  test('completed trip audit → route truth expands with estimate label, not_proved claims, technical snapshot proof', async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000)

    const stamp = Date.now()
    const users = buildFlowUsers(stamp)
    await registerDriver(request, users.driver)
    await registerRiderViaInternal(request, users.rider)
    await ensureDriverApproved(request, users.driver, users.admin)
    const driverToken = await loginUser(request, users.driver.email, users.driver.password)
    const riderToken = await loginUser(request, users.rider.email, users.rider.password)

    const rideId = await completeRideViaApi(request, riderToken, driverToken)

    const routePayload = await fetchRouteSnapshots(request, driverToken, rideId)
    expect(routePayload.snapshots.length).toBeGreaterThanOrEqual(1)
    expect(routePayload.route_truth.osrm_runtime_claim).toBe('not_proved')
    expect(routePayload.route_truth.production_routing_claim).toBe('not_proved')
    expect(routePayload.route_truth.used_fallback).toBe(true)
    expect(routePayload.copy?.routing_label).toBe('Straight-line estimate')

    const appApiBase = '/api'
    await page.addInitScript(
      ({ token, base }) => {
        sessionStorage.setItem('halfapp_api_base_override', base)
        localStorage.setItem('driver_token', token)
        localStorage.setItem('driver_role', 'driver')
      },
      { token: driverToken, base: appApiBase }
    )

    await page.goto(`/#/driver/trips/${rideId}/audit`)
    await expect(page.getByTestId('trip-audit-page')).toBeVisible({ timeout: 25_000 })
    await expect(page.getByTestId('trip-audit-route')).toBeVisible()

    const routeSection = page.getByTestId('trip-audit-route')
    await expect(routeSection.getByTestId('route-truth-details')).toBeVisible()

    const routeLoad = page.waitForResponse(
      (res) =>
        res.url().includes(`/drivers/rides/${rideId}/route-snapshots`) &&
        res.request().method() === 'GET' &&
        res.status() === 200,
      { timeout: 30_000 }
    )
    await routeSection.getByTestId('route-truth-details-toggle').click()
    await routeLoad

    const routeBody = routeSection.getByTestId('route-truth-details-body')
    await expect(routeBody).toBeVisible()
    await expect(routeBody.getByTestId('route-truth-routing-label')).toContainText(/Straight-line estimate/i)
    await expect(routeBody.getByTestId('route-truth-osrm-status')).toContainText(/not proved/i)
    await expect(routeBody.getByTestId('route-truth-estimate-note')).toBeVisible()
    await expect(routeBody.getByTestId('route-truth-snapshot-list')).toBeVisible()
    await expect(routeBody.getByTestId('route-truth-snapshot-row').first()).toBeVisible()

    await expect(routeBody.getByTestId('route-truth-technical-body')).not.toBeVisible()
    await routeBody.getByTestId('route-truth-technical-toggle').click()
    await expect(routeBody.getByTestId('route-truth-technical-body')).toBeVisible()
    await expect(routeBody.getByTestId('route-truth-production-claim')).toContainText('not_proved')
    await expect(routeBody.getByTestId('route-truth-snapshot-id').first()).toContainText(/^snapshot #\d+/i)
    await expect(routeBody.getByTestId('route-truth-snapshot-timestamp').first()).not.toHaveText('—')

    const firstSnap = routePayload.snapshots[0]
    if (firstSnap.geometry_hash) {
      await expect(routeBody.getByTestId('route-truth-geometry-hash').first()).toContainText(/^geometry_hash:/)
    }

    const visibleText = (await routeBody.innerText()).toLowerCase()
    for (const phrase of FORBIDDEN_ROUTING_PHRASES) {
      expect(visibleText.includes(phrase), `forbidden routing phrase: ${phrase}`).toBe(false)
    }
  })
})
