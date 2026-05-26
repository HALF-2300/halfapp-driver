import React, { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  assignRide,
  cancelRide,
  formatCents,
  formatDate,
  getRide,
  listDrivers,
  statusBadgeClass,
} from '../utils/api.js'

const POLL_MS = 5000

export default function RideDetailPage() {
  const { rideId } = useParams()
  const [ride, setRide] = useState(null)
  const [drivers, setDrivers] = useState([])
  const [selectedDriverId, setSelectedDriverId] = useState('')
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [cancelReason, setCancelReason] = useState('ops intervention')

  const load = useCallback(async () => {
    try {
      const data = await getRide(rideId)
      setRide(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }, [rideId])

  useEffect(() => {
    load()
    const timer = setInterval(load, POLL_MS)
    return () => clearInterval(timer)
  }, [load])

  useEffect(() => {
    listDrivers()
      .then((rows) => setDrivers(rows))
      .catch(() => setDrivers([]))
  }, [])

  const canCancel = ride && !['completed', 'cancelled'].includes(ride.status)
  const canAssign = ride && ride.status === 'requested' && !ride.driver_id

  const eligibleDrivers = drivers.filter(
    (d) => d.online && !d.active_ride_id && d.approval?.status === 'approved',
  )

  const onCancel = async () => {
    setBusy(true)
    setActionError(null)
    try {
      const result = await cancelRide(rideId, cancelReason)
      setRide(result.ride)
    } catch (err) {
      setActionError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const onAssign = async () => {
    if (!selectedDriverId) return
    setBusy(true)
    setActionError(null)
    try {
      const result = await assignRide(rideId, Number(selectedDriverId))
      setRide(result.ride)
    } catch (err) {
      setActionError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !ride) {
    return (
      <div>
        <Link to="/" className="text-sm text-orange-300">
          ← Back to rides
        </Link>
        <p className="mt-4 text-red-300">{error}</p>
      </div>
    )
  }

  if (!ride) {
    return <p className="text-[var(--ops-muted)]">Loading ride…</p>
  }

  return (
    <div>
      <Link to="/" className="text-sm text-orange-300">
        ← Back to rides
      </Link>

      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Ride #{ride.id}</h1>
          <p className="mt-1 text-sm text-[var(--ops-muted)]">{ride.customer_name || 'Unnamed rider'}</p>
        </div>
        <span className={`ops-badge ${statusBadgeClass(ride.status)}`}>{ride.status}</span>
      </div>

      {actionError ? <p className="mt-4 text-sm text-red-300">{actionError}</p> : null}

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-white/10 bg-[var(--ops-surface)] p-4">
          <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--ops-muted)]">Assignment</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--ops-muted)]">Rider ID</dt>
              <dd>{ride.rider_id ?? '—'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--ops-muted)]">Driver ID</dt>
              <dd>{ride.driver_id ?? 'Unassigned'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--ops-muted)]">Lifecycle reason</dt>
              <dd>{ride.lifecycle_reason || '—'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--ops-muted)]">Created</dt>
              <dd>{formatDate(ride.created_at)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--ops-muted)]">Accepted</dt>
              <dd>{formatDate(ride.accepted_at)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--ops-muted)]">Completed</dt>
              <dd>{formatDate(ride.completed_at)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--ops-muted)]">Cancelled</dt>
              <dd>{formatDate(ride.cancelled_at)}</dd>
            </div>
          </dl>
        </section>

        <section className="rounded-xl border border-white/10 bg-[var(--ops-surface)] p-4">
          <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--ops-muted)]">Payment</h2>
          {ride.payment ? (
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--ops-muted)]">Status</dt>
                <dd>
                  <span className={`ops-badge ${statusBadgeClass(ride.payment.status)}`}>
                    {ride.payment.status}
                  </span>
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--ops-muted)]">Amount</dt>
                <dd>{formatCents(ride.payment.amount_cents)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--ops-muted)]">Driver payout</dt>
                <dd>{formatCents(ride.payment.driver_payout_cents)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--ops-muted)]">Authorized</dt>
                <dd>{formatDate(ride.payment.authorized_at)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--ops-muted)]">Captured</dt>
                <dd>{formatDate(ride.payment.captured_at)}</dd>
              </div>
            </dl>
          ) : (
            <p className="mt-3 text-sm text-[var(--ops-muted)]">No payment record</p>
          )}
        </section>
      </div>

      <section className="mt-4 rounded-xl border border-white/10 bg-[var(--ops-surface)] p-4">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--ops-muted)]">Lifecycle events</h2>
        <div className="mt-3 max-h-64 overflow-y-auto">
          <table className="ops-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Event</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {(ride.lifecycle_events || []).map((event, index) => (
                <tr key={`${event.event_type}-${event.occurred_at}-${index}`}>
                  <td>{formatDate(event.occurred_at)}</td>
                  <td>{event.event_type}</td>
                  <td>{event.source || '—'}</td>
                </tr>
              ))}
              {!ride.lifecycle_events?.length ? (
                <tr>
                  <td colSpan={3} className="text-[var(--ops-muted)]">
                    No lifecycle events recorded
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-4 rounded-xl border border-white/10 bg-[var(--ops-surface)] p-4">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--ops-muted)]">Interventions</h2>

        {canCancel ? (
          <div className="mt-3 space-y-2">
            <label className="block text-sm">
              Cancel reason
              <input
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                className="mt-1 w-full max-w-md rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm"
              />
            </label>
            <button
              type="button"
              disabled={busy}
              className="ops-btn ops-btn-danger"
              data-testid="cancel-ride-btn"
              onClick={onCancel}
            >
              Cancel ride
            </button>
          </div>
        ) : (
          <p className="mt-3 text-sm text-[var(--ops-muted)]">Ride is terminal — cannot cancel.</p>
        )}

        {canAssign ? (
          <div className="mt-4 border-t border-white/10 pt-4">
            <p className="text-sm text-[var(--ops-muted)]">Force assign an online, available driver:</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <select
                value={selectedDriverId}
                onChange={(e) => setSelectedDriverId(e.target.value)}
                className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm"
              >
                <option value="">Select driver…</option>
                {eligibleDrivers.map((driver) => (
                  <option key={driver.id} value={driver.id}>
                    #{driver.id} {driver.name || driver.email}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={busy || !selectedDriverId}
                className="ops-btn ops-btn-primary"
                data-testid="assign-ride-btn"
                onClick={onAssign}
              >
                Assign driver
              </button>
            </div>
            {!eligibleDrivers.length ? (
              <p className="mt-2 text-xs text-[var(--ops-muted)]">No eligible online drivers right now.</p>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  )
}
