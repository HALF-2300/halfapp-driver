import React from 'react'
import { formatCurrency } from '../../theme/halfAppTheme.js'

export default function CompletionReceiptCard({ ride, amount, onDismiss }) {
  return (
    <div
      className="rounded-xl border p-3"
      style={{
        borderColor: 'rgba(52,211,153,0.35)',
        background: 'linear-gradient(135deg, rgba(6,40,28,0.9) 0%, rgba(2,20,15,0.85) 100%)',
      }}
      data-testid="completion-receipt-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em]" style={{ color: '#34d399' }}>
            Trip completed
          </p>
          <p className="mt-1 text-[16px] font-semibold leading-snug" style={{ color: '#f0fdf4' }}>
            Fare obligation recorded
          </p>
          {ride?.riderName ? (
            <p className="mt-0.5 truncate text-[12px]" style={{ color: 'rgba(134,239,172,0.8)' }}>
              Job with {ride.riderName}
            </p>
          ) : null}
          <p className="mt-1 text-[12px]" style={{ color: 'rgba(134,239,172,0.85)' }} data-testid="completion-receipt-manual-review">
            Payout not executed. Manual review required.
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-[9px] font-semibold uppercase tracking-wide" style={{ color: 'rgba(134,239,172,0.7)' }}>
            Recorded obligation
          </p>
          <p
            className="text-[24px] font-bold leading-none mt-0.5 tabular-nums"
            style={{ color: '#34d399' }}
            data-testid="completion-recorded-obligation"
          >
            {amount == null ? 'Pending' : formatCurrency(amount)}
          </p>
        </div>
      </div>
      {onDismiss ? (
        <button
          type="button"
          className="mt-3 min-h-[36px] w-full text-center text-[12px] font-medium"
          style={{ color: 'rgba(134,239,172,0.7)' }}
          onClick={onDismiss}
          data-testid="completion-receipt-dismiss"
        >
          Dismiss
        </button>
      ) : null}
    </div>
  )
}
