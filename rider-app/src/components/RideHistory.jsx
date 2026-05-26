import { Link } from 'react-router-dom'
import { formatCents } from '../utils/api.js'
import { riderStatusLabel } from '../utils/riderStatus.js'

export default function RideHistory({ rides, loading }) {
  if (loading) {
    return <p className="fare-label">Loading trip history…</p>
  }

  if (!rides?.length) {
    return (
      <div className="fare-estimate">
        <p className="fare-label">No past trips yet. Request your first ride above.</p>
      </div>
    )
  }

  return (
    <div className="fare-estimate" data-testid="ride-history">
      <p className="field-label">Recent trips</p>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {rides.map((ride) => (
          <li
            key={ride.id}
            style={{
              borderTop: '1px solid var(--border)',
              padding: '10px 0',
            }}
          >
            <Link
              to={`/ride/${ride.id}`}
              style={{ color: 'var(--blue)', textDecoration: 'none', fontSize: 13, fontWeight: 600 }}
            >
              Ride #{ride.id}
            </Link>
            <div className="fare-row" style={{ marginTop: 4 }}>
              <span className="fare-label">{riderStatusLabel(ride)}</span>
              <span className="fare-value">
                {ride.customer_total_cents != null
                  ? formatCents(ride.customer_total_cents)
                  : '—'}
              </span>
            </div>
            <p className="fare-label" style={{ marginTop: 4 }}>
              {(ride.pickup_location || '—').split(',')[0]} →{' '}
              {(ride.dropoff_location || ride.destination || '—').split(',')[0]}
            </p>
            {ride.assigned_driver_name && (
              <p className="fare-label">Driver: {ride.assigned_driver_name}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
