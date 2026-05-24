/** Distance display with driver units preference (mi | km). */

export function formatDistanceMeters(meters, units = 'mi') {
  const n = Number(meters)
  if (!Number.isFinite(n) || n < 0) return '—'

  if (units === 'km') {
    if (n < 1000) return `${Math.round(n)} m`
    return `${(n / 1000).toFixed(1)} km`
  }

  const miles = n / 1609.344
  if (miles < 0.1) return `${Math.round(n * 3.28084)} ft`
  return `${miles.toFixed(1)} mi`
}

export function formatDistanceKm(km, units = 'mi') {
  const n = Number(km)
  if (!Number.isFinite(n) || n < 0) return '—'
  return formatDistanceMeters(n * 1000, units)
}
