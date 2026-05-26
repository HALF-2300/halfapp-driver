import { test, expect } from '@playwright/test'

test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Driver Portal public face', () => {
  test('root renders driver portal front page, not login card only', async ({ page }) => {
    await page.goto('/#/')
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('driver-portal-hero')).toBeVisible()
    await expect(page.getByTestId('driver-portal-hero').getByText('HalfApp Driver Portal')).toBeVisible()
    await expect(page.getByTestId('driver-portal-capabilities')).toBeVisible()
    const hero = await page.getByTestId('driver-portal-hero').boundingBox()
    const auth = await page.getByTestId('driver-auth-panel').boundingBox()
    expect(hero?.height ?? 0).toBeGreaterThan(120)
    expect(auth?.height ?? 0).toBeGreaterThan(80)
    await expect(page.getByTestId('driver-portal-cockpit-preview')).toBeAttached()
  })

  test('enter driver portal CTA focuses auth', async ({ page }) => {
    await page.goto('/#/')
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('enter-driver-portal-cta').click({ force: true })
    await expect(page.getByTestId('driver-auth-panel')).toBeInViewport()
    await expect(page.getByTestId('auth-tab-signin')).toHaveClass(/active/)
  })

  test('create driver account CTA opens signup', async ({ page }) => {
    await page.goto('/#/')
    await page.getByTestId('create-driver-account-cta').click({ force: true })
    await expect(page.getByTestId('auth-tab-signup')).toHaveClass(/active/)
    await expect(page.getByPlaceholder('Driver license number')).toBeVisible()
  })

  test('driver login reaches cockpit at /driver', async ({ page }) => {
    await page.goto('/#/')
    await page.evaluate(() => {
      try {
        localStorage.clear()
        sessionStorage.clear()
      } catch {
        /* ignore */
      }
    })
    const signIn = page.getByRole('button', { name: 'Sign In' }).first()
    if (await signIn.isVisible()) await signIn.click()
    await page.getByPlaceholder('Email Address').fill('driver1@example.com')
    await page.getByPlaceholder('Password').fill('driver123')
    await page.getByTestId('login-submit-btn').click()
    await expect(page).toHaveURL(/\/driver/, { timeout: 15_000 })
    await expect(page.getByTestId('map-home')).toBeVisible()
  })

  test('public page does not show cockpit diagnostics clutter', async ({ page }) => {
    await page.goto('/#/')
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('diagnostics-drawer')).toHaveCount(0)
    await expect(page.getByTestId('cockpit-truth-labels')).toHaveCount(0)
    await expect(page.getByTestId('dev-demo-ride-btn')).toHaveCount(0)
  })

  test('no rider product surface on driver portal', async ({ page }) => {
    await page.goto('/#/')
    await expect(page.getByText('Ride with HalfApp')).toHaveCount(0)
    await expect(page.getByText('For Riders')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Sign In as Rider/i })).toHaveCount(0)
    await expect(page.getByRole('button', { name: /Rider/i })).toHaveCount(0)
  })

  test('/login shows landing and auth panel is reachable', async ({ page }) => {
    await page.goto('/#/login')
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 })
    await page.locator('#access').scrollIntoViewIfNeeded()
    await expect(page.getByTestId('driver-auth-panel')).toBeInViewport()
  })

  test('protected cockpit redirects to landing when logged out', async ({ page }) => {
    await page.goto('/#/')
    await page.evaluate(() => {
      try {
        localStorage.clear()
        sessionStorage.clear()
      } catch {
        /* ignore */
      }
    })
    await page.goto('/#/driver')
    await expect(page).toHaveURL(/\/(#\/|#)$/, { timeout: 10_000 })
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible()
    await expect(page.getByTestId('map-home')).toHaveCount(0)
  })

  test('invalid session returns to sign in with clear notice', async ({ page }) => {
    await page.route('**/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid token' }),
      })
    })
    await page.addInitScript(() => {
      try {
        localStorage.setItem('driver_token', 'expired-real-token')
        localStorage.setItem('driver_role', 'driver')
      } catch {
        /* ignore */
      }
    })
    await page.goto('/#/driver')
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('auth-error-message')).toContainText(/Session expired or invalid/i)
  })

  test('logout returns to public landing', async ({ page }) => {
    await page.goto('/#/')
    await page.evaluate(() => {
      try {
        localStorage.clear()
        sessionStorage.clear()
      } catch {
        /* ignore */
      }
    })
    await page.locator('#access').scrollIntoViewIfNeeded()
    await page.getByPlaceholder('Email Address').fill('driver1@example.com')
    await page.getByPlaceholder('Password').fill('driver123')
    await page.getByTestId('login-submit-btn').click()
    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('logout-btn').click()
    await expect(page).toHaveURL(/\/(#\/|#)$/, { timeout: 15_000 })
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible()
    await expect(page.getByTestId('auth-session-notice')).toContainText(/Signed out/i)
  })

  test('dev banner does not dominate hero', async ({ page }) => {
    await page.goto('/#/')
    await expect(page.getByTestId('driver-portal-hero')).toBeVisible({ timeout: 15_000 })
    const heroText = await page.getByTestId('driver-portal-hero').innerText()
    expect(heroText).not.toMatch(/DEV MODE/i)
    expect(heroText).not.toMatch(/Hash routing active/i)
    await expect(page.getByTestId('dev-banner')).toBeVisible()
  })
})
