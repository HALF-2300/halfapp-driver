import { GEOLOCATION_STATES } from './locationTruth.js'

/**
 * @typedef {'locating' | 'active_map' | 'neutral'} MapSurfaceMode
 */

/**
 * Pure map surface resolution for first-load geolocation (tests + MapView).
 *
 * @param {{
 *   geoStatus: import('./locationTruth.js').GeolocationTruthState,
 *   hasMapCenter: boolean,
 *   markerPointCount: number,
 * }} input
 * @returns {{ mode: MapSurfaceMode, isLocating: boolean, canMountLeaflet: boolean }}
 */
export function resolveMapSurfaceState({ geoStatus, hasMapCenter, markerPointCount }) {
  const isLocating =
    geoStatus === GEOLOCATION_STATES.REQUESTING || geoStatus === GEOLOCATION_STATES.IDLE

  if (isLocating && markerPointCount === 0) {
    return { mode: 'locating', isLocating: true, canMountLeaflet: false }
  }
  if (hasMapCenter || markerPointCount > 0) {
    return { mode: 'active_map', isLocating: false, canMountLeaflet: true }
  }
  return { mode: 'neutral', isLocating: false, canMountLeaflet: false }
}

/**
 * Dev fixture pin only after geolocation has failed (not while requesting).
 *
 * @param {{
 *   isOnline: boolean,
 *   hasActiveRide: boolean,
 *   hasDevicePosition: boolean,
 *   usingDevFallback: boolean,
 *   geoStatus: import('./locationTruth.js').GeolocationTruthState,
 * }} input
 */
export function shouldShowDevDriverFixturePin(input) {
  if (!input.isOnline || input.hasActiveRide || input.hasDevicePosition || input.usingDevFallback) {
    return false
  }
  if (
    input.geoStatus === GEOLOCATION_STATES.REQUESTING ||
    input.geoStatus === GEOLOCATION_STATES.IDLE
  ) {
    return false
  }
  return (
    input.geoStatus === GEOLOCATION_STATES.DENIED ||
    input.geoStatus === GEOLOCATION_STATES.UNAVAILABLE
  )
}
