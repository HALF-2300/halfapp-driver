import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  GOOGLE_MAPS_DIRECTIONS_BASE,
  buildGoogleMapsNavigationUrl,
  hasNavigationTarget,
  isValidNavigationCoordinate,
} from '../../src/utils/externalNavigation.js'

describe('externalNavigation', () => {
  it('prefers coordinates over address text', () => {
    const url = buildGoogleMapsNavigationUrl({
      lat: 40.7128,
      lng: -74.006,
      label: '123 Main St, New York',
    })
    assert.equal(
      url,
      `${GOOGLE_MAPS_DIRECTIONS_BASE}&destination=40.7128%2C-74.006`
    )
  })

  it('falls back to address label when coordinates are missing', () => {
    const url = buildGoogleMapsNavigationUrl({
      label: 'Simulation Pickup',
    })
    assert.equal(
      url,
      `${GOOGLE_MAPS_DIRECTIONS_BASE}&destination=Simulation%20Pickup`
    )
  })

  it('returns null when no coordinates or address', () => {
    assert.equal(buildGoogleMapsNavigationUrl({}), null)
    assert.equal(buildGoogleMapsNavigationUrl(null), null)
  })

  it('rejects invalid coordinates and falls back to label', () => {
    assert.equal(isValidNavigationCoordinate(999, 0), false)
    assert.equal(
      buildGoogleMapsNavigationUrl({ lat: 999, lng: 0, label: 'Fallback Ave' }),
      `${GOOGLE_MAPS_DIRECTIONS_BASE}&destination=Fallback%20Ave`
    )
    assert.equal(hasNavigationTarget({ lat: 999, lng: 0, label: 'Fallback Ave' }), true)
  })

  it('detects navigation targets from coords or text', () => {
    assert.equal(hasNavigationTarget({ lat: 45.5, lng: -73.5 }), true)
    assert.equal(hasNavigationTarget({ label: 'Montreal' }), true)
    assert.equal(hasNavigationTarget({}), false)
  })
})
