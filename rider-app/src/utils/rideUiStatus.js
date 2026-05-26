/** UI lifecycle labels (Downloads bundle); mapped from backend storage status. */
export const RIDE_STATUS = {
  IDLE: 'idle',
  REQUESTING: 'requesting',
  MATCHED: 'matched',
  EN_ROUTE: 'en_route',
  ARRIVED: 'arrived',
  IN_PROGRESS: 'in_progress',
  COMPLETE: 'complete',
  CANCELLED: 'cancelled',
  ERROR: 'error',
}

const TERMINAL = new Set([
  RIDE_STATUS.COMPLETE,
  RIDE_STATUS.CANCELLED,
  RIDE_STATUS.ERROR,
])

export function isTerminalUiStatus(status) {
  return TERMINAL.has(status)
}

/** Map HalfApp `ride.status` to rider UI state machine. */
export function mapBackendStatus(storageStatus) {
  switch (storageStatus) {
    case 'requested':
      return RIDE_STATUS.REQUESTING
    case 'accepted':
      return RIDE_STATUS.MATCHED
    case 'driver_arrived':
      return RIDE_STATUS.ARRIVED
    case 'in_progress':
      return RIDE_STATUS.IN_PROGRESS
    case 'completed':
      return RIDE_STATUS.COMPLETE
    case 'cancelled':
      return RIDE_STATUS.CANCELLED
    default:
      return RIDE_STATUS.REQUESTING
  }
}

export function driverFromRide(ride) {
  if (!ride?.driver_id) return null
  const name = ride.assigned_driver_name?.trim() || `Driver #${ride.driver_id}`
  return {
    name,
    rating: null,
    vehicle: null,
    plate: null,
  }
}

/** Normalize payment API payload for Receipt.jsx */
export function paymentForReceipt(paymentView, ride) {
  if (!paymentView && !ride?.pricing?.customer_total_cents) return null
  const amountCents = paymentView?.amount_cents ?? ride?.pricing?.customer_total_cents
  return {
    fare_cents: amountCents,
    currency: paymentView?.currency ?? 'USD',
    status: paymentView?.status ?? (ride?.status === 'completed' ? 'captured' : 'pending'),
    payment_method: { label: 'HalfApp ledger' },
    settled_at: paymentView?.captured_at ?? ride?.completed_at ?? null,
    trip_id: ride?.id ?? paymentView?.ride_id,
    source: paymentView ? 'LEDGER' : 'RIDE_PRICING',
  }
}
