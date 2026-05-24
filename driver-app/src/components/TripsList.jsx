import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import AppShellLayout from './AppShellLayout.jsx'

import driverAPI from '../utils/api.js'
import { useDriverPreferences } from '../context/DriverPreferencesContext.jsx'
import { formatDistanceKm } from '../utils/formatDistance.js'
import { driverPayoutDollars } from '../utils/ridePricingDisplay.js'
import RidePayoutSummary from './cockpit/RidePayoutSummary.jsx'
import BetaTruthNotice from './BetaTruthNotice.jsx'
import TestRideLabel from './TestRideLabel.jsx'



function formatCurrency(n) {

  const num = Number(n)

  if (!Number.isFinite(num)) return '—'

  return `$${num.toFixed(2)}`

}



function formatTripDate(value) {

  if (!value) return '—'

  const d = new Date(value)

  if (Number.isNaN(d.getTime())) return '—'

  return d.toLocaleString(undefined, {

    month: 'short',

    day: 'numeric',

    hour: 'numeric',

    minute: '2-digit',

  })

}



const PAGE_LIMIT = 50

function TripsPager({ total, limit, offset, onOffsetChange }) {
  const canPrev = offset > 0
  const canNext = offset + limit < total
  const from = total === 0 ? 0 : offset + 1
  const to = Math.min(total, offset + limit)

  return (
    <div
      className="flex justify-between items-center mt-4 gap-3"
      data-testid="trips-pager"
    >
      <button
        type="button"
        className="ha-btn ha-btn--ghost text-sm"
        disabled={!canPrev}
        onClick={() => onOffsetChange(Math.max(0, offset - limit))}
        data-testid="trips-pager-prev"
      >
        Prev
      </button>
      <span className="text-xs ha-truth-note">
        {from}-{to} of {total}
      </span>
      <button
        type="button"
        className="ha-btn ha-btn--ghost text-sm"
        disabled={!canNext}
        onClick={() => onOffsetChange(offset + limit)}
        data-testid="trips-pager-next"
      >
        Next
      </button>
    </div>
  )
}

