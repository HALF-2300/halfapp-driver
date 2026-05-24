import { useEffect, useRef } from 'react'

import driverAPI from '../utils/api.js'

const TELEMETRY_INTERVAL_MS = 5000

function haversineMeters(lat1, lng1, lat2, lng2) {
  const R = 6371000
  const toRad = (d) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

/**
 * Post fleet telemetry while online (feeds keyless traffic heatmap).
 *
 * @param {{ enabled: boolean, getSnapshot: () => { lat: number, lng: number, speedMps?: number | null } | null }} opts
 */
export function useTelemetryPing({ enabled, getSnapshot }) {
  const getSnapshotRef = useRef(getSnapshot)
  getSnapshotRef.current = getSnapshot
  const lastSampleRef = useRef(null)

  useEffect(() => {
    if (!enabled) return undefined

    let cancelled = false

    async function tick() {
      const snap = getSnapshotRef.current?.()
      if (!snap || cancelled) return
      const { lat, lng } = snap
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return

      let speed_mps = snap.speedMps
      const capturedAt = snap.capturedAt ?? Date.now()
      const prev = lastSampleRef.current
      if ((speed_mps == null || !Number.isFinite(speed_mps)) && prev) {
        const dtSec = (capturedAt - prev.capturedAt) / 1000
        if (dtSec >= 0.5 && dtSec <= 60) {
          const dist = haversineMeters(prev.lat, prev.lng, lat, lng)
          speed_mps = dist / dtSec
        }
      }
      lastSampleRef.current = { lat, lng, capturedAt }

      try {
        await driverAPI.postDriverTelemetry({
          lat,
          lng,
          speed_mps: Number.isFinite(speed_mps) && speed_mps >= 0 ? speed_mps : undefined,
        })
      } catch {
        /* telemetry must not block cockpit */
      }
    }

    tick()
    const timer = window.setInterval(tick, TELEMETRY_INTERVAL_MS)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [enabled])
}
