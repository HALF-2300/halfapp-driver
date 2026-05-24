import React from 'react'
import BottomNavigation from './BottomNavigation.jsx'

/**
 * Shared HalfApp shell for authenticated non-map screens (earnings, trips, account).
 * Cockpit (/driver) uses map-first layout and does not use this wrapper.
 */
export default function AppShellLayout({
  title,
  subtitle,
  testId,
  headerAction,
  children,
}) {
  return (
    <div className="driver-app-shell" data-testid={testId}>
      <header className="driver-app-shell__header">
        <div className="driver-app-shell__header-row">
          <div>
            <p className="ha-shell-eyebrow">HalfApp Driver</p>
            <h1 className="ha-shell-title">{title}</h1>
            {subtitle ? <p className="ha-shell-subtitle">{subtitle}</p> : null}
          </div>
          {headerAction ? <div className="driver-app-shell__header-action">{headerAction}</div> : null}
        </div>
      </header>
      <main className="driver-app-shell__main">{children}</main>
      <BottomNavigation />
    </div>
  )
}
