/**
 * Debounced geocode + short-TTL route cache (v0.1 cost control).
 */

const GEOCODE_TTL_MS = 5 * 60 * 1000
const ROUTE_TTL_MS = 60 * 1000

const geocodeCache = new Map()
const routeCache = new Map()
let debounceTimer = null

export function debounce(fn, ms = 400) {
  return (...args) =>
    new Promise((resolve, reject) => {
      if (debounceTimer) clearTimeout(debounceTimer)
      debounceTimer = setTimeout(async () => {
        try {
          resolve(await fn(...args))
        } catch (e) {
          reject(e)
        }
      }, ms)
    })
}

export function getCachedGeocode(query) {
  const key = String(query).trim().toLowerCase()
  const hit = geocodeCache.get(key)
  if (!hit) return null
  if (Date.now() - hit.at > GEOCODE_TTL_MS) {
    geocodeCache.delete(key)
    return null
  }
  return hit.value
}

export function setCachedGeocode(query, value) {
  geocodeCache.set(String(query).trim().toLowerCase(), { at: Date.now(), value })
}

export function getCachedRoute(origin, destination) {
  const key = `${origin[0]},${origin[1]}->${destination[0]},${destination[1]}`
  const hit = routeCache.get(key)
  if (!hit) return null
  if (Date.now() - hit.at > ROUTE_TTL_MS) {
    routeCache.delete(key)
    return null
  }
  return hit.value
}

export function setCachedRoute(origin, destination, value) {
  const key = `${origin[0]},${origin[1]}->${destination[0]},${destination[1]}`
  routeCache.set(key, { at: Date.now(), value })
}

export function clearCachesForTests() {
  geocodeCache.clear()
  routeCache.clear()
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = null
}
