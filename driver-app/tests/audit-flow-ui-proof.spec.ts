import { test, expect } from '@playwright/test'

import {
  buildFlowUsers,
  completeRideViaApi,
  ensureDriverApproved,
  loginUser,
  registerDriver,
  registerRiderViaInternal,
  rideFlowApiBase,
} from './helpers/rideFlowApi.ts'

const FORBIDDEN_PAYMENT_PHRASES = [
  'paid out',
  'payment processed',
  'payout sent',
  'deposited',
  'cash out',
  'wallet',
  'available balance',
  'instant pay',
  'bank settled',
  'stripe',
]

test.describe('AUDIT_FLOW_UI_PROOF_V0_1', () => {
  test('completed trip → trip audit receipt with obligation, pricing, route truth, technical proof', async ({
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

    const rideId = await completeRideViaApi(request, riderToken, driverToken, {
      tip_cents: 400,
      toll_cents: 200,
    })

    const auditApi = await request.get(`${rideFlowApiBase()}/drivers/rides/${rideId}/audit`, {
      headers: { Authorization: `Bearer ${driverToken}` },
    })
    expect(auditApi.ok(), await auditApi.text()).toBeTruthy()
    const auditBody = await auditApi.json()
    expect(auditBody.copy?.payment_execution).toBe('not_implemented')
    expect(String(auditBody.copy?.driver_payment_label || '').toLowerCase()).toContain('obligation')

    const appApiBase = '/api'
    await page.addInitScript(
      ({ token, base }) => {
        sessionStorage.setItem('halfapp_api_base_override', base)
        localStorage.setItem('driver_token', token)
        localStorage.setItem('driver_role', 'driver')
      },
      { token: driverToken, base: appApiBase }
    )

    const tripsLoad = page.waitForResponse(
      (res) =>
        res.url().includes('/drivers/my-rides') &&
        res.request().method() === 'GET' &&
        res.status() === 200,
      { timeout: 45_000 }
    )

    await page.goto('/#/driver/trips')
    await expect(page.getByTestId('trips-screen')).toBeVisible({ timeout: 25_000 })
    await tripsLoad
    await expect(page.getByTestId('trips-list')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('trip-row').first()).toBeVisible()

    const auditNav = page.waitForResponse(
      (res) =>
        res.url().includes(`/drivers/rides/${rideId}/audit`) &&
        res.request().method() === 'GET' &&
        res.status() === 200,
      { timeout: 30_000 }
    )
    await page.getByTestId('trip-audit-link').first().click()
    await auditNav

    await expect(page.getByTestId('trip-audit-page')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('trip-audit-body')).toBeVisible()

    const obligation = page.getByTestId('trip-audit-obligation-label')
    await expect(obligation).toBeVisible()
    await expect(obligation).toContainText(/Recorded obligation/i)

    await expect(page.getByTestId('trip-audit-pricing')).toBeVisible()
    await expect(page.getByTestId('trip-audit-pricing').getByTestId('ride-payout-summary')).toBeVisible()
    await expect(page.getByTestId('trip-audit-pricing').getByTestId('pricing-financial-locked')).toBeVisible()
    await expect(page.getByTestId('rider-platform-service-fee')).toContainText('$1.50')

    await page.getByTestId('trip-audit-route').getByTestId('route-truth-details-toggle').click()
    await expect(page.getByTestId('route-truth-details-body')).toBeVisible()
    await expect(page.getByTestId('route-truth-osrm-status')).toContainText(/not proved/i)

    await expect(page.getByTestId('trip-audit-technical-body')).not.toBeVisible()
    await page.getByTestId('trip-audit-technical-toggle').click()
    await expect(page.getByTestId('trip-audit-technical-body')).toBeVisible()
    await expect(page.getByTestId('trip-audit-payment-execution')).toContainText('not_implemented')

    const hashRow = page.getByTestId('trip-audit-event-hash')
    if ((await hashRow.count()) > 0) {
      await expect(hashRow.first()).toContainText(/^hash:/)
    }

    const visibleText = (await page.getByTestId('trip-audit-body').innerText()).toLowerCase()
    for (const phrase of FORBIDDEN_PAYMENT_PHRASES) {
      expect(visibleText.includes(phrase), `forbidden phrase on audit page: ${phrase}`).toBe(false)
    }
  })
})
