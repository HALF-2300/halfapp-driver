import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import { useRide, RIDE_STATUS } from '../hooks/useRide.js'
import { fetchMyRides } from '../utils/api.js'
import RiderAppShell from './RiderAppShell.jsx'
import BookRide from './BookRide.jsx'
import TrackRide from './TrackRide.jsx'
import Receipt from './Receipt.jsx'
import RideHistory from './RideHistory.jsx'

const BOOKING_STATES = new Set([RIDE_STATUS.IDLE, RIDE_STATUS.ERROR])
const TRACKING_STATES = new Set([
  RIDE_STATUS.REQUESTING,
  RIDE_STATUS.MATCHED,
  RIDE_STATUS.EN_ROUTE,
  RIDE_STATUS.ARRIVED,
  RIDE_STATUS.IN_PROGRESS,
])

export default function RequestRidePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { status, ride, driver, driverLocation, eta, fare, payment, error, request, cancel, reset } =
    useRide({
    customerName: user?.name || 'Rider',
  })
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchMyRides()
      .then((payload) => {
        if (!cancelled) setHistory(payload.rides || [])
      })
      .catch(() => {
        if (!cancelled) setHistory([])
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [ride?.id, status])

  const handleRequest = useCallback(
    async (params) => {
      try {
        const created = await request(params)
        navigate(`/ride/${created.id}`, { replace: true })
      } catch {
        /* error surfaced via useRide */
      }
    },
    [request, navigate],
  )

  const handleDone = useCallback(() => {
    reset()
    navigate('/', { replace: true })
  }, [reset, navigate])

  const handleSignOut = () => {
    logout()
    navigate('/login')
  }

  return (
    <RiderAppShell onSignOut={handleSignOut}>
      {BOOKING_STATES.has(status) && (
        <>
          <BookRide
            onRequest={handleRequest}
            disabled={status !== RIDE_STATUS.IDLE}
            customerName={user?.name || 'Rider'}
          />
          <RideHistory rides={history} loading={historyLoading} />
          {error && (
            <div className="error-banner">
              <strong>Something went wrong:</strong> {error.message}
            </div>
          )}
        </>
      )}

      {TRACKING_STATES.has(status) && (
        <TrackRide
          status={status}
          driver={driver}
          driverLocation={driverLocation}
          eta={eta}
          fare={fare}
          ride={ride}
          onCancel={cancel}
        />
      )}

      {status === RIDE_STATUS.COMPLETE && (
        <Receipt payment={payment} ride={ride} driver={driver} onDone={handleDone} />
      )}

      {status === RIDE_STATUS.CANCELLED && (
        <div className="cancelled-panel">
          <p>Ride cancelled.</p>
          <button type="button" className="btn btn--primary" onClick={handleDone}>
            Book again
          </button>
        </div>
      )}
    </RiderAppShell>
  )
}
