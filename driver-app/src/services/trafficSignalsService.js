/**
 * Free official traffic signals (ODOT TripCheck / WSDOT) via backend proxy.
 * Failure-safe: never throws to callers; empty signals on error.
 */

const env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {}
const API_BASE = env.VITE_API_BASE || 'http://127.0.0.1:8000'
export const TRAFFIC_SIGNALS_ENABLED =
  String(env.VITE_TRAFFIC_SIGNALS_ENABLED || 'false').toLowerCase() === 'true'

/**
 * @param {string} token
 * @param {{ origin?: { lat: number, lng: number }, destination?: { lat: number, lng: number }, bbox?: { minLat: number, maxLat: number, minLng: number, maxLng: number } }} params
 * @returns {Promise<{ provider: string, trafficAware: boolean, trafficSignalAware: boolean, routeConfidence: string, signals: Array<{ id: string, title: string, latitude: number, longitude: number, kind: string, severity: string }>, etaBufferMinutes: number, fetchStatus: string, disclaimer: string }>}
 */
export async function fetchTrafficSignals(token, params = {}) {
  const empty = {
    provider: 'none',
    trafficAware: false,
    trafficSignalAware: false,
    routeConfidence: 'low',
    signals: [],
    etaBufferMinutes: 0,
    fetchStatus: 'skipped',
    disclaimer: 'Official incident/flow signals only — not street-level live traffic',
  }

  if (!TRAFFIC_SIGNALS_ENABLED || !token) return empty

  const search = new URLSearchParams()
  const { origin, destination, bbox } = params
  if (origin?.lat != null && origin?.lng != null && destination?.lat != null && destination?.lng != null) {
    search.set('origin_lat', String(origin.lat))
    search.set('origin_lng', String(origin.lng))
    search.set('destination_lat', String(destination.lat))
    search.set('destination_lng', String(destination.lng))
  } else if (bbox) {
    search.set('min_lat', String(bbox.minLat))
    search.set('max_lat', String(bbox.maxLat))
    search.set('min_lng', String(bbox.minLng))
    search.set('max_lng', String(bbox.maxLng))
  } else {
    return empty
  }

  try {
    const res = await fetch(`${API_BASE}/drivers/traffic-signals?${search}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return { ...empty, fetchStatus: 'error' }
    const body = await res.json()
    return {
      provider: body.provider || 'none',
      trafficAware: Boolean(body.traffic_aware),
      trafficSignalAware: Boolean(body.traffic_signal_aware),
      routeConfidence: body.route_confidence || 'low',
      signals: Array.isArray(body.signals) ? body.signals : [],
      etaBufferMinutes: Number(body.eta_buffer_minutes) || 0,
      fetchStatus: body.fetch_status || 'ok',
      disclaimer: body.disclaimer || empty.disclaimer,
    }
  } catch {
    return { ...empty, fetchStatus: 'error' }
  }
}
