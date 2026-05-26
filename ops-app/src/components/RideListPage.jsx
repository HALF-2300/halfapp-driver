import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatCents, formatDate, listRides, statusBadgeClass } from '../utils/api.js'

const POLL_MS = 5000

export default function RideListPage() {
  const [filter, setFilter] = useState('all')
  const [rides, setRides] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)

  const load = useCallback(async () => {
    try {
      const status = filter === 'active' ? 'active' : filter === 'completed' ? 'completed' : undefined
      const data = await listRides({ status })
      setRides(data.rides || [])
      setError(null)
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    setLoading(true)
    load()
    const timer = setInterval(load, POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  const activeCount = rides.filter((r) =>
    ['accepted', 'driver_arrived', 'in_progress', 'requested'].includes(r.status),
  ).length

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Rides</h1>
          <p className="text-sm text-[var(--ops-muted)]">
            {filter === 'active' ? `${rides.length} active` : `${rides.length} shown`}
            {lastUpdated ? ` · updated ${lastUpdated.toLocaleTimeString()}` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          {['all', 'active', 'completed'].map((value) => (
            <button
              key={value}
              type="button"
              className={`ops-btn ${filter === value ? 'ops-btn-primary' : ''}`}
              onClick={() => setFilter(value)}
            >
              {value}
            </button>
          ))}
          <button type="button" className="ops-btn" onClick={load}>
            Refresh
          </button>
        </div>
      </div>

      {error ? <p className="mb-4 text-sm text-red-300">{error}</p> : null}

      <div className="mb-4 rounded-xl border border-white/10 bg-[var(--ops-surface)] p-4 text-sm">
        <span className="text-[var(--ops-muted)]">Quick answers: </span>
        <strong>{activeCount}</strong> rides in active-ish states on this page · filter “active” for in-flight only
      </div>

      <div className="overflow-x-auto rounded-xl border border-white/10 bg-[var(--ops-surface)]">
        {loading && !rides.length ? (
          <p className="p-6 text-sm text-[var(--ops-muted)]">Loading rides…</p>
        ) : (
          <table className="ops-table" data-testid="rides-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Status</th>
                <th>Rider</th>
                <th>Driver</th>
                <th>Payment</th>
                <th>Amount</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {rides.map((ride) => (
                <tr key={ride.id}>
                  <td>
                    <Link to={`/rides/${ride.id}`} className="text-orange-300 hover:underline">
                      #{ride.id}
                    </Link>
                  </td>
                  <td>
                    <span className={`ops-badge ${statusBadgeClass(ride.status)}`}>{ride.status}</span>
                  </td>
                  <td>{ride.rider_id ?? '—'}</td>
                  <td>{ride.driver_id ?? '—'}</td>
                  <td>
                    {ride.payment_status ? (
                      <span className={`ops-badge ${statusBadgeClass(ride.payment_status)}`}>
                        {ride.payment_status}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>{formatCents(ride.payment_amount_cents)}</td>
                  <td>{formatDate(ride.created_at)}</td>
                </tr>
              ))}
              {!rides.length ? (
                <tr>
                  <td colSpan={7} className="text-center text-[var(--ops-muted)]">
                    No rides found
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
