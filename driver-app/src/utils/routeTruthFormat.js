/** Route snapshot / route truth display helpers (read-only, honest claims). */

export const OSRM_RUNTIME_NOT_PROVED = 'not_proved'
export const OSRM_RUNTIME_PROVED_PORTLAND = 'proved_portland_v0_1'

/** @param {number | null | undefined} meters */
export function formatDistanceMeters(meters) {
  const n = Number(meters)
  if (!Number.isFinite(n) || n < 0) return '—'
  if (n < 1000) return `${Math.round(n)} m`
  return `${(n / 1000).toFixed(1)} km`
}

/** @param {number | null | undefined} seconds */
export function formatDurationSeconds(seconds) {
  const n = Number(seconds)
  if (!Number.isFinite(n) || n < 0) return '—'
  const mins = Math.round(n / 60)
  return mins > 0 ? `~${mins} min` : '<1 min'
}

/** @param {string | null | undefined} provider */
export function isFallbackProvider(provider) {
  return provider === 'haversine_fallback'
}

/** @param {Record<string, unknown> | null | undefined} payload */
export function routingLabelFromPayload(payload) {
  if (!payload) return '—'
  if (payload.copy?.routing_label) return payload.copy.routing_label
  const truth = payload.route_truth
  if (truth?.used_fallback) return 'Straight-line estimate'
  return truth?.current_provider || '—'
}

/** @param {Record<string, unknown> | null | undefined} payload */
export function osrmStatusLabel(payload) {
  const claim = payload?.route_truth?.osrm_runtime_claim
  if (claim === OSRM_RUNTIME_PROVED_PORTLAND) {
    return 'OSRM runtime proved (Portland evidence on file)'
  }
  if (claim === OSRM_RUNTIME_NOT_PROVED) return 'OSRM runtime not proved'
  return payload?.copy?.osrm_status || 'OSRM runtime not proved'
}

const FORBIDDEN_ROUTING_PHRASES = [
  'production osrm',
  'road-accurate',
  'road accurate',
  'live road network proof',
]

/** @param {string} text */
export function containsForbiddenRoutingClaim(text) {
  if (!text) return false
  const lower = text.toLowerCase()
  return FORBIDDEN_ROUTING_PHRASES.some((phrase) => lower.includes(phrase))
}
