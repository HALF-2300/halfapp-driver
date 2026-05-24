/**
 * v0.1 map provider abstraction — Leaflet/OSM default; Google/Mapbox off unless env enables.
 */

const env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {}

export const MAP_DISPLAY_PROVIDER =
  env.VITE_MAP_DISPLAY_PROVIDER || 'carto_voyager'
export const ROUTING_PROVIDER = env.VITE_ROUTING_PROVIDER || 'current_or_osrm'
export const TRAFFIC_PROVIDER = env.VITE_TRAFFIC_PROVIDER || 'none'
export const TRAFFIC_SIGNALS_ENABLED =
  String(env.VITE_TRAFFIC_SIGNALS_ENABLED || 'false').toLowerCase() === 'true'
export const GOOGLE_MAPS_FALLBACK_ENABLED =
  String(env.VITE_GOOGLE_MAPS_FALLBACK_ENABLED || 'false').toLowerCase() === 'true'
export const MAPBOX_TRAFFIC_ENABLED =
  String(env.VITE_MAPBOX_TRAFFIC_ENABLED || 'false').toLowerCase() === 'true'

let externalCallCount = 0

export function getMapDisplayConfig() {
  const useCartoVoyager = String(MAP_DISPLAY_PROVIDER).toLowerCase().includes('carto_voyager')
  return {
    provider: MAP_DISPLAY_PROVIDER,
    tileUrl: useCartoVoyager
      ? 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png'
      : 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: useCartoVoyager
      ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
      : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }
}

export function getRouteStyle() {
  return {
    color: '#38bdf8',
    weight: 4,
    opacity: 0.85,
    dashArray: null,
    lineCap: 'round',
  }
}

/** @returns {Promise<{ lat: number, lng: number, label?: string }[]>} */
export async function geocode(query, { signal } = {}) {
  if (!query || String(query).trim().length < 3) return []
  if (GOOGLE_MAPS_FALLBACK_ENABLED) {
    throw new Error('Google geocode fallback is disabled in v0.1')
  }
  externalCallCount += 1
  return []
}

export async function reverseGeocode(lat, lng) {
  if (GOOGLE_MAPS_FALLBACK_ENABLED) {
    throw new Error('Google reverse geocode fallback is disabled in v0.1')
  }
  return { lat, lng, label: `${lat.toFixed(5)}, ${lng.toFixed(5)}` }
}

/**
 * Placeholder route — chord/visual until backend route snapshots ship.
 * @returns {Promise<{ distanceKm: number, durationMinutes: number, polyline: [number, number][], routeProvider: string, trafficProvider: string, trafficAware: boolean, routeConfidence: string }>}
 */
export async function route(origin, destination, options = {}) {
  if (GOOGLE_MAPS_FALLBACK_ENABLED || MAPBOX_TRAFFIC_ENABLED) {
    throw new Error('Paid routing providers are disabled in v0.1')
  }
  const [lat1, lng1] = origin
  const [lat2, lng2] = destination
  const distanceKm = haversineKm(lat1, lng1, lat2, lng2) * 1.25
  const durationMinutes = Math.max(1, Math.round((distanceKm / 30) * 60))
  externalCallCount += 1
  return {
    distanceKm,
    durationMinutes,
    polyline: [
      [lat1, lng1],
      [lat2, lng2],
    ],
    routeProvider: ROUTING_PROVIDER,
    trafficProvider: TRAFFIC_PROVIDER,
    trafficAware: TRAFFIC_PROVIDER !== 'none' && MAPBOX_TRAFFIC_ENABLED,
    trafficSignalAware: false,
    routeConfidence: distanceKm > 0 ? 'medium' : 'low',
  }
}

export async function estimateEta(origin, destination, options = {}) {
  const r = await route(origin, destination, options)
  return r.durationMinutes
}

export async function getTrafficForRoute() {
  if (!TRAFFIC_SIGNALS_ENABLED) return null
  return {
    status: 'signals_only',
    trafficAware: false,
    disclaimer: 'Official ODOT/WSDOT signals only — not route-level live traffic',
  }
}

export function getProviderCallCount() {
  return externalCallCount
}

export function resetProviderCallCountForTests() {
  externalCallCount = 0
}

function haversineKm(lat1, lon1, lat2, lon2) {
  const r = 6371
  const dLat = ((lat2 - lat1) * Math.PI) / 180
  const dLon = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2
  return r * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}
