import { useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import { useRide, RIDE_STATUS } from '../hooks/useRide.js'
import RiderAppShell from './RiderAppShell.jsx'
import TrackRide from './TrackRide.jsx'
import Receipt from './Receipt.jsx'

const TRACKING_STATES = new Set([
  RIDE_STATUS.REQUESTING,
  RIDE_STATUS.MATCHED,
  RIDE_STATUS.EN_ROUTE,
  RIDE_STATUS.ARRIVED,
  RIDE_STATUS.IN_PROGRESS,
])

export default function RideDetailPage() {
  const { rideId } = useParams()
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { status, ride, driver, driverLocation, eta, fare, payment, error, cancel, reset } = useRide({
    rideId: Number(rideId),
  })

  const handleDone = useCallback(() => {
    reset()
    navigate('/', { replace: true })
  }, [reset, navigate])

  if (error && !ride) {
    return (
      <RiderAppShell onSignOut={() => { logout(); navigate('/login') }}>
        <div className="error-banner">{error.message}</div>
        <button type="button" className="btn btn--ghost" onClick={() => navigate('/')}>
          Back home
        </button>
      </RiderAppShell>
    )
  }

  if (!ride && status === RIDE_STATUS.REQUESTING) {
    return (
      <RiderAppShell>
        <p className="fare-label">Loading ride…</p>
      </RiderAppShell>
    )
  }

  return (
    <RiderAppShell onSignOut={() => { logout(); navigate('/login') }}>
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

      {error && (
        <div className="error-banner">
          <strong>Update error:</strong> {error.message}
        </div>
      )}
    </RiderAppShell>
  )
}
