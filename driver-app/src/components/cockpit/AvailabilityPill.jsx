import React from 'react'

export default function AvailabilityPill({ isOnline, disabled, onToggle, stateLabel }) {
  return (
    <div
      data-testid="availability-pill"
      className="flex shrink-0 items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.05] px-2 py-1"
    >
      <span
        data-testid="driver-state-badge"
        className={`text-[10px] font-semibold uppercase tracking-wide ${
          isOnline ? 'text-emerald-300' : 'text-slate-400'
        }`}
      >
        {stateLabel}
      </span>
      <button
        type="button"
        onClick={onToggle}
        disabled={disabled}
        data-testid="online-toggle"
        aria-pressed={isOnline}
        aria-label={isOnline ? 'Go offline' : 'Go online'}
        className={`online-toggle-track relative min-h-[36px] min-w-[46px] rounded-full p-1.5 transition-colors duration-200 ${
          isOnline ? 'bg-emerald-400' : 'bg-slate-600'
        } disabled:opacity-50`}
      >
        <span
          className={`online-toggle-thumb absolute top-1/2 left-1.5 h-6 w-6 -translate-y-1/2 rounded-full bg-white shadow transition-transform duration-200 ${
            isOnline ? 'translate-x-[16px]' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  )
}
