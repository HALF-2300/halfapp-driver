import React from 'react'
import { DEFAULT_PLATFORM_SERVICE_FEE_CENTS, formatCents } from '../../utils/ridePricingDisplay.js'

function Line({ label, cents, testId, emphasize, hint }) {
  return (
    <div className="space-y-0.5" data-testid={testId}>
      <div className={`flex justify-between gap-3 text-[12px] ${emphasize ? 'font-semibold' : ''}`}>
        <span className="text-[#AAB6C8]">{label}</span>
        <span className={`text-right font-medium ${emphasize ? 'text-emerald-300' : 'text-[#F8FAFC]'}`}>
          {formatCents(cents ?? 0)}
        </span>
      </div>
      {hint && <p className="text-[10px] text-[#64748B]">{hint}</p>}
    </div>
  )
}

function OptionalLine({ label, cents, testId }) {
  if (!cents) return null
  return <Line label={label} cents={cents} testId={testId} />
}

/**
 * Backend pricing ledger summary — integer cents from `ride.pricing` only (no client-side billing).
 *
 * @param {{ pricing: Record<string, unknown> | null, locked?: boolean, variant?: 'driver' | 'rider' | 'ledger' | 'quote' | 'final' }} props
 */
export default function RidePayoutSummary({ pricing, locked = false, variant = 'ledger' }) {
  if (!pricing) {
    return (
      <div
        className="rounded-[20px] border border-white/10 bg-white/[0.04] p-3"
        data-testid="ride-payout-summary"
        data-pricing-state="unavailable"
      >
        <p className="text-[12px] text-[#94A3B8]">Payout summary pending from backend.</p>
      </div>
    )
  }

  const isFinal = variant === 'final' || (variant === 'ledger' && locked)
  const showDriver =
    variant === 'driver' || variant === 'final' || variant === 'ledger' || variant === 'quote'
  const showRider = variant === 'rider' || variant === 'final' || variant === 'ledger' || variant === 'quote'

  const titles = {
    driver: 'Recorded driver obligation',
    rider: 'Customer receipt',
    quote: 'Obligation preview',
    final: 'Trip completed',
    ledger: isFinal ? 'Recorded obligation (locked)' : 'Obligation preview',
  }
  const title = titles[variant] ?? titles.ledger

  const passThroughLines = [
    { label: 'City fee (pass-through)', cents: pricing.city_fee_cents, testId: 'rider-city-fee' },
    { label: 'Airport fee (pass-through)', cents: pricing.airport_fee_cents, testId: 'rider-airport-fee' },
    { label: 'Toll (pass-through)', cents: pricing.toll_cents, testId: 'rider-toll-fee' },
    {
      label: 'Accessibility fee (pass-through)',
      cents: pricing.accessibility_fee_cents,
      testId: 'rider-accessibility-fee',
    },
  ]

  return (
    <div
      className="rounded-[20px] border border-white/10 bg-white/[0.04] p-3 space-y-2"
      data-testid="ride-payout-summary"
      data-pricing-variant={variant}
      data-pricing-state={locked ? 'locked' : 'open'}
      data-financial-locked={locked ? 'true' : 'false'}
    >
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[#7BA3FF]">{title}</p>
        {locked && (
          <span
            className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-300"
            data-testid="pricing-financial-locked"
          >
            financial_locked
          </span>
        )}
      </div>

      {showDriver && (
        <div className="space-y-2" data-testid="driver-earnings-breakdown">
          {isFinal && (
            <p className="text-[11px] text-emerald-300/90" data-testid="ride-status-completed">
              Ride status: Completed
            </p>
          )}
          <Line
            label="Driver obligation base"
            cents={pricing.driver_ride_payout_cents ?? pricing.driver_commission_cents}
            testId="driver-ride-payout"
            hint="After platform commission on driver-shareable fare"
          />
          <Line
            label="Tips"
            cents={pricing.tip_cents}
            testId="driver-tips"
            hint="Tips are driver money and are not commissioned"
          />
          <Line
            label="Recorded driver obligation"
            cents={pricing.driver_total_payout_cents ?? pricing.driver_earnings_cents}
            testId="driver-total-payout"
            emphasize
          />
          {locked && pricing.locked_at && (
            <p className="text-[10px] text-[#64748B]" data-testid="financial-locked-at">
              Locked at {String(pricing.locked_at)}
            </p>
          )}
        </div>
      )}

      {showRider && (
        <div
          className={`space-y-2 ${showDriver ? 'border-t border-white/10 pt-2' : ''}`}
          data-testid="rider-receipt-breakdown"
        >
          <Line
            label="Ride fare"
            cents={pricing.driver_shareable_fare_cents}
            testId="rider-ride-fare"
            hint="Driver-shareable fare (not the same as driver payout)"
          />
          <Line
            label="Platform service fee"
            cents={pricing.platform_service_fee_cents ?? DEFAULT_PLATFORM_SERVICE_FEE_CENTS}
            testId="rider-platform-service-fee"
          />
          {passThroughLines.map((row) => (
            <OptionalLine key={row.testId} {...row} />
          ))}
          <Line label="Tips" cents={pricing.tip_cents} testId="rider-tips" />
          <Line
            label="Customer total"
            cents={pricing.customer_total_cents ?? pricing.total_rider_charge_cents}
            testId="rider-customer-total"
            emphasize
          />
          <Line
            label="Platform commission"
            cents={pricing.platform_commission_cents}
            testId="rider-platform-commission"
            hint="Applies to ride fare only — not pass-through fees or tips"
          />
        </div>
      )}

      {variant === 'ledger' && (
        <div className="border-t border-white/10 pt-2 space-y-2">
          <Line
            label="Platform revenue"
            cents={pricing.platform_revenue_cents ?? pricing.platform_earnings_cents}
            testId="payout-platform-revenue"
          />
        </div>
      )}
    </div>
  )
}
