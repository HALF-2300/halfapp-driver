import { RIDE_STATUS } from '../hooks/useRide.js'

const STATUS_COPY = {
  [RIDE_STATUS.REQUESTING]: { label: 'Finding your driver…', sub: 'Open board — first driver claim wins' },
  [RIDE_STATUS.MATCHED]: { label: 'Driver matched', sub: 'Your driver is on the way' },
  [RIDE_STATUS.EN_ROUTE]: { label: 'Driver en route', sub: 'Head to your pickup spot' },
  [RIDE_STATUS.ARRIVED]: { label: 'Driver has arrived', sub: 'Your driver is waiting' },
  [RIDE_STATUS.IN_PROGRESS]: { label: 'Trip in progress', sub: 'Sit back and enjoy the ride' },
}

function fmtEta(seconds) {
  if (seconds == null) return null
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m > 0 ? `${m} min${m > 1 ? 's' : ''}` : `${s}s`
}

function fmtFare(cents) {
  if (cents == null) return null
  return `$${(cents / 100).toFixed(2)}`
}

export default function TrackRide({ status, driver, eta, fare, ride, onCancel }) {
  const copy = STATUS_COPY[status] ?? { label: status, sub: '' }
  const canCancel = [RIDE_STATUS.REQUESTING, RIDE_STATUS.MATCHED].includes(status)
  const isMeter = status === RIDE_STATUS.IN_PROGRESS

  return (
    <div className="track-panel">
      <div className={`status-banner status-banner--${status}`}>
        <div className="status-pulse" />
        <div>
          <div className="status-label">{copy.label}</div>
          <div className="status-sub">{copy.sub}</div>
        </div>
      </div>

      {eta != null && status !== RIDE_STATUS.ARRIVED && (
        <div className="eta-chip">
          <span className="eta-number">{fmtEta(eta)}</span>
          <span className="eta-unit">{isMeter ? 'remaining' : 'away'}</span>
        </div>
      )}

      {isMeter && fare != null && (
        <div className="fare-meter">
          <span className="meter-label">Fare</span>
          <span className="meter-value">{fmtFare(fare)}</span>
        </div>
      )}

      {driver && (
        <div className="driver-card">
          <div className="driver-avatar">{(driver.name ?? 'D').charAt(0).toUpperCase()}</div>
          <div className="driver-info">
            <div className="driver-name">{driver.name ?? 'Your driver'}</div>
            <div className="driver-meta">
              {driver.rating != null ? `★ ${driver.rating.toFixed(2)}` : 'Assigned'}
              {driver.vehicle ? ` · ${driver.vehicle}` : ''}
              {driver.plate ? ` · ${driver.plate}` : ''}
            </div>
          </div>
        </div>
      )}

      {ride?.pickup_location && (
        <div className="fare-estimate">
          <div className="fare-row">
            <span className="fare-label">Pickup</span>
            <span className="fare-value">{ride.pickup_location.split(',')[0]}</span>
          </div>
          <div className="fare-row">
            <span className="fare-label">Dropoff</span>
            <span className="fare-value">
              {(ride.dropoff_location || ride.destination || '—').split(',')[0]}
            </span>
          </div>
          <div className="fare-row">
            <span className="fare-label">Ride</span>
            <span className="fare-value mono">#{ride.id}</span>
          </div>
        </div>
      )}

      {status === RIDE_STATUS.ARRIVED && (
        <div className="arrived-cta">
          <p>Your driver is at pickup. Ride #{ride?.id ?? '—'}.</p>
        </div>
      )}

      {canCancel && (
        <button type="button" className="btn btn--ghost" onClick={onCancel}>
          Cancel ride
        </button>
      )}
    </div>
  )
}
