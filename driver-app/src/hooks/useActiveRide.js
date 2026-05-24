import { useCallback, useEffect, useState } from 'react'
import driverAPI from '../utils/api.js'

/**
 * Cockpit session recovery: undefined = loading, null = none, object = active payload.
 */
export function useActiveRide({ enabled = true } = {}) {
  const [activeRide, setActiveRide] = useState(undefined)
  const [error, setError] = useState(null)

  const fetchActiveRide = useCallback(async () => {
    if (!enabled) {
      setActiveRide(null)
      return null
    }
    setActiveRide(undefined)
    try {
      const data = await driverAPI.getActiveRide()
      setActiveRide(data ?? null)
      setError(null)
      return data ?? null
    } catch (err) {
      setError(err)
      setActiveRide(null)
      return null
    }
  }, [enabled])

  useEffect(() => {
    let cancelled = false
    if (!enabled) {
      setActiveRide(null)
      return undefined
    }
    driverAPI
      .getActiveRide()
      .then((data) => {
        if (!cancelled) {
          setActiveRide(data ?? null)
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err)
          setActiveRide(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [enabled])

  return { activeRide, error, refetch: fetchActiveRide, loading: activeRide === undefined }
}
