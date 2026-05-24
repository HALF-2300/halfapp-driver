/**
 * External navigation URLs — convenience only; does not affect fare, ledger, or in-app map.
 * Uses public Google Maps directions URLs (no API key).
 */

export const GOOGLE_MAPS_DIRECTIONS_BASE = 'https://www.google.com/maps/dir/?api=1'

/**
 * @param {unknown} lat
 * @param {unknown} lng
 */
export function isValidNavigationCoordinate(lat, lng) {
  const la = Number(lat)
  const ln = Number(lng)
  return (
    Number.isFinite(la) &&
    Number.isFinite(ln) &&
    la >= -90 &&
    la <= 90 &&
    ln >= -180 &&
    ln <= 180
  )
}

/**
 * @param {{ lat?: unknown, lng?: unknown, address?: unknown, label?: unknown } | null | undefined} target
 */
export function hasNavigationTarget(target) {
  if (!target) return false
  if (isValidNavigationCoordinate(target.lat, target.lng)) return true
  const text = String(target.address ?? target.label ?? '').trim()
  return text.length > 0
}

/**
 * Prefer coordinates; fall back to address/label text when coords are missing.
 *
 * @param {{ lat?: unknown, lng?: unknown, address?: unknown, label?: unknown } | null | undefined} target
 * @returns {string | null}
 */
export function buildGoogleMapsNavigationUrl(target) {
  if (!target) return null

  if (isValidNavigationCoordinate(target.lat, target.lng)) {
    const la = Number(target.lat)
    const ln = Number(target.lng)
    const destination = `${la},${ln}`
    return `${GOOGLE_MAPS_DIRECTIONS_BASE}&destination=${encodeURIComponent(destination)}`
  }

  const text = String(target.address ?? target.label ?? '').trim()
  if (!text) return null

  return `${GOOGLE_MAPS_DIRECTIONS_BASE}&destination=${encodeURIComponent(text)}`
}

/**
 * Opens navigation in the system browser or maps app (new tab/window when supported).
 *
 * @param {string | null | undefined} url
 * @returns {boolean} whether a window open was attempted successfully
 */
export function openExternalNavigation(url) {
  if (!url || typeof url !== 'string') return false
  if (typeof window === 'undefined') return false
  const opened = window.open(url, '_blank', 'noopener,noreferrer')
  return opened != null
}
