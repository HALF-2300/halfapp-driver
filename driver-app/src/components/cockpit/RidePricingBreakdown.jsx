import React from 'react'
import {
  buildDriverEarningsRows,
  buildPricingLedgerDebugRows,
  buildRiderReceiptRows,
  resolveRidePricing,
} from '../../utils/ridePricingDisplay.js'

function BreakdownRow({ label, value, testId, hint, emphasize }) {
  return (
    <div className="space-y-0.5" data-testid={testId}>
      <div className={`flex justify-between gap-3 text-[12px] ${emphasize ? 'font-semibold text-[#F8FAFC]' : ''}`}>
        <span className={emphasize ? 'text-[#F8FAFC]' : 'text-[#AAB6C8]'}>{label}</span>
        <span className="text-right text-[#F8FAFC]">{value}</span>
      </div>
      {hint && <p className="text-[10px] text-[#64748B]">{hint}</p>}
    </div>
  )
}

/**
 * @param {'driver' | 'rider' | 'debug'} props.variant
 * @param {Record<string, unknown> | null | undefined} props.ride
 * @param {Record<string, unknown> | null | undefined} [props.pricing]
 * @param {string} [props.className]
 */
export default function RidePricingBreakdown({ variant = 'driver', ride, pricing: pricingProp, className = '' }) {
  const pricing = pricingProp ?? resolveRidePricing(ride)
  if (!pricing) return null

  if (variant === 'debug') {
    const rows = buildPricingLedgerDebugRows(pricing)
    if (!rows) return null
    return (
      <div
        className={`rounded-[16px] border border-amber-400/25 bg-amber-950/30 p-3 space-y-1.5 ${className}`}
        data-testid="pricing-ledger-debug"
      >
        <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-200/90">
          Pricing ledger (internal)
        </p>
        {rows.map((row) => (
          <div key={row.label} className="flex justify-between gap-2 font-mono text-[10px]">
            <span className="text-amber-100/70">{row.label}</span>
            <span className="text-amber-50">{row.value}</span>
          </div>
        ))}
      </div>
    )
  }

  if (variant === 'rider') {
    const receipt = buildRiderReceiptRows(pricing)
    if (!receipt) return null
    return (
      <div
        className={`rounded-[18px] border border-white/10 bg-white/[0.04] p-3 space-y-2 ${className}`}
        data-testid="rider-receipt-breakdown"
      >
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[#94A3B8]">{receipt.title}</p>
        {receipt.rows.map((row) => (
          <BreakdownRow key={row.label} {...row} />
        ))}
      </div>
    )
  }

  const driverView = buildDriverEarningsRows(pricing)
  if (!driverView) return null
  return (
    <div
      className={`rounded-[18px] border border-emerald-500/25 bg-emerald-950/40 p-3 space-y-2 ${className}`}
      data-testid="driver-earnings-breakdown"
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-300/90">
        Driver earnings · {driverView.statusLabel}
      </p>
      {driverView.rows.map((row) => (
        <BreakdownRow key={row.label} {...row} />
      ))}
    </div>
  )
}
