import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  GEOLOCATION_STATES,
  geolocationDriverMessage,
  geolocationDiagnosticMessage,
  geolocationStatusMessage,
  isLocationCaptureStale,
  resolveGeolocationPresentation,
} from '../../src/utils/locationTruth.js'

describe('locationTruth', () => {
  it('marks captures older than stale threshold as stale', () => {
    const old = Date.now() - 130_000
    assert.equal(isLocationCaptureStale(old), true)
    assert.equal(isLocationCaptureStale(Date.now()), false)
  })

  it('uses dev fallback when geolocation api missing in dev', () => {
    const result = resolveGeolocationPresentation({
      hasGeolocationApi: false,
      permissionDenied: false,
      permissionUnavailable: false,
      isDev: true,
    })
    assert.equal(result.status, GEOLOCATION_STATES.DEV_FALLBACK)
    assert.equal(result.usingFallback, true)
  })

  it('reports unavailable when geolocation api missing in production', () => {
    const result = resolveGeolocationPresentation({
      hasGeolocationApi: false,
      permissionDenied: false,
      permissionUnavailable: false,
      isDev: false,
    })
    assert.equal(result.status, GEOLOCATION_STATES.UNAVAILABLE)
    assert.equal(result.usingFallback, false)
  })

  it('reports denied without fallback outside dev', () => {
    const result = resolveGeolocationPresentation({
      hasGeolocationApi: true,
      permissionDenied: true,
      permissionUnavailable: false,
      isDev: false,
    })
    assert.equal(result.status, GEOLOCATION_STATES.DENIED)
  })

  it('describes dev fallback honestly in status copy', () => {
    const message = geolocationStatusMessage(GEOLOCATION_STATES.DEV_FALLBACK)
    assert.match(message, /DEV FALLBACK/i)
    assert.match(message, /not real/i)
  })

  it('describes allowed device GPS as map-only not dispatch truth in diagnostics', () => {
    const message = geolocationDiagnosticMessage(GEOLOCATION_STATES.ALLOWED)
    assert.match(message, /map only/i)
    assert.match(message, /not backend dispatch truth/i)
  })

  it('describes requesting state with honest diagnostic copy', () => {
    const message = geolocationDiagnosticMessage(GEOLOCATION_STATES.REQUESTING)
    assert.equal(message, 'Requesting device location...')
  })

  it('uses driver-simple copy on primary surface', () => {
    assert.equal(geolocationDriverMessage(GEOLOCATION_STATES.REQUESTING), 'Finding your location...')
    assert.equal(geolocationDriverMessage(GEOLOCATION_STATES.ALLOWED), 'Location active')
    assert.match(
      geolocationDriverMessage(GEOLOCATION_STATES.ALLOWED, { accuracyMeters: 24 }),
      /Accuracy: 24m/
    )
    assert.equal(geolocationDriverMessage(GEOLOCATION_STATES.DENIED), 'Location unavailable')
  })

  it('keeps geolocationStatusMessage as diagnostic alias', () => {
    const message = geolocationStatusMessage(GEOLOCATION_STATES.ALLOWED)
    assert.match(message, /not backend dispatch truth/i)
  })
})
