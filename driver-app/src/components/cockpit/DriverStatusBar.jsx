import React from 'react'
import DriverIdentityChip from './DriverIdentityChip.jsx'
import AvailabilityPill from './AvailabilityPill.jsx'

/**
 * Compact map overlay status bar — online toggle + identity; diagnostics only in dev builds.
 */
export default function DriverStatusBar({
  userName,
  stateLabel,
  isOnline,
  onlineToggleDisabled,
  onToggleOnline,
  onLogout,
  onOpenDiagnostics,
  diagnosticsOpen,
  showDiagnostics = import.meta.env.DEV,
}) {
  return (
    <header
      className="driver-status-bar map-overlay-header"
      data-testid="map-overlay-header"
    >
      <div className="driver-status-bar__brand min-w-0">
        <p className="driver-status-bar__title">Driver</p>
        <p className="driver-status-bar__subtitle truncate">{userName || 'HalfApp'}</p>
      </div>
      <AvailabilityPill
        isOnline={isOnline}
        disabled={onlineToggleDisabled}
        onToggle={onToggleOnline}
        stateLabel={stateLabel}
      />
      <DriverIdentityChip name={userName} onLogout={onLogout} compact />
      {showDiagnostics && onOpenDiagnostics && (
        <button
          type="button"
          onClick={onOpenDiagnostics}
          aria-expanded={diagnosticsOpen}
          data-testid="diagnostics-toggle"
          className="driver-status-bar__diag cockpit-pressable"
        >
          {diagnosticsOpen ? 'Close' : 'Debug'}
        </button>
      )}
    </header>
  )
}
