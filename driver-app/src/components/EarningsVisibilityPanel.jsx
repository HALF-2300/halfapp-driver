import React, { useCallback, useEffect, useState } from 'react'
import driverAPI from '../utils/api.js'
import {
  BETA_CALCULATED_VALUE_LABEL,
  BETA_OBLIGATION_NOT_PAYOUT,
  BETA_PAYMENT_AVAILABLE_LABEL,
  BETA_PAYMENT_VISIBILITY_NOTE,
  BETA_PAYMENT_VISIBILITY_TITLE,
  BETA_PAYOUT_FAILED_LABEL,
  BETA_PAYOUT_LAST_STATUS_LABEL,
  BETA_PAYOUT_LAST_STATUS_NONE,
  BETA_PAYOUT_LAST_TIME_LABEL,
  BETA_PAYOUT_LAST_TIME_NONE,
  BETA_PAYOUT_ESTIMATED_ARRIVAL,
  BETA_PAYOUT_PAID_LABEL,
  BETA_PAYOUT_PENDING_LABEL,
  BETA_PAYOUT_VISIBILITY_NOTE,
  BETA_PAYOUT_VISIBILITY_TITLE,
} from '../utils/betaTruthCopy.js'

function formatCents(cents) {
  const n = Number(cents)
  if (!Number.isFinite(n)) return '$0.00'
  return `$${(n / 100).toFixed(2)}`
}

function formatExecutionType(type) {
  const map = {
    charge_rider: 'Customer charge',
    refund_rider: 'Refund',
    dispute: 'Dispute',
    payout_driver: 'Payout record',
  }
  return map[type] || type || '—'
}

function formatPayoutTime(iso) {
  if (!iso) return BETA_PAYOUT_LAST_TIME_NONE
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return BETA_PAYOUT_LAST_TIME_NONE
  return d.toLocaleString()
}

function TextRow({ label, value, muted = false, testId }) {
  return (
    <div className="flex justify-between gap-3 text-sm" data-testid={testId}>
      <span className={muted ? 'ha-truth-note' : ''}>{label}</span>
      <span className={muted ? 'ha-truth-note' : ''} style={!muted ? { color: 'var(--ha-text)' } : undefined}>
        {value}
      </span>
    </div>
  )
}

