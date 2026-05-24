import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  isLegacyUnrelatedDefaultCenter,
  LEGACY_UNRELATED_DEFAULT_CENTER,
  MAP_CENTER_SOURCES,
  resolveMapCenterPresentation,
} from '../../src/utils/mapCenterPresentation.js'
import { GEOLOCATION_STATES } from '../../src/utils/locationTruth.js'

describe('mapCenterPresentation', () => {
  it('flags legacy Montreal default as unrelated', () => {
    assert.equal(
      isLegacyUnrelatedDefaultCenter(
        LEGACY_UNRELATED_DEFAULT_CENTER.lat,
        LEGACY_UNRELATED_DEFAULT_CENTER.lng
      ),
      true
    )
    assert.equal(isLegacyUnrelatedDefaultCenter(37.7749, -122.4194), false)
  })

  it('uses neutral locating shell while requesting without unrelated center', () => {
    const result = resolveMapCenterPresentation({
      geoStatus: GEOLOCATION_STATES.REQUESTING,
      devicePosition: null,
      markers: [],
      cachedViewport: {
        latitude: LEGACY_UNRELATED_DEFAULT_CENTER.lat,
        longitude: LEGACY_UNRELATED_DEFAULT_CENTER.lng,
        zoom: 12,
      },
    })
    assert.equal(result.showLocatingOverlay, true)
    assert.equal(result.showMapCanvas, false)
    assert.equal(result.mapCenter, null)
    assert.equal(result.centerSource, MAP_CENTER_SOURCES.NONE)
  })

  it('centers on device coordinates when allowed', () => {
    const result = resolveMapCenterPresentation({
      geoStatus: GEOLOCATION_STATES.ALLOWED,
      devicePosition: { lat: 37.7749, lng: -122.4194 },
      markers: [
        {
          id: 'device-driver',
          kind: 'driver',
          label: 'You',
          latitude: 37.7749,
          longitude: -122.4194,
          source: 'device_location',
        },
      ],
    })
    assert.equal(result.showLocatingOverlay, false)
    assert.equal(result.showMapCanvas, true)
    assert.equal(result.mapCenter?.lat, 37.7749)
    assert.equal(result.centerSource, MAP_CENTER_SOURCES.DEVICE)
  })

  it('uses dev fallback center only after fallback state', () => {
    const result = resolveMapCenterPresentation({
      geoStatus: GEOLOCATION_STATES.DEV_FALLBACK,
      devicePosition: { lat: 45.501, lng: -73.567 },
      usingDevFallback: true,
      markers: [],
    })
    assert.equal(result.centerSource, MAP_CENTER_SOURCES.DEV_FALLBACK)
    assert.equal(result.showLocatingOverlay, false)
    assert.equal(result.showMapCanvas, true)
  })
})
