import { useEffect, useRef, useState } from 'react'
import {
  DEV_FALLBACK_COORDINATES,
  GEOLOCATION_STATES,
  isLocationCaptureStale,
  LOCATION_STALE_MS,
} from '../utils/locationTruth.js'

const IS_DEV = import.meta.env.DEV

/**
 * Request device location for experimental map placement only.
 * Never sent to backend or used as marketplace truth.
 *
 * @returns {{
 *   position: { lat: number, lng: number, capturedAt?: number } | null,
 *   status: import('../utils/locationTruth.js').GeolocationTruthState,
 *   usingFallback: boolean,
 *   error: string | null,
 *   accuracyMeters: number | null,
 *   speedMps: number | null,
 * }}
 */
export function useDriverGeolocation() {
  const [position, setPosition] = useState(null)
  const [status, setStatus] = useState(GEOLOCATION_STATES.REQUESTING)
  const [usingFallback, setUsingFallback] = useState(false)
  const [error, setError] = useState(null)
  const [accuracyMeters, setAccuracyMeters] = useState(null)
  const [speedMps, setSpeedMps] = useState(null)
  const watchIdRef = useRef(null)
  const staleTimerRef = useRef(null)

  useEffect(() => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      if (IS_DEV) {
        setPosition({ ...DEV_FALLBACK_COORDINATES, capturedAt: Date.now() })
        setStatus(GEOLOCATION_STATES.DEV_FALLBACK)
        setUsingFallback(true)
        setError(null)
      } else {
        setStatus(GEOLOCATION_STATES.UNAVAILABLE)
        setError('Geolocation is not supported in this browser')
      }
      return undefined
    }

    setStatus(GEOLOCATION_STATES.REQUESTING)
    setPosition(null)
    setUsingFallback(false)

    const applyDevFallback = (message) => {
      if (!IS_DEV) return false
      setPosition({ ...DEV_FALLBACK_COORDINATES, capturedAt: Date.now() })
      setStatus(GEOLOCATION_STATES.DEV_FALLBACK)
      setUsingFallback(true)
      setError(message)
      return true
    }

    const scheduleStaleCheck = (capturedAt) => {
      if (staleTimerRef.current) window.clearTimeout(staleTimerRef.current)
      const age = Date.now() - capturedAt
      const delay = Math.max(LOCATION_STALE_MS - age, 0)
      staleTimerRef.current = window.setTimeout(() => {
        setStatus((current) =>
          current === GEOLOCATION_STATES.ALLOWED ? GEOLOCATION_STATES.STALE : current
        )
      }, delay)
    }

    watchIdRef.current = navigator.geolocation.watchPosition(
      (result) => {
        const capturedAt = result.timestamp
        const coords = {
          lat: result.coords.latitude,
          lng: result.coords.longitude,
          capturedAt,
        }
        const accuracy = result.coords.accuracy
        const speed = result.coords.speed
        setPosition(coords)
        setAccuracyMeters(Number.isFinite(accuracy) ? accuracy : null)
        setSpeedMps(Number.isFinite(speed) && speed >= 0 ? speed : null)
        setUsingFallback(false)
        setError(null)
        if (isLocationCaptureStale(capturedAt)) {
          setStatus(GEOLOCATION_STATES.STALE)
        } else {
          setStatus(GEOLOCATION_STATES.ALLOWED)
          scheduleStaleCheck(capturedAt)
        }
      },
      (err) => {
        const message = err?.message || 'Location permission denied'
        if (err?.code === 1) {
          if (!applyDevFallback(message)) {
            setStatus(GEOLOCATION_STATES.DENIED)
            setUsingFallback(false)
            setError(message)
          }
          return
        }
        if (!applyDevFallback(message)) {
          setStatus(GEOLOCATION_STATES.UNAVAILABLE)
          setUsingFallback(false)
          setError(message)
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 15_000,
        maximumAge: 0,
      }
    )

    return () => {
      if (watchIdRef.current != null) {
        navigator.geolocation.clearWatch(watchIdRef.current)
        watchIdRef.current = null
      }
      if (staleTimerRef.current) {
        window.clearTimeout(staleTimerRef.current)
        staleTimerRef.current = null
      }
    }
  }, [])

  return { position, status, usingFallback, error, accuracyMeters, speedMps }
}
