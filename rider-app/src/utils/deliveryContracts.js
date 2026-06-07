export const DELIVERY_STATUSES = [
  'created',
  'priced',
  'paid',
  'merchant_accepted',
  'preparing',
  'ready_for_pickup',
  'courier_assigned',
  'picked_up',
  'en_route',
  'delivered',
  'cancelled',
  'refunded',
  'failed',
]

export const DELIVERY_STATUS_LABELS = {
  created: 'Created',
  priced: 'Priced',
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

export const DELIVERY_TIMELINE = [
  'paid',
  'merchant_accepted',
  'preparing',
  'ready_for_pickup',
  'courier_assigned',
  'picked_up',
  'en_route',
  'delivered',
]

export function deliveryStatusLabel(status) {
  return DELIVERY_STATUS_LABELS[status] || status || 'Unknown'
}

export function deliveryStepIndex(status) {
  const index = DELIVERY_TIMELINE.indexOf(status)
  return index < 0 ? 0 : index
}
