import { test, expect } from '@playwright/test'

import { loginDriver } from './helpers/driverLogin.ts'

test.use({ storageState: { cookies: [], origins: [] } })

test.describe('v0.1 map foundation', () => {
  test('OSM map loads, can pan, and paid providers stay disabled', async ({ page, context }) => {
    await context.setGeolocation({ latitude: 45.501, longitude: -73.567 })
    await context.grantPermissions(['geolocation'])

    await loginDriver(page)
    await expect(page.getByTestId('map-view')).toBeVisible({ timeout: 30_000 })

    const mapView = page.getByTestId('map-view')
    await expect(mapView).toHaveAttribute('data-route-provider', 'leaflet_osm')
    await expect(mapView).toHaveAttribute('data-traffic-provider', 'none')
    await expect(mapView).toHaveAttribute('data-traffic-aware', 'false')
    await expect(mapView).toHaveAttribute('data-google-fallback', 'false')
    await expect(mapView).toHaveAttribute('data-mapbox-traffic', 'false')

    const leaflet = page.locator('.leaflet-container')
    await expect(leaflet).toBeVisible({ timeout: 15_000 })

    const box = await leaflet.boundingBox()
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
      await page.mouse.down()
      await page.mouse.move(box.x + box.width / 2 + 80, box.y + box.height / 2 + 40, { steps: 6 })
      await page.mouse.up()
    }

    await expect(page.locator('.leaflet-tile-pane img').first()).toBeVisible({ timeout: 15_000 })
  })
})
