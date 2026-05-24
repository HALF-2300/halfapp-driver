const cache = new Map()

function randomSuffix() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

/** Stable key per (rideId, action) until the write succeeds. */
export function getIdempotencyKey(rideId, action) {
  const slot = `${rideId}:${action}`
  if (!cache.has(slot)) {
    cache.set(slot, `drv:${slot}:${randomSuffix()}`)
  }
  return cache.get(slot)
}

export function clearIdempotencyKey(rideId, action) {
  cache.delete(`${rideId}:${action}`)
}
