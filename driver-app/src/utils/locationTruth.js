/** @typedef {'idle' | 'requesting_location' | 'location_allowed' | 'location_denied' | 'location_unavailable' | 'using_dev_fallback_location' | 'location_stale'} GeolocationTruthState */

export const GEOLOCATION_STATES = {
  IDLE: 'idle',
  REQUESTING: 'requesting_location',
  ALLOWED: 'location_allowed',
  DENIED: 'location_denied',
  UNAVAILABLE: 'location_unavailable',
  DEV_FALLBACK: 'using_dev_fallback_location',
  STALE: 'location_stale',
}

/** Montreal demo basin — map preview only, never marketplace truth. */
export const DEV_FALLBACK_COORDINATES = {
  lat: 45.501,
  lng: -73.567,
}

export const LOCATION_STALE_MS = 120_000

/**
 * Driver-facing location copy for the primary cockpit surface.
 *
 * @param {GeolocationTruthState} status
 * @param {{ accuracyMeters?: number }} [opts]
 */
export function geolocationDriverMessage(status, opts = {}) {
  const { accuracyMeters } = opts
  const hasAccuracy = Number.isFinite(accuracyMeters) && accuracyMeters > 0
  switch (status) {
    case GEOLOCATION_STATES.IDLE:
    case GEOLOCATION_STATES.REQUESTING:
      return 'Finding your location...'
    case GEOLOCATION_STATES.ALLOWED:
      return hasAccuracy
        ? `Location active · Accuracy: ${Math.round(accuracyMeters)}m`
        : 'Location active'
    case GEOLOCATION_STATES.STALE:
      return 'Location updating...'
    case GEOLOCATION_STATES.DENIED:
    case GEOLOCATION_STATES.UNAVAILABLE:
      return 'Location unavailable'
    case GEOLOCATION_STATES.DEV_FALLBACK:
      return 'Location unavailable'
    default:
      return 'Locating...'
  }
}

/**
 * Engineering / diagnostics location copy.
 *
 * @param {GeolocationTruthState} status
 * @param {{ usingFallback?: boolean, isDev?: boolean, accuracyMeters?: number, capturedAtMs?: number }} [opts]
 */
export function geolocationDiagnosticMessage(status, opts = {}) {
  const { usingFallback = false, isDev = false, accuracyMeters, capturedAtMs } = opts
  const accuracyNote = Number.isFinite(accuracyMeters)
    ? ` · accuracy ${Math.round(accuracyMeters)}m`
    : ''
  const capturedNote = Number.isFinite(capturedAtMs)
    ? ` · captured ${new Date(capturedAtMs).toISOString()}`
    : ''
  switch (status) {
    case GEOLOCATION_STATES.IDLE:
      return 'Waiting for location permission…'
    case GEOLOCATION_STATES.REQUESTING:
      return 'Requesting device location...'
    case GEOLOCATION_STATES.ALLOWED:
      return `Device location on map only — not backend dispatch truth${accuracyNote}${capturedNote}`
    case GEOLOCATION_STATES.STALE:
      return 'Device location is stale — recenter when updated'
    case GEOLOCATION_STATES.DENIED:
      return isDev && usingFallback
        ? 'Location denied — using dev fallback (not real GPS)'
        : 'Location denied — map uses demo area only'
    case GEOLOCATION_STATES.UNAVAILABLE:
      return isDev && usingFallback
        ? 'Geolocation unavailable — using dev fallback (not real GPS)'
        : 'Geolocation unavailable — map uses demo area only'
    case GEOLOCATION_STATES.DEV_FALLBACK:
      return 'DEV FALLBACK LOCATION — not real driver GPS'
    default:
      return 'Location status unknown'
  }
}

/** @deprecated Use geolocationDiagnosticMessage in diagnostics; geolocationDriverMessage on main UI. */
export function geolocationStatusMessage(status, opts = {}) {
  return geolocationDiagnosticMessage(status, opts)
}

/**
 * @param {number | undefined} capturedAtMs
 * @param {number} [staleAfterMs]
 */
export function isLocationCaptureStale(capturedAtMs, staleAfterMs = LOCATION_STALE_MS) {
  if (!Number.isFinite(capturedAtMs)) return false
  return Date.now() - capturedAtMs > staleAfterMs
}

/**
 * Pure resolution for tests — mirrors hook transitions.
 *
 * @param {{
 *   hasGeolocationApi: boolean,
 *   permissionDenied: boolean,
 *   permissionUnavailable: boolean,
 *   capturedAtMs?: number,
 *   isDev?: boolean,
 * }} input
 * @returns {{ status: GeolocationTruthState, usingFallback: boolean }}
 */
export function resolveGeolocationPresentation(input) {
  const isDev = input.isDev === true
  if (!input.hasGeolocationApi) {
    return isDev
      ? { status: GEOLOCATION_STATES.DEV_FALLBACK, usingFallback: true }
      : { status: GEOLOCATION_STATES.UNAVAILABLE, usingFallback: false }
  }
  if (input.permissionDenied) {
    return isDev
      ? { status: GEOLOCATION_STATES.DEV_FALLBACK, usingFallback: true }
      : { status: GEOLOCATION_STATES.DENIED, usingFallback: false }
  }
  if (input.permissionUnavailable) {
    return isDev
      ? { status: GEOLOCATION_STATES.DEV_FALLBACK, usingFallback: true }
      : { status: GEOLOCATION_STATES.UNAVAILABLE, usingFallback: false }
  }
  if (isLocationCaptureStale(input.capturedAtMs)) {
    return { status: GEOLOCATION_STATES.STALE, usingFallback: false }
  }
  return { status: GEOLOCATION_STATES.ALLOWED, usingFallback: false }
}
