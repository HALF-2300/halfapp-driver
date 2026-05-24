/**
 * Driver ride display — fields aligned with backend `RideDriverView` (OpenAPI / docs/RIDE_LIFECYCLE_CONTRACT.md).
 * Do not derive map, ETA, or coordinates here until those keys exist on the contract payload.
 */

export const RIDE_UI_STATES = {
  REQUESTED: 'requested',
  ACCEPTED: 'accepted',
  OFFERED: 'offered',
  DRIVER_ARRIVED: 'driver_arrived',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
  UNKNOWN: 'unknown',
}

export const NA = '—'

const CONTRACT_STATUSES = new Set([
  'requested',
  'offered',
  'accepted',
  'driver_arrived',
  'in_progress',
  'completed',
  'cancelled',
])

export function normalizeRideStatus(raw) {
  const s = String(raw ?? '').toLowerCase().trim()
  if (!s) return RIDE_UI_STATES.UNKNOWN
  if (CONTRACT_STATUSES.has(s)) return s
  if (s === 'available' || s === 'pending') return RIDE_UI_STATES.REQUESTED
  return RIDE_UI_STATES.UNKNOWN
}

export function formatRideStatusLabel(raw) {
  const n = normalizeRideStatus(raw)
  const labels = {
    [RIDE_UI_STATES.REQUESTED]: 'Requested',
    [RIDE_UI_STATES.OFFERED]: 'Offered',
    [RIDE_UI_STATES.ACCEPTED]: 'Accepted',
    [RIDE_UI_STATES.DRIVER_ARRIVED]: 'Driver arrived',
    [RIDE_UI_STATES.IN_PROGRESS]: 'In progress',
    [RIDE_UI_STATES.COMPLETED]: 'Completed',
    [RIDE_UI_STATES.CANCELLED]: 'Cancelled',
  }
  return labels[n] || 'Unknown'
}

export function formatOptional(value) {
  if (value == null || value === '') return NA
  return String(value)
}

/**
 * @param {Record<string, unknown>} raw — must match `RideDriverView` from API
 */
export function normalizeRideForDisplay(raw) {
  const customerName = raw.customer_name != null && raw.customer_name !== '' ? String(raw.customer_name) : NA
  const pickup = raw.pickup_location ?? null
  const destination = raw.destination ?? null

  let fareLabel = NA
  if (raw.fare_amount != null && raw.fare_amount !== '') {
    const n = Number(raw.fare_amount)
    if (Number.isFinite(n)) fareLabel = `$${n.toFixed(2)}`
    else fareLabel = formatOptional(raw.fare_amount)
  }

  let distanceLabel = NA
  if (raw.distance_km != null && raw.distance_km !== '') {
    const n = Number(raw.distance_km)
    if (Number.isFinite(n)) distanceLabel = `${n} km`
    else distanceLabel = formatOptional(raw.distance_km)
  }

  return {
    id: raw.id,
    customerName,
    pickup: formatOptional(pickup),
    destination: formatOptional(destination),
    fareLabel,
    distanceLabel,
    rawStatus: raw.status ?? '',
    normalizedStatus: normalizeRideStatus(raw.status),
    statusLabel: formatRideStatusLabel(raw.status),
  }
}
