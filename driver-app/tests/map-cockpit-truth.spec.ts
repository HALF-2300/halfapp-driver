import { test, expect } from '@playwright/test'

import { loginDriver } from './helpers/driverLogin.ts'



test.use({ storageState: { cookies: [], origins: [] } })



test.describe('Map-first cockpit truth labels', () => {

  test('map shell is primary surface without verbose proof on idle', async ({ page }) => {

    await loginDriver(page)

    await expect(page.getByTestId('experimental-map-panel')).toBeVisible()

    await expect(page.getByTestId('map-view')).toBeVisible()

    await expect(page.getByTestId('experimental-map-disclaimer')).toBeAttached()

    await expect(page.getByTestId('location-status')).toBeVisible()

    await expect(page.getByTestId('truth-label-backend_owned')).toHaveCount(0)

    await expect(page.getByTestId('cockpit-truth-labels')).toHaveCount(0)

    await expect(page.getByTestId('diagnostics-drawer')).toHaveCount(0)

    await expect(
      page
        .getByTestId('map-region')
        .or(page.getByTestId('marketplace-bottom-sheet'))
        .getByText(/not backend dispatch truth/i)
    ).toHaveCount(0)

  })



  test('diagnostics drawer holds extended truth labels', async ({ page }) => {

    await loginDriver(page)

    await page.getByTestId('diagnostics-toggle').click()

    await expect(page.getByTestId('diagnostics-drawer')).toBeVisible()

    await expect(page.getByTestId('cockpit-truth-labels')).toBeVisible()

    await expect(page.getByTestId('truth-label-experimental')).toBeVisible()

    await expect(page.getByTestId('truth-label-dispatch_backend_owned')).toBeVisible()

    await expect(page.getByTestId('diagnostics-location-copy')).toContainText(
      /map only|dispatch truth|requesting device|DEV FALLBACK/i
    )
    await expect(page.getByTestId('truth-label-no_fare_quote')).toBeVisible()

  })



  test('delayed geolocation shows locating shell then centers on device coords', async ({

    page,

    context,

  }) => {

    await context.setGeolocation({ latitude: 37.7749, longitude: -122.4194 })

    await context.grantPermissions(['geolocation'])



    await page.addInitScript(() => {

      try {

        sessionStorage.clear()

        localStorage.removeItem('halfapp:last-map-viewport')

      } catch {

        /* ignore */

      }

      const coords = {

        latitude: 37.7749,

        longitude: -122.4194,

        accuracy: 5,

        altitude: null,

        altitudeAccuracy: null,

        heading: null,

        speed: null,

      }

      const delayedPosition = {

        coords,

        timestamp: Date.now(),

        toJSON() {

          return this

        },

      }

      const scheduleDelayed = (success, error) => {

        const id = window.setTimeout(() => success(delayedPosition), 2500)

        return id

      }

      navigator.geolocation.watchPosition = scheduleDelayed

      navigator.geolocation.getCurrentPosition = scheduleDelayed

      navigator.geolocation.clearWatch = (id) => {

        window.clearTimeout(id)

      }

    })



    await page.goto('/#/')

    await page.waitForLoadState('domcontentloaded')

    await page.locator('#access input[name="email"]').fill('driver1@example.com')

    await page.locator('#access input[name="password"]').fill('driver123')

    await page.getByTestId('login-submit-btn').click()

    await expect(page.getByTestId('map-home')).toBeVisible({ timeout: 20_000 })



    const mapView = page.getByTestId('map-view')

    await expect(page.getByTestId('map-locating-state')).toBeVisible({ timeout: 5_000 })

    await expect(page.getByTestId('location-status')).toContainText(/finding your location/i)



    const initialLat = await mapView.getAttribute('data-map-center-lat')

    expect(initialLat === '' || initialLat === null || Number(initialLat) !== 45.501).toBeTruthy()



    await expect(mapView).toHaveAttribute('data-map-center-lat', '37.7749', { timeout: 15_000 })

    await expect(mapView).toHaveAttribute('data-map-center-source', 'device_location', {

      timeout: 15_000,

    })

    await expect(page.getByTestId('map-locating-state')).toBeHidden({ timeout: 15_000 })

    await expect(page.getByTestId('location-status')).toContainText(/location active/i)

    await expect(
      page
        .getByTestId('map-region')
        .or(page.getByTestId('marketplace-bottom-sheet'))
        .getByText(/ETA guarantee|nearest driver|route truth|fare truth/i)
    ).toHaveCount(0)

  })



  test('denied geolocation shows honest status without claiming backend GPS', async ({

    page,

    context,

  }) => {

    await context.setGeolocation({ latitude: 0, longitude: 0 })

    await context.clearPermissions()

    await context.grantPermissions([])



    await loginDriver(page)



    const status = page.getByTestId('location-status')

    await expect(status).toBeVisible({ timeout: 15_000 })

    const text = (await status.textContent()) || ''

    expect(text.toLowerCase()).toMatch(/unavailable|finding|locating/)

    await expect(page.getByTestId('truth-label-device_location')).toHaveCount(0)

    await expect(
      page
        .getByTestId('map-region')
        .or(page.getByTestId('marketplace-bottom-sheet'))
        .getByText(/ETA guarantee|nearest driver|route truth|fare truth/i)
    ).toHaveCount(0)

    const mapView = page.getByTestId('map-view')

    const source = await mapView.getAttribute('data-map-center-source')

    if (source === 'dev_fallback') {

      await page.getByTestId('diagnostics-toggle').click()

      await expect(page.getByTestId('diagnostics-dev-fallback-banner')).toBeVisible()

    } else {

      const lat = await mapView.getAttribute('data-map-center-lat')

      expect(lat === '' || lat === null).toBeTruthy()

    }

  })



  test('dev fallback label appears in diagnostics when map uses dev fallback source', async ({

    page,

    context,

  }) => {

    await context.clearPermissions()

    await context.grantPermissions([])



    await loginDriver(page)



    const mapView = page.getByTestId('map-view')

    await expect(mapView).not.toHaveAttribute('data-map-center-source', '', { timeout: 15_000 })

    const source = await mapView.getAttribute('data-map-center-source')

    if (source === 'dev_fallback') {

      await page.getByTestId('diagnostics-toggle').click()

      await expect(page.getByTestId('diagnostics-dev-fallback-banner')).toContainText(

        /DEV FALLBACK LOCATION/i

      )

      await expect(page.getByTestId('diagnostics-dev-fallback-banner')).toContainText(

        /not real driver GPS/i

      )

    } else {
      await expect(page.getByTestId('map-dev-fallback-label')).toHaveCount(0)
      await expect(
        page
          .getByTestId('map-region')
          .or(page.getByTestId('marketplace-bottom-sheet'))
          .getByText(/ETA guarantee|nearest driver|route truth|fare truth/i)
      ).toHaveCount(0)
    }

  })

})


