/**
 * @typedef {'driver' | 'ride_pickup' | 'ride_dropoff' | 'traffic_incident'} ExperimentalMapMarkerKind
 * @typedef {'dev_fixture' | 'backend' | 'device_location'} ExperimentalMapMarkerSource
 *
 * @typedef {Object} ExperimentalMapMarker
 * @property {string} id
 * @property {ExperimentalMapMarkerKind} kind
 * @property {string} label
 * @property {number} latitude
 * @property {number} longitude
 * @property {ExperimentalMapMarkerSource} source
 */

/** Montreal demo basin — matches backend simulation coordinates. */
export const DEV_DRIVER_FIXTURE = {
  id: 'dev-driver',
  kind: 'driver',
  label: 'Driver (dev fixture)',
  latitude: 45.501,
  longitude: -73.567,
  source: 'dev_fixture',
}

/**
 * Build markers for the experimental map layer only (not marketplace truth).
 *
 * @param {Object} input
 * @param {boolean} [input.includeDevDriver]
 * @param {{ lat: number, lng: number } | null} [input.devicePosition] browser geolocation (map only)
 * @param {boolean} [input.usingDevFallback]
 * @param {import('./experimentalMapMarkers.js').ExperimentalMapMarker[]} [input.extraMarkers]
 * @param {Object | null} [input.activeRide] cockpit ride with pickup/dropoff lat-lng
 * @returns {ExperimentalMapMarker[]}
 */
export function buildExperimentalMapMarkers({
  includeDevDriver = false,
  devicePosition = null,
  usingDevFallback = false,
  activeRide = null,
  extraMarkers = [],
}) {
  /** @type {ExperimentalMapMarker[]} */
  const markers = [...extraMarkers]

  if (devicePosition) {
    markers.push({
      id: usingDevFallback ? 'dev-fallback-driver' : 'device-driver',
      kind: 'driver',
      label: 'You',
      latitude: devicePosition.lat,
      longitude: devicePosition.lng,
      source: usingDevFallback ? 'dev_fixture' : 'device_location',
    })
  } else if (includeDevDriver) {
    markers.push({ ...DEV_DRIVER_FIXTURE })
  }

  if (activeRide?.pickup) {
    markers.push({
      id: `ride-${activeRide.rideId}-pickup`,
      kind: 'ride_pickup',
      label: activeRide.pickup.label || 'Pickup',
      latitude: activeRide.pickup.lat,
      longitude: activeRide.pickup.lng,
      source: 'backend',
    })
  }

  if (activeRide?.dropoff) {
    markers.push({
      id: `ride-${activeRide.rideId}-dropoff`,
      kind: 'ride_dropoff',
      label: activeRide.dropoff.label || 'Dropoff',
      latitude: activeRide.dropoff.lat,
      longitude: activeRide.dropoff.lng,
      source: 'backend',
    })
  }

  return markers
}
