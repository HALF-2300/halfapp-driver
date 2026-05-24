/** @typedef {'ui_viewport_only'} MapViewportSource */

/**
 * @typedef {Object} CachedMapViewport
 * @property {number} latitude
 * @property {number} longitude
 * @property {number} zoom
 * @property {MapViewportSource} source
 * @property {string} savedAt
 */

export const MAP_VIEWPORT_STORAGE_KEY = 'halfapp:last-map-viewport'

/**
 * @param {unknown} value
 * @returns {value is CachedMapViewport}
 */
export function isCachedMapViewport(value) {
  if (!value || typeof value !== 'object') return false
  const v = /** @type {CachedMapViewport} */ (value)
  return (
    v.source === 'ui_viewport_only' &&
    Number.isFinite(v.latitude) &&
    Number.isFinite(v.longitude) &&
    Number.isFinite(v.zoom)
  )
}

/**
 * @returns {CachedMapViewport | null}
 */
export function readCachedMapViewport() {
  if (typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(MAP_VIEWPORT_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return isCachedMapViewport(parsed) ? parsed : null
  } catch {
    return null
  }
}

/**
 * @param {CachedMapViewport} viewport
 */
export function writeCachedMapViewport(viewport) {
  if (typeof sessionStorage === 'undefined') return
  if (!isCachedMapViewport(viewport)) return
  try {
    sessionStorage.setItem(MAP_VIEWPORT_STORAGE_KEY, JSON.stringify(viewport))
  } catch {
    // UI-only cache — ignore quota / privacy errors.
  }
}
