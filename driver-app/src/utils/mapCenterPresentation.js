import { DEV_FALLBACK_COORDINATES, GEOLOCATION_STATES } from './locationTruth.js'

/** @typedef {'none' | 'ui_viewport_only' | 'device_location' | 'dev_fallback' | 'markers'} MapCenterSource */

export const MAP_CENTER_SOURCES = {
  NONE: 'none',
  CACHED_VIEWPORT: 'ui_viewport_only',
  DEVICE: 'device_location',
  DEV_FALLBACK: 'dev_fallback',
  MARKERS: 'markers',
}

/** Legacy unrelated default — must never be used as first-load map center. */
export const LEGACY_UNRELATED_DEFAULT_CENTER = {
  lat: DEV_FALLBACK_COORDINATES.lat,
  lng: DEV_FALLBACK_COORDINATES.lng,
}

/**
 * @param {number | undefined} lat
 * @param {number | undefined} lng
 */
export function isLegacyUnrelatedDefaultCenter(lat, lng) {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false
  return (
    Math.abs(lat - LEGACY_UNRELATED_DEFAULT_CENTER.lat) < 0.0001 &&
    Math.abs(lng - LEGACY_UNRELATED_DEFAULT_CENTER.lng) < 0.0001
  )
}

/**
 * @param {import('./experimentalMapMarkers.js').ExperimentalMapMarker[]} markers
 */
function hasRideBoundsMarkers(markers) {
  return markers.some((m) => m.kind === 'ride_pickup' || m.kind === 'ride_dropoff')
}

/**
 * Pure map presentation for tests and MapHome wiring.
 *
 * @param {{
 *   geoStatus: import('./locationTruth.js').GeolocationTruthState,
 *   devicePosition: { lat: number, lng: number } | null,
 *   usingDevFallback?: boolean,
 *   markers?: import('./experimentalMapMarkers.js').ExperimentalMapMarker[],
 *   cachedViewport?: { latitude: number, longitude: number, zoom: number } | null,
 * }} input
 */
export function resolveMapCenterPresentation(input) {
  const {
    geoStatus,
    devicePosition,
    usingDevFallback = false,
    markers = [],
    cachedViewport = null,
  } = input

  if (hasRideBoundsMarkers(markers)) {
    const pickup = markers.find((m) => m.kind === 'ride_pickup')
    return {
      showLocatingOverlay: false,
      showMapCanvas: true,
      mapCenter: pickup
        ? { lat: pickup.latitude, lng: pickup.longitude, zoom: 13 }
        : null,
      centerSource: MAP_CENTER_SOURCES.MARKERS,
    }
  }

  const isAwaitingDevice =
    geoStatus === GEOLOCATION_STATES.REQUESTING || geoStatus === GEOLOCATION_STATES.IDLE

  if (isAwaitingDevice) {
    return {
      showLocatingOverlay: true,
      showMapCanvas: false,
      mapCenter: null,
      centerSource: MAP_CENTER_SOURCES.NONE,
    }
  }

  if (
    (geoStatus === GEOLOCATION_STATES.ALLOWED || geoStatus === GEOLOCATION_STATES.STALE) &&
    devicePosition
  ) {
    return {
      showLocatingOverlay: false,
      showMapCanvas: true,
      mapCenter: { lat: devicePosition.lat, lng: devicePosition.lng, zoom: 14 },
      centerSource: MAP_CENTER_SOURCES.DEVICE,
    }
  }

  if (geoStatus === GEOLOCATION_STATES.DEV_FALLBACK && devicePosition && usingDevFallback) {
    return {
      showLocatingOverlay: false,
      showMapCanvas: true,
      mapCenter: { lat: devicePosition.lat, lng: devicePosition.lng, zoom: 12 },
      centerSource: MAP_CENTER_SOURCES.DEV_FALLBACK,
    }
  }

  return {
    showLocatingOverlay: false,
    showMapCanvas: false,
    mapCenter: null,
    centerSource: MAP_CENTER_SOURCES.NONE,
  }
}

/**
 * Short driver-facing map status (primary surface).
 *
 * @param {MapCenterSource} centerSource
 */
export function mapLocationDriverLabel(centerSource) {
  if (centerSource === MAP_CENTER_SOURCES.DEVICE) return 'Location active'
  if (centerSource === MAP_CENTER_SOURCES.DEV_FALLBACK) return 'Location active'
  if (centerSource === MAP_CENTER_SOURCES.MARKERS) return 'Ride on map'
  if (centerSource === MAP_CENTER_SOURCES.CACHED_VIEWPORT) return 'Finding your location...'
  return 'Finding your location...'
}

/**
 * Engineering / diagnostics map source copy.
 *
 * @param {MapCenterSource} centerSource
 * @param {import('./experimentalMapMarkers.js').ExperimentalMapMarker[]} markers
 */
export function mapLocationDiagnosticLabel(centerSource, markers = []) {
  return mapLocationSourceLabel(centerSource, markers)
}

/**
 * @param {MapCenterSource} centerSource
 * @param {import('./experimentalMapMarkers.js').ExperimentalMapMarker[]} markers
 */
export function mapLocationSourceLabel(centerSource, markers = []) {
  if (centerSource === MAP_CENTER_SOURCES.DEV_FALLBACK) {
    return 'DEV FALLBACK LOCATION — not real driver GPS'
  }
  if (centerSource === MAP_CENTER_SOURCES.DEVICE) {
    return 'Device location on map only — not backend dispatch truth'
  }
  if (centerSource === MAP_CENTER_SOURCES.CACHED_VIEWPORT) {
    return 'Last map viewport (UI only) — requesting device location…'
  }
  const hasDevFallback = markers.some((m) => m.id === 'dev-fallback-driver')
  if (hasDevFallback) {
    return 'DEV FALLBACK LOCATION — not real driver GPS'
  }
  const hasDevice = markers.some((m) => m.source === 'device_location')
  if (hasDevice && !markers.some((m) => m.kind.startsWith('ride_'))) {
    return 'Device location on map only — not backend dispatch truth'
  }
  if (centerSource === MAP_CENTER_SOURCES.MARKERS) {
    return 'Ride pins: backend coordinates (visualization only)'
  }
  return 'Map canvas — awaiting device location'
}