function Row({ label, cents, negative = false, muted = false, bold = false, testId }) {
  return (
    <div className="flex justify-between gap-3 text-sm" data-testid={testId}>
      <span className={muted ? 'ha-truth-note' : ''} style={{ color: muted ? undefined : 'var(--ha-text)' }}>
        {label}
      </span>
      <span
        className={[
          bold ? 'font-semibold' : '',
          negative ? 'text-red-400' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        style={!negative && !muted ? { color: 'var(--ha-green)' } : undefined}
      >
        {negative && Number(cents) > 0 ? '−' : ''}
        {formatCents(cents)}
      </span>
    </div>
  )
}

export default function EarningsVisibilityPanel({ compact = false, className = '' }) {
  const [data, setData] = useState(null)
  const [items, setItems] = useState([])
  const [payouts, setPayouts] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [recon, executions, payoutList] = await Promise.all([
        driverAPI.getPaymentReconciliation(),
        compact ? Promise.resolve(null) : driverAPI.getPaymentExecutions(),
        compact ? Promise.resolve(null) : driverAPI.getPayouts(),
      ])
      setData(recon || null)
      setItems(executions?.items || [])
      setPayouts(payoutList?.items || [])
    } catch (err) {
      setData(null)
      setItems([])
      setPayouts([])
      setError(err?.message || 'Payment visibility unavailable')
    } finally {
      setLoading(false)
    }
  }, [compact])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <div
        className={`ha-card ha-empty text-sm ${className}`}
        data-testid="earnings-visibility-loading"
      >
        Loading payment visibility…
      </div>
    )
  }

  if (error) {
    return (
      <div className={`ha-card ${className}`} data-testid="earnings-visibility-error">
        <p className="text-sm" style={{ color: '#fcd34d' }}>
          {error}
        </p>
        <button type="button" className="ha-btn ha-btn--ghost mt-2 text-xs" onClick={load}>
          Retry
        </button>
      </div>
    )
  }

  if (!data) return null

  const wrapperClass = compact
    ? `rounded-xl border border-white/10 bg-[#0f172a]/90 p-3 space-y-2 ${className}`
    : `ha-card space-y-3 ${className}`

  return (
    <div className={wrapperClass} data-testid="earnings-visibility-panel">
      <div>
        <h2
          className={compact ? 'text-[12px] font-semibold text-[#E2E8F0]' : 'ha-section-title'}
          data-testid="earnings-visibility-title"
        >
          {BETA_PAYMENT_VISIBILITY_TITLE}
        </h2>
        {!compact && (
          <p className="text-xs ha-truth-note mt-1" data-testid="earnings-visibility-pricing-earned">
            {BETA_CALCULATED_VALUE_LABEL}: {formatCents(data.pricing_earned_cents)} · {BETA_OBLIGATION_NOT_PAYOUT}
          </p>
        )}
      </div>

      <Row
        label="Collected (provider processed)"
        cents={data.collected_cents ?? data.execution_collected_cents}
        testId="earnings-visibility-collected"
      />
      <Row
        label="Pending (not finalized)"
        cents={data.pending_cents ?? data.execution_pending_collection_cents}
        muted
        testId="earnings-visibility-pending"
      />
      <Row
        label="Refunds"
        cents={data.refunded_cents ?? data.execution_refunded_cents}
        negative
        testId="earnings-visibility-refunded"
      />
      <Row
        label="Disputes"
        cents={data.disputed_cents ?? data.execution_disputed_cents}
        negative
        testId="earnings-visibility-disputed"
      />

      <div className={compact ? 'border-t border-white/10 pt-2 mt-1' : 'border-t border-[var(--ha-border)] pt-2 mt-1'}>
        <Row
          label={BETA_PAYMENT_AVAILABLE_LABEL}
          cents={data.available_cents ?? data.execution_refundable_cents}
          bold
          testId="earnings-visibility-available"
        />
      </div>

      {data.provider_payout_visible && (
        <div
          className={compact ? 'border-t border-white/10 pt-2 mt-1 space-y-2' : 'border-t border-[var(--ha-border)] pt-2 mt-1 space-y-2'}
          data-testid="earnings-visibility-payout-section"
        >
          <div className={compact ? 'text-[11px] font-semibold text-[#E2E8F0]' : 'ha-stat-label'}>
            {BETA_PAYOUT_VISIBILITY_TITLE}
          </div>
          <Row
            label={BETA_PAYOUT_PAID_LABEL}
            cents={data.payout_paid_cents}
            testId="earnings-visibility-payout-paid"
          />
          <Row
            label={BETA_PAYOUT_PENDING_LABEL}
            cents={data.payout_pending_cents}
            muted
            testId="earnings-visibility-payout-pending"
          />
          <Row
            label={BETA_PAYOUT_FAILED_LABEL}
            cents={data.payout_failed_cents ?? 0}
            negative
            testId="earnings-visibility-payout-failed"
          />
          <TextRow
            label={BETA_PAYOUT_LAST_STATUS_LABEL}
            value={data.payout_last_status || BETA_PAYOUT_LAST_STATUS_NONE}
            muted={!data.payout_last_status}
            testId="earnings-visibility-payout-last-status"
          />
          <TextRow
            label={BETA_PAYOUT_LAST_TIME_LABEL}
            value={formatPayoutTime(data.payout_last_at)}
            muted={!data.payout_last_at}
            testId="earnings-visibility-payout-last-time"
          />
          <p className="text-[11px] ha-truth-note" data-testid="earnings-visibility-payout-note">
            {BETA_PAYOUT_VISIBILITY_NOTE}
          </p>
        </div>
      )}

      <p className="text-[11px] ha-truth-note" data-testid="earnings-visibility-disclaimer">
        {data.display_note || BETA_PAYMENT_VISIBILITY_NOTE}
      </p>

      {!compact && payouts.length > 0 && (
        <div className="mt-2" data-testid="earnings-visibility-payouts-list">
          <div className="ha-stat-label mb-2">Recent provider payouts</div>
          <ul className="ha-list max-h-40 overflow-y-auto">
            {payouts.slice(0, 10).map((row) => (
              <li
                key={row.payout_id}
                className="ha-list-item flex justify-between gap-2 text-xs"
                data-testid="earnings-visibility-payout-row"
              >
                <span>
                  {row.status}
                  <span className="ha-truth-note block">{row.payout_id}</span>
                  {row.arrival_date ? (
                    <span className="ha-truth-note block">
                      {BETA_PAYOUT_ESTIMATED_ARRIVAL}:{' '}
                      {new Date(row.arrival_date).toLocaleDateString()}
                    </span>
                  ) : null}
                </span>
                <span className="font-medium">{formatCents(row.amount_cents)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!compact && items.length > 0 && (
        <div className="mt-2" data-testid="earnings-visibility-executions-list">
          <div className="ha-stat-label mb-2">Recent execution rows</div>
          <ul className="ha-list max-h-48 overflow-y-auto">
            {items.slice(0, 15).map((row) => (
              <li
                key={row.id}
                className="ha-list-item flex justify-between gap-2 text-xs"
                data-testid="earnings-visibility-execution-row"
              >
                <span>
                  {formatExecutionType(row.execution_type)} · ride #{row.ride_id}
                  <span className="ha-truth-note block">{row.status}</span>
                </span>
                <span className="font-medium">{formatCents(row.amount_cents)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
