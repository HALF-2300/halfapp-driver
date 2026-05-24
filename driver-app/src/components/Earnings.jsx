import React, { useCallback, useEffect, useMemo, useState } from 'react'
import AppShellLayout from './AppShellLayout.jsx'
import driverAPI from '../utils/api'
import { driverPayoutDollars } from '../utils/ridePricingDisplay.js'
import RidePayoutSummary from './cockpit/RidePayoutSummary.jsx'
import BetaTruthNotice from './BetaTruthNotice.jsx'
import EarningsVisibilityPanel from './EarningsVisibilityPanel.jsx'
import EarningsChart from './EarningsChart.jsx'
import {
  BETA_CALCULATED_VALUE_LABEL,
  BETA_EARNINGS_SUBTITLE,
  BETA_NO_MONEY_TRUTH_ENABLED,
  BETA_OBLIGATION_DETAIL,
} from '../utils/betaTruthCopy.js'

function formatMoney(n) {
  const num = Number(n)
  if (!Number.isFinite(num)) return null
  return num.toFixed(2)
}

function formatCompletedAt(value) {
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

export default function Earnings() {
  const [earnings, setEarnings] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchEarnings = useCallback(() => {
    setLoading(true)
    setError(null)
    driverAPI
      .getEarnings()
      .then((data) => {
        setEarnings(data || null)
      })
      .catch((err) => {
        setEarnings(null)
        setError(err?.message || 'Backend earnings unavailable')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    fetchEarnings()
  }, [fetchEarnings])

  const summary = earnings?.earnings_summary || {}
  const recent = Array.isArray(earnings?.recent_rides) ? earnings.recent_rides : []
  const chartData = useMemo(
    () =>
      recent.map((ride, index) => ({
        label: ride.completed_at
          ? new Date(ride.completed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
          : `T${index + 1}`,
        earnings: driverPayoutDollars(ride) ?? Number(ride.fare_amount) ?? 0,
      })),
    [recent]
  )
  const totalStr = formatMoney(summary.total_earnings) ?? '0.00'
  const todayStr = formatMoney(summary.today_earnings) ?? '0.00'
  const weeklyStr = formatMoney(summary.weekly_earnings) ?? '0.00'

  return (
    <AppShellLayout
      testId="earnings-screen"
      title="Earnings"
      subtitle={BETA_EARNINGS_SUBTITLE}
    >
      <BetaTruthNotice variant="full" />
      <section className="ha-section">
        <div className="ha-card ha-card--accent" data-testid="earnings-hero-card">
          <div className="ha-stat-label" style={{ color: 'rgba(191, 219, 254, 0.9)' }}>
            Lifetime (backend)
          </div>
          <div className="text-4xl font-bold mt-1" data-testid="earnings-total-display">
            ${totalStr}
          </div>
          {BETA_NO_MONEY_TRUTH_ENABLED ? (
          <p className="text-[11px] mt-2 ha-truth-note" data-testid="earnings-calculated-test-label">
            {BETA_CALCULATED_VALUE_LABEL} · {BETA_OBLIGATION_DETAIL}
          </p>
          ) : null}
          <p className="text-xs mt-2" style={{ color: 'rgba(191, 219, 254, 0.85)' }}>
            Across {summary.total_rides_completed || 0} completed{' '}
            {(summary.total_rides_completed || 0) === 1 ? 'trip' : 'trips'}
          </p>
        </div>

        <div className="ha-stat-grid mt-3">
          <div className="ha-stat">
            <div className="ha-stat-label">Today</div>
            <div className="ha-stat-value">${todayStr}</div>
            <div className="ha-stat-meta">
              {summary.today_rides || 0} {(summary.today_rides || 0) === 1 ? 'trip' : 'trips'}
            </div>
          </div>
          <div className="ha-stat">
            <div className="ha-stat-label">Last 7 days</div>
            <div className="ha-stat-value">${weeklyStr}</div>
            <div className="ha-stat-meta">{summary.weekly_rides || 0} rides</div>
          </div>
        </div>
      </section>

      <section className="ha-section">
        <EarningsChart data={chartData} />
      </section>

      <section className="ha-section">
        <EarningsVisibilityPanel />
      </section>

      <section className="ha-section">
        <div className="ha-card">
          <div className="ha-stat-label">Source of truth</div>
          {loading ? (
            <p className="text-sm mt-2" style={{ color: 'var(--ha-muted)' }}>
              Checking <code>GET /drivers/earnings</code>…
            </p>
          ) : error ? (
            <div className="mt-2 text-sm">
              <span style={{ color: '#fcd34d', fontWeight: 600 }}>Unavailable</span>
              <span style={{ color: 'var(--ha-muted)' }}> · {error}</span>
              <p className="ha-truth-note">
                The driver app does not substitute local trip earnings as real backend truth.
              </p>
            </div>
          ) : (
            <div className="mt-2 text-sm" style={{ color: 'var(--ha-text)' }}>
              Live backend response from <code>GET /drivers/earnings</code>.
              <p className="ha-truth-note">
                Local browser storage may cache auth/UI state, but not completed trip earnings.
              </p>
            </div>
          )}
        </div>
      </section>

      <section className="ha-section">
        <h2 className="ha-section-title">Recent backend trips</h2>
        {loading ? (
          <div className="ha-card ha-empty">Loading backend earnings…</div>
        ) : recent.length === 0 ? (
          <div className="ha-card ha-empty" data-testid="earnings-no-recent">
            <p>No completed trips yet.</p>
            <p className="ha-truth-note mt-2">
              Complete a backend ride from the cockpit and it will appear here.
            </p>
          </div>
        ) : (
          <ul className="ha-list" data-testid="earnings-recent-list">
            {recent.slice(0, 10).map((trip) => (
              <li key={trip.id} className="ha-list-item space-y-2" data-testid="earnings-trip-row">
                <div className="flex justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold truncate">{trip.customer_name}</div>
                    <div className="text-xs" style={{ color: 'var(--ha-muted)' }}>
                      {formatCompletedAt(trip.completed_at)}
                    </div>
                    <div className="text-xs ha-truth-note">Ride #{trip.id} · driver earnings</div>
                  </div>
                  <div
                    className="text-right font-semibold"
                    style={{ color: 'var(--ha-green)' }}
                    data-testid="earnings-trip-driver-payout"
                  >
                    +${formatMoney(driverPayoutDollars(trip) ?? trip.fare_amount) ?? '0.00'}
                  </div>
                </div>
                {trip.pricing && (
                  <RidePayoutSummary
                    pricing={trip.pricing}
                    locked={Boolean(trip.pricing.financial_locked)}
                    variant="driver"
                  />
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </AppShellLayout>
  )
}

