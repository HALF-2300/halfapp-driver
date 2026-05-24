import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  resolveMapSurfaceState,
  shouldShowDevDriverFixturePin,
} from '../../src/utils/mapLocationSurface.js'
import {
  GEOLOCATION_STATES,
  geolocationDiagnosticMessage,
  geolocationDriverMessage,
} from '../../src/utils/locationTruth.js'

describe('initialMapLocation', () => {
  it('shows locating surface while requesting with no markers', () => {
    const result = resolveMapSurfaceState({
      geoStatus: GEOLOCATION_STATES.REQUESTING,
      hasMapCenter: false,
      markerPointCount: 0,
    })
    assert.equal(result.mode, 'locating')
    assert.equal(result.canMountLeaflet, false)
  })

  it('does not use unrelated default city surface when still requesting', () => {
    const locating = resolveMapSurfaceState({
      geoStatus: GEOLOCATION_STATES.REQUESTING,
      hasMapCenter: false,
      markerPointCount: 0,
    })
    assert.notEqual(locating.mode, 'active_map')
  })

  it('mounts active map when device center resolves', () => {
    const result = resolveMapSurfaceState({
      geoStatus: GEOLOCATION_STATES.ALLOWED,
      hasMapCenter: true,
      markerPointCount: 1,
    })
    assert.equal(result.mode, 'active_map')
    assert.equal(result.canMountLeaflet, true)
  })

  it('uses neutral shell when denied without center or ride pins', () => {
    const result = resolveMapSurfaceState({
      geoStatus: GEOLOCATION_STATES.DENIED,
      hasMapCenter: false,
      markerPointCount: 0,
    })
    assert.equal(result.mode, 'neutral')
    assert.equal(result.canMountLeaflet, false)
  })

  it('labels dev fallback honestly in diagnostics', () => {
    const message = geolocationDiagnosticMessage(GEOLOCATION_STATES.DEV_FALLBACK)
    assert.match(message, /DEV FALLBACK LOCATION/i)
    assert.match(message, /not real driver GPS/i)
  })

  it('labels allowed device GPS as map-only not dispatch truth in diagnostics', () => {
    const message = geolocationDiagnosticMessage(GEOLOCATION_STATES.ALLOWED)
    assert.match(message, /map only/i)
    assert.match(message, /not backend dispatch truth/i)
  })

  it('uses finding-your-location copy while requesting on main surface', () => {
    const message = geolocationDriverMessage(GEOLOCATION_STATES.REQUESTING)
    assert.match(message, /finding your location/i)
  })

  it('does not show dev fixture pin while requesting location', () => {
    assert.equal(
      shouldShowDevDriverFixturePin({
        isOnline: true,
        hasActiveRide: false,
        hasDevicePosition: false,
        usingDevFallback: false,
        geoStatus: GEOLOCATION_STATES.REQUESTING,
      }),
      false
    )
  })

  it('shows dev fixture pin only after denied without device position', () => {
    assert.equal(
      shouldShowDevDriverFixturePin({
        isOnline: true,
        hasActiveRide: false,
        hasDevicePosition: false,
        usingDevFallback: false,
        geoStatus: GEOLOCATION_STATES.DENIED,
      }),
      true
    )
  })
})
