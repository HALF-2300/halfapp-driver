export const DELIVERY_STATUS_LABELS = {
  paid: 'Order placed',
  merchant_accepted: 'Merchant accepted',
  preparing: 'Preparing',
  ready_for_pickup: 'Ready for pickup',
  courier_assigned: 'Assigned to you',
  picked_up: 'Picked up',
  en_route: 'On the way',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
  refunded: 'Refunded',
  failed: 'Failed',
}

export function deliveryStatusLabel(status) {
  return DELIVERY_STATUS_LABELS[status] || status || 'Unknown'
}

export function nextCourierDeliveryAction(status) {
  if (status === 'courier_assigned') return 'pickup'
  if (status === 'picked_up') return 'en_route'
  if (status === 'en_route') return 'delivered'
  return null
}

export function locationHealthLabel({ status, usingFallback, error }) {
  if (usingFallback) return 'Dev fallback location'
  if (status === 'denied') return 'Location permission denied'
  if (status === 'stale') return 'Stale location'
  if (status === 'unavailable') return 'Location unavailable'
  if (error) return `Location issue: ${error}`
  if (status === 'allowed') return 'Accurate location available'
  return 'Checking location'
}
