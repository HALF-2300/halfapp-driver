import React from 'react'
import PrimaryRideActionButton from './PrimaryRideActionButton.jsx'

export default function DriverReadinessCard({
  readiness,
  onAction,
  loading,
  compact = false,
}) {
  const ready = Boolean(readiness?.canGoOnline)
  const primary = readiness?.primaryBlocker
  const blockers = readiness?.blockers || []

  return (
    <div
      className={`rounded-xl border ${
        ready ? 'border-emerald-500/30 bg-emerald-950/35' : 'border-amber-500/45 bg-amber-950/45'
      } p-3`}
      data-testid="driver-readiness-card"
      data-readiness={ready ? 'ready' : 'blocked'}
    >
      <p className={`text-[10px] font-semibold uppercase tracking-[0.14em] ${
        ready ? 'text-emerald-300' : 'text-amber-300'
      }`}>
        {readiness?.statusLabel || 'Checking readiness'}
      </p>
      <p className="mt-1 text-[16px] font-semibold leading-snug text-[#F8FAFC]">
        {readiness?.headline || 'Checking driver setup'}
      </p>
      {!ready && primary ? (
        <p className="mt-1 text-[13px] text-amber-100" data-testid="driver-readiness-reason">
          Reason: {primary.label}
        </p>
      ) : (
        <p className="mt-1 text-[13px] text-emerald-100" data-testid="driver-readiness-ready">
          Profile, vehicle, documents, insurance, and beta approval are clear.
          Manual operations readiness is recorded.
        </p>
      )}
      {!ready && blockers.length > 1 && !compact ? (
        <ul className="mt-2 space-y-1 text-[12px] text-amber-100/90" data-testid="driver-readiness-blockers">
          {blockers.slice(1).map((item) => (
            <li key={item.code}>- {item.label}</li>
          ))}
        </ul>
      ) : null}
      <div className="mt-3">
        <PrimaryRideActionButton
          onClick={onAction}
          disabled={loading}
          tone={ready ? 'success' : 'neutral'}
          testId={ready ? 'readiness-go-online-btn' : 'readiness-action-btn'}
        >
          {ready ? 'Go online' : primary?.actionLabel || 'Complete driver setup'}
        </PrimaryRideActionButton>
      </div>
    </div>
  )
}
