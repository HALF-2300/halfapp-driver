import { test, expect } from '@playwright/test'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

import {
  buildFlowUsers,
  createRiderTrip,
  ensureDriverApproved,
  loginUser,
  registerDriver,
  registerRiderViaInternal,
  rideFlowApiBase,
  setDriverAvailable,
} from './helpers/rideFlowApi.ts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const screenshotDir = path.join(__dirname, '..', 'test-results', 'ride-flow-ui-proof')

/** Trip details are collapsed on the map-first cockpit; expand before pricing assertions. */
async function ensureTripPricingVisible(page: import('@playwright/test').Page) {
  const toggle = page.getByTestId('trip-truth-details-toggle').first()
  const summary = page.getByTestId('ride-payout-summary')
  if (!(await summary.isVisible())) {
    await toggle.click()
    await expect(page.getByTestId('trip-truth-details-body')).toBeVisible()
  }
  await expect(summary).toBeVisible()
}

test.describe('RIDE_FLOW_UI_PROOF_V0_2', () => {
  test('rider request → driver accept → start → complete with locked payout summary', async ({
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

    const openedUrls: string[] = []
    await page.exposeFunction('recordOpenedUrl', (url: string) => {
      openedUrls.push(url)
    })
    await page.addInitScript(() => {
      window.open = ((url: string | URL | undefined) => {
        const href = typeof url === 'string' ? url : url?.toString() ?? ''
        ;(window as unknown as { recordOpenedUrl?: (u: string) => void }).recordOpenedUrl?.(href)
        return null
      }) as typeof window.open
    })

    const apiBase = rideFlowApiBase()
    const appApiBase = '/api'
    await setDriverAvailable(request, driverToken)

    await page.addInitScript(
      ({ token, base }) => {
        sessionStorage.setItem('halfapp_api_base_override', base)
        localStorage.setItem('driver_token', token)
        localStorage.setItem('driver_role', 'driver')
      },
      { token: driverToken, base: appApiBase }
    )

    await page.context().grantPermissions(['geolocation'])
    await page.context().setGeolocation({ latitude: 45.5152, longitude: -122.6784 })

    const cockpitLoad = page.waitForResponse(
      (res) =>
        res.url().includes('/drivers/me/status') &&
        res.request().method() === 'GET' &&
        res.status() === 200,
      { timeout: 45_000 }
    )

    await page.goto('/#/driver')
    const health = await request.get(`${apiBase}/health`)
    expect(health.ok()).toBeTruthy()

    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 25_000 })
    await cockpitLoad
    await expect(page.getByTestId('sheet-online-idle')).toBeVisible({ timeout: 45_000 })

    const created = await createRiderTrip(request, riderToken, 'Proof Rider')
    const rideId = created.ride.id as number
    expect(created.ride.status).toBe('requested')

    await page.waitForResponse(
      (res) =>
        res.url().includes('/drivers/available-rides') &&
        res.request().method() === 'GET' &&
        res.status() === 200,
      { timeout: 15_000 }
    )
    await expect(page.getByTestId('sheet-request-incoming')).toBeVisible({ timeout: 15_000 })
    await ensureTripPricingVisible(page)
    await expect(page.getByTestId('rider-platform-service-fee')).toContainText('$1.50')
    await expect(page.getByTestId('open-pickup-google-maps')).toBeVisible()
    await expect(page.locator('iframe[src*="google"]')).toHaveCount(0)

    await page.getByTestId('open-pickup-google-maps').click()
    await expect.poll(() => openedUrls.length).toBeGreaterThan(0)
    expect(openedUrls[openedUrls.length - 1]).toMatch(/^https:\/\/www\.google\.com\/maps\/dir\/\?api=1&destination=/)

    const acceptResponse = page.waitForResponse(
      (res) =>
        res.url().includes('/drivers/accept-ride/') &&
        res.request().method() === 'POST' &&
        res.status() === 200,
      { timeout: 30_000 }
    )
    await page.getByTestId('accept-ride-btn').click()
    await acceptResponse
    await expect(page.getByTestId('sheet-accepted_to_pickup')).toBeVisible({ timeout: 20_000 })
    await ensureTripPricingVisible(page)
    await expect(page.getByTestId('map-view')).toHaveAttribute(
      'data-route-provider',
      /leaflet_osm|current_or_osrm|osrm_self_hosted|haversine_fallback/
    )
    await expect(page.getByTestId('map-view')).toHaveAttribute('data-traffic-provider', /disabled|none/)
    await expect(page.getByTestId('map-view')).toHaveAttribute('data-google-fallback', 'false')

    await page.getByTestId('advance-accepted_to_pickup').click()
    await expect(page.getByTestId('sheet-arrived_pickup')).toBeVisible()
    await page.getByTestId('advance-arrived_pickup').click()
    await expect(page.getByTestId('sheet-in_progress')).toBeVisible()

    await page.route('**/drivers/complete-ride/**', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue()
        return
      }
      const headers = route.request().headers()
      await route.continue({
        headers,
        postData: JSON.stringify({
          tip_cents: 400,
          toll_cents: 200,
          city_fee_cents: 0,
        }),
      })
    })

    await page.getByTestId('advance-in_progress').click()
    await page.waitForResponse(
      (res) =>
        res.url().includes('/drivers/complete-ride/') &&
        res.request().method() === 'POST' &&
        res.status() === 200,
      { timeout: 20_000 }
    )
    const completedSummary = page.getByTestId('ride-flow-completed-summary')
    await expect(completedSummary).toBeVisible({ timeout: 20_000 })
    await expect(completedSummary.getByTestId('pricing-financial-locked')).toBeVisible()
    await expect(completedSummary.getByTestId('rider-ride-fare')).toBeVisible()
    await expect(completedSummary.getByTestId('rider-platform-commission')).toBeVisible()
    await expect(completedSummary.getByTestId('rider-platform-service-fee')).toContainText('$1.50')
    await expect(completedSummary.getByTestId('driver-total-payout')).toBeVisible()

    fs.mkdirSync(screenshotDir, { recursive: true })
    const screenshotPath = path.join(screenshotDir, 'completed-payout-summary.png')
    await page.screenshot({ path: screenshotPath, fullPage: true })
    await expect(fs.existsSync(screenshotPath)).toBeTruthy()

    let completed: {
      id: number
      status: string
      pricing?: Record<string, unknown>
      route_provider?: string
      traffic_provider?: string
      traffic_aware?: boolean
    } | undefined
    await expect
      .poll(
        async () => {
          const res = await request.get(`${rideFlowApiBase()}/drivers/my-rides`, {
            headers: { Authorization: `Bearer ${driverToken}` },
          })
          if (!res.ok()) return null
          const rides = (await res.json()) as Array<{
            id: number
            status: string
            pricing?: Record<string, unknown>
            route_provider?: string
            traffic_provider?: string
            traffic_aware?: boolean
          }>
          completed = rides.find((r) => r.id === rideId)
          return completed?.status ?? null
        },
        { message: `ride ${rideId} not completed in /drivers/my-rides`, timeout: 15_000 }
      )
      .toBe('completed')
    expect(completed).toBeTruthy()
    expect(completed?.pricing?.financial_locked).toBe(true)
    expect(completed?.pricing?.platform_service_fee_cents).toBe(150)
    expect(completed?.pricing?.tip_cents).toBe(400)
    expect(completed?.pricing?.toll_cents).toBe(200)
    expect(completed?.pricing?.driver_shareable_fare_cents).toBeGreaterThan(0)
    const shareable = completed.pricing.driver_shareable_fare_cents as number
    const commission = completed.pricing.platform_commission_cents as number
    expect(commission).toBe(Math.round((shareable * 2000) / 10000))
    expect(completed.pricing.driver_total_payout_cents).toBe(
      (completed.pricing.driver_ride_payout_cents ?? completed.pricing.driver_commission_cents) + 400
    )
    expect(completed.pricing.customer_total_cents).toBe(shareable + 150 + 400 + 200)
    expect(completed?.route_provider).toMatch(
      /leaflet_osm|current_or_osrm|osrm_self_hosted|haversine_fallback/
    )
    expect(['disabled', 'none']).toContain(completed?.traffic_provider)
    expect(completed?.traffic_aware).toBe(false)

    const presenceBefore = await request.get(`${rideFlowApiBase()}/drivers/me/status`, {
      headers: { Authorization: `Bearer ${driverToken}` },
    })
    const presenceBody = await presenceBefore.json()
    expect(presenceBody.online).toBe(true)

    await page.reload()
    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 25_000 })
    const completedAfterReload = page.getByTestId('ride-flow-completed-summary')
    await expect(completedAfterReload).toBeVisible({ timeout: 20_000 })
    await expect(completedAfterReload.getByTestId('pricing-financial-locked')).toBeVisible()
    await expect(completedAfterReload.getByTestId('rider-platform-service-fee')).toContainText('$1.50')

    const presenceAfter = await request.get(`${rideFlowApiBase()}/drivers/me/status`, {
      headers: { Authorization: `Bearer ${driverToken}` },
    })
    const presenceAfterBody = await presenceAfter.json()
    expect(presenceAfterBody.online).toBe(true)
  })
})

