import { useEffect, useRef } from 'react'

import L from 'leaflet'

import 'leaflet.heat'

import driverAPI from '../utils/api.js'

/**
 * Fleet slow-zone overlay (HalfApp driver speeds — not municipal live traffic).
 */
export default function TrafficHeatLayer({ map, enabled }) {
  const heatRef = useRef(null)

  useEffect(() => {
    if (!map) return undefined

    if (!heatRef.current) {
      heatRef.current = L.heatLayer([], {
        radius: 26,
        blur: 18,
        minOpacity: 0.25,
        gradient: { 0.2: 'lime', 0.6: 'yellow', 1.0: 'red' },
      })
    }

    const layer = heatRef.current
    if (enabled) {
      layer.addTo(map)
    } else {
      try {
        layer.removeFrom(map)
      } catch {
        /* already detached */
      }
    }

    return undefined
  }, [map, enabled])

  useEffect(() => {
    if (!enabled || !map) return undefined

    let cancelled = false

    async function refresh() {
      try {
        const json = await driverAPI.getFleetTrafficHeatmap({
          minutes: 10,
          precision: 0.002,
        })
        if (cancelled || !heatRef.current) return
        const pts = (json?.points || []).map((p) => [p[0], p[1], p[2]])
        heatRef.current.setLatLngs(pts)
      } catch {
        /* heatmap optional */
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
  }, [enabled, map])

  return null
}
