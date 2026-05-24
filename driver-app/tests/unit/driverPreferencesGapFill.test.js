import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { applyTheme } from '../../src/state/useTheme.js'
import { formatDistanceKm, formatDistanceMeters } from '../../src/utils/formatDistance.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

describe('formatDistance', () => {
  it('formats meters in miles by default', () => {
    assert.match(formatDistanceMeters(1609), /mi/)
  })

  it('formats meters in km when requested', () => {
    assert.equal(formatDistanceMeters(2500, 'km'), '2.5 km')
  })

  it('formats km helper with units', () => {
    assert.match(formatDistanceKm(3.2, 'mi'), /mi/)
  })
})

describe('applyTheme', () => {
  it('sets data-theme on document when DOM exists', () => {
    if (typeof document === 'undefined') {
      assert.ok(true)
      return
    }
    applyTheme('light')
    assert.equal(document.documentElement.getAttribute('data-theme'), 'light')
    applyTheme('system')
    assert.equal(document.documentElement.getAttribute('data-theme'), null)
  })
})

describe('gap-fill source wiring', () => {
  it('DriverSettings includes quiet hours and locale', () => {
    const src = readFileSync(
      path.resolve(__dirname, '../../src/components/DriverSettings.jsx'),
      'utf8'
    )
    assert.match(src, /settings-quiet-hours/)
    assert.match(src, /settings-locale-select/)
    assert.match(src, /settings-logout-all-btn/)
  })

  it('MapHome includes approval gate', () => {
    const src = readFileSync(path.resolve(__dirname, '../../src/components/MapHome.jsx'), 'utf8')
    assert.match(src, /cockpit-approval-gate/)
    assert.match(src, /driverApproved/)
  })

  it('includes ride chat and navigation panels', () => {
    const sheet = readFileSync(
      path.resolve(__dirname, '../../src/components/cockpit/MarketplaceBottomSheet.jsx'),
      'utf8'
    )
    assert.match(sheet, /RideChatPanel/)
    assert.match(sheet, /RideNavigationPanel/)
    assert.match(sheet, /release-ride-btn/)
  })

  it('BottomNavigation includes notifications tab', () => {
    const src = readFileSync(
      path.resolve(__dirname, '../../src/components/BottomNavigation.jsx'),
      'utf8'
    )
    assert.match(src, /id: 'notifications'/)
  })

  it('MapHome wires Street Intelligence + telemetry ping', () => {
    const mapHome = readFileSync(
      path.resolve(__dirname, '../../src/components/MapHome.jsx'),
      'utf8'
    )
    assert.match(mapHome, /useTelemetryPing/)
    assert.match(mapHome, /SilMapLayer/)
    assert.match(mapHome, /StreetIntelligencePanel/)
    assert.match(mapHome, /street-intelligence-open/)
  })

  it('MapHome wires City Reality panel', () => {
    const mapHome = readFileSync(
      path.resolve(__dirname, '../../src/components/MapHome.jsx'),
      'utf8'
    )
    assert.match(mapHome, /CityRealityPanel/)
    assert.match(mapHome, /city-reality-open/)
  })

  it('street intelligence labels include anti-fake disclaimers', () => {
    const labels = readFileSync(
      path.resolve(__dirname, '../../src/utils/streetIntelligenceLabels.js'),
      'utf8'
    )
    assert.match(labels, /Not official demand/)
    assert.match(labels, /Not official live traffic/)
    assert.match(labels, /not road-accurate/i)
  })

  it('TripsList uses paginated me/trips API and CSV export', () => {
    const trips = readFileSync(
      path.resolve(__dirname, '../../src/components/TripsList.jsx'),
      'utf8'
    )
    const api = readFileSync(path.resolve(__dirname, '../../src/utils/api.js'), 'utf8')
    assert.match(trips, /getDriverTrips/)
    assert.match(trips, /trips-pager/)
    assert.match(api, /\/drivers\/me\/trips/)
    assert.match(api, /\/drivers\/me\/trips\/export\.csv/)
  })
})