export default function TripsList() {
  const { units } = useDriverPreferences()
  const [rides, setRides] = useState([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('completed')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [searchQ, setSearchQ] = useState('')

  const fetchTrips = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await driverAPI.getDriverTrips({
        status: statusFilter || undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        q: searchQ.trim() || undefined,
        limit: PAGE_LIMIT,
        offset,
      })
      setRides(Array.isArray(data?.items) ? data.items : [])
      setTotal(Number(data?.total) || 0)
    } catch (err) {
      setRides([])
      setTotal(0)
      setError(err?.message || 'Could not load backend trips')
    } finally {
      setLoading(false)
    }
  }, [statusFilter, fromDate, toDate, searchQ, offset])



  useEffect(() => {

    fetchTrips()

  }, [fetchTrips])



  const completedTrips = useMemo(() => {
    if (statusFilter === 'completed') return rides.filter((ride) => ride.status === 'completed')
    if (statusFilter) return rides.filter((ride) => ride.status === statusFilter)
    return rides
  }, [rides, statusFilter])

  const handleExportCsv = async () => {
    try {
      await driverAPI.exportMyRidesCsv({
        status: statusFilter || undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        q: searchQ.trim() || undefined,
      })
    } catch (err) {
      setError(err?.message || 'Could not export trips')
    }
  }

  const resetFiltersPage = () => setOffset(0)



  const summary = useMemo(() => {

    const todayStr = new Date().toDateString()

    let totalEarnings = 0

    let todayEarnings = 0

    let todayTrips = 0



    for (const ride of completedTrips) {

      const fare = driverPayoutDollars(ride) ?? Number(ride.fare_amount)

      if (Number.isFinite(fare)) totalEarnings += fare

      if (ride.completed_at) {

        const d = new Date(ride.completed_at)

        if (!Number.isNaN(d.getTime()) && d.toDateString() === todayStr) {

          todayTrips += 1

          if (Number.isFinite(fare)) todayEarnings += fare

        }

      }

    }



    return {

      todayTrips,

      todayEarnings,

      totalTrips: completedTrips.length,

      totalEarnings,

    }

  }, [completedTrips])



  return (

    <AppShellLayout

      testId="trips-screen"

      title="Trips"

      subtitle="Completed rides from the backend lifecycle assigned to this driver."

    >

      <BetaTruthNotice />

      <section className="ha-section" data-testid="trips-filters">
        <div className="flex flex-wrap gap-3 items-end">
          <label className="text-xs ha-truth-note flex flex-col gap-1">
            Status
            <select
              className="text-sm"
              value={statusFilter}
              onChange={(e) => {
                resetFiltersPage()
                setStatusFilter(e.target.value)
              }}
            >
              <option value="completed">Completed</option>
              <option value="">All</option>
              <option value="accepted">Accepted</option>
              <option value="in_progress">In progress</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </label>
          <label className="text-xs ha-truth-note flex flex-col gap-1 flex-[2] min-w-[140px]">
            Search
            <input
              type="search"
              className="text-sm"
              value={searchQ}
              onChange={(e) => {
                resetFiltersPage()
                setSearchQ(e.target.value)
              }}
              placeholder="Pickup, dropoff, rider"
              data-testid="trips-search-input"
            />
          </label>
          <label className="text-xs ha-truth-note flex flex-col gap-1">
            From
            <input
              type="date"
              className="text-sm"
              value={fromDate}
              onChange={(e) => {
                resetFiltersPage()
                setFromDate(e.target.value)
              }}
            />
          </label>
          <label className="text-xs ha-truth-note flex flex-col gap-1">
            To
            <input
              type="date"
              className="text-sm"
              value={toDate}
              onChange={(e) => {
                resetFiltersPage()
                setToDate(e.target.value)
              }}
            />
          </label>
          <button
            type="button"
            className="ha-btn ha-btn--ghost text-sm"
            onClick={() => {
              resetFiltersPage()
              fetchTrips()
            }}
          >
            Apply
          </button>
          <button
            type="button"
            className="ha-btn ha-btn--ghost text-sm"
            onClick={handleExportCsv}
            data-testid="trips-export-csv"
          >
            Export CSV
          </button>
          <span className="text-xs ha-truth-note self-center" data-testid="trips-total-count">
            {loading ? 'Loading…' : `${total} trips`}
          </span>
        </div>
      </section>

      <section className="ha-section">

        <div className="ha-stat-grid">

          <div className="ha-stat">

            <div className="ha-stat-label">Trips today</div>

            <div className="ha-stat-value">{summary.todayTrips}</div>

          </div>

          <div className="ha-stat">

            <div className="ha-stat-label">Earnings today</div>

            <div className="ha-stat-value">{formatCurrency(summary.todayEarnings)}</div>

          </div>

          <div className="ha-stat">

            <div className="ha-stat-label">Total trips</div>

            <div className="ha-stat-value">{summary.totalTrips}</div>

          </div>

          <div className="ha-stat">

            <div className="ha-stat-label">Total earnings</div>

            <div className="ha-stat-value">{formatCurrency(summary.totalEarnings)}</div>

          </div>

        </div>

        <p className="ha-truth-note mt-2 px-0">

          Summary is derived from <code>GET /drivers/me/trips</code> rows on this page, not local mock storage.

        </p>

      </section>



      <section className="ha-section">

        <h2 className="ha-section-title">Backend completed trips</h2>

        {error ? <div className="ha-alert ha-alert--warn">{error}</div> : null}

        {loading ? (

          <div className="ha-card ha-empty">Loading backend trips…</div>

        ) : completedTrips.length === 0 ? (

          <div className="ha-card ha-empty" data-testid="trips-empty">

            <p>No trips yet.</p>

            <p className="ha-truth-note mt-2">

              Complete a backend ride from the cockpit and it will appear here.

            </p>

          </div>

        ) : (

          <ul className="ha-list" data-testid="trips-list">

            {completedTrips.map((trip) => (

              <li key={trip.id} className="ha-list-item" data-testid="trip-row">

                <div className="flex items-start justify-between gap-3">

                  <div className="min-w-0">

                    <div className="text-sm font-semibold truncate">{trip.customer_name}</div>

                    <TestRideLabel
                      lifecycleReason={trip.lifecycle_reason}
                      testId={`trip-test-label-${trip.id}`}
                    />

                    <div className="text-xs" style={{ color: 'var(--ha-muted)' }}>

                      {formatTripDate(trip.completed_at)}

                    </div>

                  </div>

                  <div className="text-right">

                    <div
                      className="text-sm font-bold"
                      style={{ color: 'var(--ha-green)' }}
                      data-testid="trip-driver-total-payout"
                    >
                      +{formatCurrency(driverPayoutDollars(trip) ?? trip.fare_amount)}
                    </div>

                    <div className="text-[10px] uppercase tracking-wide" style={{ color: '#64748b' }}>

                      Driver total payout · Completed

                    </div>

                  </div>

                </div>

                <div className="mt-3 grid gap-1 text-xs" style={{ color: 'var(--ha-text)' }}>

                  <div>

                    <span style={{ color: 'var(--ha-muted)' }}>From: </span>

                    {trip.pickup_location || '—'}

                  </div>

                  <div>

                    <span style={{ color: 'var(--ha-muted)' }}>To: </span>

                    {trip.destination || '—'}

                  </div>

                  {(trip.distance_km != null || trip.duration_minutes != null) && (

                    <div style={{ color: 'var(--ha-muted)' }}>

                      {trip.distance_km != null

                        ? formatDistanceKm(Number(trip.distance_km), units)

                        : 'Distance —'}

                      {trip.duration_minutes != null

                        ? ` · ~${trip.duration_minutes} min (stored fields, not live routing)`

                        : ''}

                    </div>

                  )}

                </div>
                {trip.pricing && (
                  <div className="mt-3 space-y-2" data-testid="trip-pricing-breakdown">
                    <RidePayoutSummary
                      pricing={trip.pricing}
                      locked={Boolean(trip.pricing.financial_locked)}
                      variant="driver"
                    />
                    <RidePayoutSummary
                      pricing={trip.pricing}
                      locked={Boolean(trip.pricing.financial_locked)}
                      variant="rider"
                    />
                  </div>
                )}

                <Link
                  to={`/driver/trips/${trip.id}/audit`}
                  className="mt-3 inline-block text-xs font-semibold"
                  style={{ color: 'var(--ha-green)' }}
                  data-testid="trip-audit-link"
                >
                  Trip audit / receipt details →
                </Link>

              </li>

            ))}

          </ul>

        )}

        {!loading && total > 0 ? (
          <TripsPager
            total={total}
            limit={PAGE_LIMIT}
            offset={offset}
            onOffsetChange={setOffset}
          />
        ) : null}

      </section>

    </AppShellLayout>

  )

}


