import React from 'react'
import { formatCurrency } from '../../theme/halfAppTheme.js'
import MetricMiniChip from './MetricMiniChip.jsx'

export default function DriverAvailabilityCard({
  title = 'Available',
  subtitle = 'Waiting for requests nearby.',
  todayTrips,
  totalTrips,
  todayEarnings,
  onSync,
  loadingBackend,
  backendError,
  backendHideNotice,
  expanded,
  onToggleExpand,
  presenceSynced,
}) {
  return (
    <div data-testid="driver-availability-card" className="w-full">
      <div className="flex w-full items-start justify-between gap-2">
        <button
          type="button"
          onClick={onToggleExpand}
          className="min-w-0 flex-1 text-left"
          aria-expanded={expanded}
        >
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-emerald-300/90">
            {title}
          </p>
          <div
            data-testid="availability-title"
            className="mt-0.5 text-[16px] font-semibold leading-snug text-[#F8FAFC]"
          >
            {subtitle}
          </div>
          <p className="mt-1 text-[12px] text-[#94A3B8]">
            Trips {todayTrips} · {formatCurrency(todayEarnings)} today
          </p>
        </button>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {presenceSynced && (
            <span
              data-testid="presence-synced-label"
              className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-300"
            >
              Synced
            </span>
          )}
          <button
            type="button"
            onClick={onSync}
            disabled={loadingBackend}
            data-testid="sync-marketplace-btn"
            className="cockpit-pressable rounded-full border border-white/10 px-2.5 py-1 text-[11px] font-medium text-[#AAB6C8] hover:text-[#F8FAFC] disabled:opacity-50"
            aria-label="Sync with server"
          >
            ↻
          </button>
        </div>
      </div>
      {expanded && (
        <div className="mt-3 grid grid-cols-2 gap-2">
          <MetricMiniChip label="Trips today" value={String(todayTrips)} testId="metric-trips-today" />
          <MetricMiniChip label="Total trips" value={String(totalTrips)} testId="metric-total-trips" />
        </div>
      )}
      {backendError && (
        <p className="mt-2 text-[11px] text-amber-300" data-testid="accept-ride-error">
          {backendError}
        </p>
      )}
      {backendHideNotice && (
        <p className="mt-2 text-[11px] text-amber-300" data-testid="backend-hide-notice">
          {backendHideNotice}
        </p>
      )}
    </div>
  )
}
