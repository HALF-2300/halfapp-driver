export const DELIVERY_STATUS_LABELS = {
  paid: 'Order placed',
  merchant_accepted: 'Merchant accepted',
  preparing: 'Preparing',
  ready_for_pickup: 'Ready for pickup',
  courier_assigned: 'Courier assigned',
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

export function deliveryBadgeTone(status) {
  if (status === 'delivered') return 'ops-status-badge--good'
  if (status === 'cancelled' || status === 'failed' || status === 'refunded') return 'ops-status-badge--warn'
  if (status === 'paid' || status === 'preparing' || status === 'ready_for_pickup') return 'ops-status-badge--active'
  return ''
}
