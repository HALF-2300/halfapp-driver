import { useEffect, useRef } from 'react'

import L from 'leaflet'

import 'leaflet.heat'

import driverAPI from '../utils/api.js'

/**
 * SIL heat overlay — busy + slow hex aggregates (gated server-side).
 */
export default function SilMapLayer({ map, enabled, showBusy, showSlow }) {
  const busyRef = useRef(null)
  const slowRef = useRef(null)

  useEffect(() => {
    if (!map) return undefined

    if (!busyRef.current) {
      busyRef.current = L.heatLayer([], {
        radius: 28,
        blur: 20,
        minOpacity: 0.2,
        gradient: { 0.3: '#22c55e', 0.7: '#eab308', 1.0: '#f97316' },
      })
    }
    if (!slowRef.current) {
      slowRef.current = L.heatLayer([], {
        radius: 26,
        blur: 18,
        minOpacity: 0.25,
        gradient: { 0.2: 'lime', 0.6: 'yellow', 1.0: 'red' },
      })
    }

    const busy = busyRef.current
    const slow = slowRef.current

    if (enabled && showBusy) busy.addTo(map)
    else {
      try {
        busy.removeFrom(map)
      } catch {
        /* detached */
      }
    }
    if (enabled && showSlow) slow.addTo(map)
    else {
      try {
        slow.removeFrom(map)
      } catch {
        /* detached */
      }
    }

    return undefined
  }, [map, enabled, showBusy, showSlow])

  useEffect(() => {
    if (!enabled || !map || (!showBusy && !showSlow)) return undefined

    let cancelled = false
    const layers = [showBusy && 'busy', showSlow && 'slow'].filter(Boolean).join(',')

    async function refresh() {
      try {
        const json = await driverAPI.getSilMap({ layers, window: '30m' })
        if (cancelled) return
        const cells = json?.cells || []
        if (showBusy && busyRef.current) {
          const pts = cells
            .filter((c) => c.busy_score != null)
            .map((c) => [c.lat, c.lng, c.busy_score])
          busyRef.current.setLatLngs(pts)
        }
        if (showSlow && slowRef.current) {
          const pts = cells
            .filter((c) => c.congestion_score != null)
            .map((c) => [c.lat, c.lng, c.congestion_score])
          slowRef.current.setLatLngs(pts)
        }
      } catch {
        /* optional overlay */
      }
    }

    refresh()
    const timer = window.setInterval(() => {
      if (!document.hidden) refresh()
    }, 15000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [enabled, map, showBusy, showSlow])

  return null
}
