export async function geocodeAddress(query, citySuffix = 'Portland, OR') {
  const fullQuery = query.includes(',') ? query : `${query.trim()}, ${citySuffix}`
  const url = new URL('https://nominatim.openstreetmap.org/search')
  url.searchParams.set('q', fullQuery)
  url.searchParams.set('format', 'jsonv2')
  url.searchParams.set('limit', '1')

  const res = await fetch(url.toString(), {
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) throw new Error(`Geocoding failed (${res.status})`)

  const data = await res.json()
  if (!Array.isArray(data) || !data[0]) {
    throw new Error(`Address not found: ${query}`)
  }

  return {
    lat: Number(data[0].lat),
    lng: Number(data[0].lon),
    label: data[0].display_name || query,
  }
}
