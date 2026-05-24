import { test, expect } from '@playwright/test'
import { loginDriver } from './helpers/driverLogin.ts'

test('completed ride shows driver payout, $1.50 service fee, and financial_locked', async ({ page }) => {
  test.setTimeout(60_000)

  await loginDriver(page)
  await page.getByTestId('go-online-btn').click()
  await page.getByTestId('dev-demo-ride-btn').click()
  await page.getByTestId('accept-ride-btn').click()
  await page.getByTestId('advance-accepted_to_pickup').click()
  await page.getByTestId('advance-arrived_pickup').click()
  await page.getByTestId('advance-in_progress').click()

  const flash = page.getByTestId('completed-flash')
  await expect(flash).toBeVisible()
  await expect(flash.getByTestId('driver-ride-payout')).toBeVisible()
  await expect(flash.getByTestId('driver-total-payout')).toBeVisible()
  await expect(flash.getByTestId('rider-platform-service-fee')).toContainText('$1.50')
  await expect(flash.getByTestId('pricing-financial-locked').first()).toBeVisible()
  await expect(flash.getByTestId('driver-tips')).toContainText('$0.00')

  const summary = page.getByTestId('ride-flow-completed-summary')
  await expect(summary).toBeVisible({ timeout: 10_000 })
  await expect(summary.getByTestId('pricing-financial-locked')).toBeVisible()
  await expect(page.getByTestId('open-pickup-google-maps')).toHaveCount(0)
})
