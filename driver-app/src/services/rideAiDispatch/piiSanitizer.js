const PLATE_PATTERN = /\b[A-Z]{2}[-\s]?\d{3,4}\b/gi

/**
 * @param {string | null | undefined} plate
 * @returns {string}
 */
export function tokenizePlate(plate) {
  if (!plate || typeof plate !== 'string') return 'VEHICLE_TOKEN_UNKNOWN'
  const digits = plate.replace(/\D/g, '')
  const suffix = digits.slice(-2) || '00'
  return `VEHICLE_TOKEN_${suffix}`
}

/**
 * @param {number | null | undefined} value
 * @returns {number | null}
 */
function roundCoord(value) {
  if (value == null || !Number.isFinite(Number(value))) return null
  return Math.round(Number(value) * 100) / 100
}

/**
 * @param {Record<string, unknown>} ctx
 * @returns {Record<string, unknown>}
 */
export function sanitizeOperationalContext(ctx = {}) {
  const out = { ...ctx }
  if ('rider_name' in out) delete out.rider_name
  if ('customer_name' in out) delete out.customer_name
  if ('license_plate' in out) out.vehicle_token = tokenizePlate(String(out.license_plate))
  if ('plate' in out) out.vehicle_token = tokenizePlate(String(out.plate))
  delete out.license_plate
  delete out.plate
  if ('pickup_latitude' in out) {
    out.pickup_lat_rounded = roundCoord(out.pickup_latitude)
    delete out.pickup_latitude
  }
  if ('pickup_longitude' in out) {
    out.pickup_lng_rounded = roundCoord(out.pickup_longitude)
    delete out.pickup_longitude
  }
  if ('dropoff_latitude' in out) {
    out.dropoff_lat_rounded = roundCoord(out.dropoff_latitude)
    delete out.dropoff_latitude
  }
  if ('dropoff_longitude' in out) {
    out.dropoff_lng_rounded = roundCoord(out.dropoff_longitude)
    delete out.dropoff_longitude
  }
  if (typeof out.pickup_location === 'string') {
    out.pickup_zone = 'PICKUP_ZONE_REDACTED'
    delete out.pickup_location
  }
  if (typeof out.destination === 'string') {
    out.dropoff_zone = 'DROPOFF_ZONE_REDACTED'
    delete out.destination
  }
  return out
}

/**
 * @param {string} text
 * @returns {string}
 */
export function scrubSensitiveStrings(text) {
  if (!text) return ''
  return text.replace(PLATE_PATTERN, (match) => tokenizePlate(match))
}

/**
 * @param {Record<string, unknown>} payload
 * @returns {string}
 */
export function buildSanitizedPromptPayload(payload) {
  const sanitized = sanitizeOperationalContext(payload)
  const json = JSON.stringify(sanitized, null, 2)
  return scrubSensitiveStrings(json)
}
