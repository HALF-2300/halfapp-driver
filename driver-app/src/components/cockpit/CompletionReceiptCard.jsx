import React from 'react'
import { formatCurrency } from '../../theme/halfAppTheme.js'

export default function CompletionReceiptCard({ ride, amount, onDismiss }) {
  return (
    <div
      className="rounded-xl border border-emerald-500/30 bg-emerald-950/45 p-3"
      data-testid="completion-receipt-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-emerald-300">
            Trip completed
          </p>
          <p className="mt-1 text-[16px] font-semibold text-[#F8FAFC]">
            Fare obligation recorded
          </p>
          <p className="mt-1 text-[12px] text-emerald-100" data-testid="completion-receipt-manual-review">
            Payout not executed. Manual review required.
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-[10px] uppercase tracking-wide text-emerald-200/80">
            Recorded obligation
          </p>
          <p className="text-[20px] font-bold text-emerald-100" data-testid="completion-recorded-obligation">
            {amount == null ? 'Pending review' : formatCurrency(amount)}
          </p>
        </div>
      </div>
      {ride?.riderName ? (
        <p className="mt-2 truncate text-[12px] text-emerald-100/80">
          Job with {ride.riderName}
        </p>
      ) : null}
      {onDismiss ? (
        <button
          type="button"
          className="mt-3 min-h-[36px] text-[12px] font-medium text-emerald-200 hover:text-emerald-100"
          onClick={onDismiss}
          data-testid="completion-receipt-dismiss"
        >
          Dismiss receipt
        </button>
      ) : null}
    </div>
  )
}
