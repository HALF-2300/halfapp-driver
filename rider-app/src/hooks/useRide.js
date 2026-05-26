import { useState, useEffect, useRef, useCallback } from 'react'
import {
  createRide,
  cancelRide,
  fetchRide,
  fetchRidePayment,
  subscribeRideStatus,
} from '../utils/api.js'
import {
  RIDE_STATUS,
  driverFromRide,
  isTerminalUiStatus,
  mapBackendStatus,
  paymentForReceipt,
} from '../utils/rideUiStatus.js'

export { RIDE_STATUS }

/**
 * Rider lifecycle hook — Downloads UI states backed by HalfApp API (auth + SSE/poll).
 */
export function useRide({ rideId: initialRideId = null, customerName = 'Rider' } = {}) {
  const [status, setStatus] = useState(RIDE_STATUS.IDLE)
  const [ride, setRide] = useState(null)
  const [driver, setDriver] = useState(null)
  const [driverLocation, setDriverLoc] = useState(null)
  const [eta, setEta] = useState(null)
  const [fare, setFare] = useState(null)
  const [payment, setPayment] = useState(null)
  const [error, setError] = useState(null)

  const cleanupStream = useRef(null)

  const applyRide = useCallback((nextRide) => {
    if (!nextRide) return
    setRide(nextRide)
    setStatus(mapBackendStatus(nextRide.status))
    setDriver(driverFromRide(nextRide))
    const cents =
      nextRide.pricing?.customer_total_cents ??
      nextRide.customer_total_cents ??
      null
    if (cents != null) setFare(cents)
  }, [])

  useEffect(() => {
    if (isTerminalUiStatus(status)) {
      cleanupStream.current?.()
      cleanupStream.current = null
    }
  }, [status])

  useEffect(() => () => cleanupStream.current?.(), [])

  const openStream = useCallback(
    (id) => {
      cleanupStream.current?.()
      cleanupStream.current = subscribeRideStatus(id, {
        onStatus: (_storageStatus, nextRide) => {
          applyRide(nextRide)
          if (nextRide.status === 'completed') {
            fetchRidePayment(id)
              .then((payload) => setPayment(paymentForReceipt(payload.payment, nextRide)))
              .catch(() => {
                setPayment(paymentForReceipt(null, nextRide))
              })
          }
        },
        onDriverLocation: (loc) => setDriverLoc(loc),
        onFareUpdate: ({ fare_cents }) => setFare(fare_cents),
        onEtaUpdate: ({ eta_seconds }) => setEta(eta_seconds),
        onError: (err) => {
          setError(err)
          setStatus((prev) => (isTerminalUiStatus(prev) ? prev : RIDE_STATUS.ERROR))
        },
      })
    },
    [applyRide],
  )

  useEffect(() => {
    if (!initialRideId) return undefined
    let cancelled = false
    setStatus(RIDE_STATUS.REQUESTING)
    fetchRide(initialRideId)
      .then((payload) => {
        if (cancelled) return
        applyRide(payload.ride)
        if (payload.ride.status === 'completed') {
          return fetchRidePayment(initialRideId).then((payPayload) => {
            if (!cancelled) setPayment(paymentForReceipt(payPayload.payment, payload.ride))
          })
        }
        if (!isTerminalUiStatus(mapBackendStatus(payload.ride.status))) {
          openStream(initialRideId)
        }
        return undefined
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err)
          setStatus(RIDE_STATUS.ERROR)
        }
      })
    return () => {
      cancelled = true
    }
  }, [initialRideId, applyRide, openStream])

  const request = useCallback(
    async (params) => {
      setStatus(RIDE_STATUS.REQUESTING)
      setError(null)
      setDriver(null)
      setEta(null)
      setFare(null)
      setPayment(null)

      try {
        const body = {
          customer_name: customerName,
          pickup_location: params.pickup_address,
          dropoff_location: params.dropoff_address,
          pickup_latitude: params.pickup_lat,
          pickup_longitude: params.pickup_lng,
          dropoff_latitude: params.dropoff_lat,
          dropoff_longitude: params.dropoff_lng,
        }
        const response = await createRide(body)
        const created = response.ride
        applyRide(created)
        openStream(created.id)
        return created
      } catch (e) {
        setError(e)
        setStatus(RIDE_STATUS.ERROR)
        throw e
      }
    },
    [customerName, applyRide, openStream],
  )

  const cancel = useCallback(async () => {
    if (!ride?.id) return
    try {
      const response = await cancelRide(ride.id, 'rider_cancelled_from_app')
      applyRide(response.ride)
    } catch (e) {
      setError(e)
    }
  }, [ride?.id, applyRide])

  const reset = useCallback(() => {
    cleanupStream.current?.()
    cleanupStream.current = null
    setStatus(RIDE_STATUS.IDLE)
    setRide(null)
    setDriver(null)
    setDriverLoc(null)
    setEta(null)
    setFare(null)
    setPayment(null)
    setError(null)
  }, [])

  return {
    status,
    ride,
    driver,
    driverLocation,
    eta,
    fare,
    payment,
    error,
    request,
    cancel,
    reset,
  }
}
