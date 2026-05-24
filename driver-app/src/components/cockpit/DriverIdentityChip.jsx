import React from 'react'

export default function DriverIdentityChip({ name, onLogout, compact = false }) {
  const initial = (name || 'D').slice(0, 1).toUpperCase()
  return (
    <div className="flex min-w-0 items-center gap-2">
      <div
        data-testid="driver-identity-chip"
        className={`flex min-w-0 items-center rounded-full border border-white/10 bg-white/[0.06] py-1 pl-1 ${
          compact ? 'pr-1' : 'pr-2.5 gap-2'
        }`}
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#3B82F6] text-xs font-semibold text-white">
          {initial}
        </div>
        {!compact && (
          <span className="max-w-[120px] truncate text-[13px] font-semibold text-[#F8FAFC]">{name || 'Driver'}</span>
        )}
      </div>
      {onLogout && (
        <button
          type="button"
          onClick={onLogout}
          className="cockpit-pressable shrink-0 rounded-full border border-white/10 px-2.5 py-1 text-[11px] font-medium text-[#AAB6C8] hover:text-[#F8FAFC]"
          aria-label="Logout"
          data-testid="logout-btn"
        >
          Out
        </button>
      )}
    </div>
  )
}
