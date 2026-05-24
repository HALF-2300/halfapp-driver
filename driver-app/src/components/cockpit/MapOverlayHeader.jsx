import React from 'react'
import DriverIdentityChip from './DriverIdentityChip.jsx'
import AvailabilityPill from './AvailabilityPill.jsx'

export default function MapOverlayHeader({
  userName,
  stateLabel,
  isOnline,
  onlineToggleDisabled,
  onToggleOnline,
  onLogout,
  onOpenDiagnostics,
  diagnosticsOpen,
}) {
  return (
    <header className="map-overlay-header" data-testid="map-overlay-header">
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-[15px] font-semibold text-[#F8FAFC]">HalfApp</h1>
        <p className="text-[11px] text-[#94A3B8]">Driver</p>
      </div>
      <DriverIdentityChip name={userName} onLogout={onLogout} />
      <AvailabilityPill
        isOnline={isOnline}
        disabled={onlineToggleDisabled}
        onToggle={onToggleOnline}
        stateLabel={stateLabel}
      />
      <button
        type="button"
        onClick={onOpenDiagnostics}
        aria-expanded={diagnosticsOpen}
        data-testid="diagnostics-toggle"
        className="cockpit-pressable shrink-0 rounded-full border border-white/10 px-2.5 py-1.5 text-[11px] font-medium text-[#AAB6C8] hover:text-[#F8FAFC]"
      >
        {diagnosticsOpen ? 'Close' : 'Advanced'}
      </button>
    </header>
  )
}
