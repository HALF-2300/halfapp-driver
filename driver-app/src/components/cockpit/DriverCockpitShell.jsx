import React from 'react'

/**
 * Map-first full-screen shell; centered phone frame on wide viewports.
 */
export default function DriverCockpitShell({ children, map, testId = 'map-home' }) {
  return (
    <div data-testid="driver-cockpit-root" className="driver-cockpit-root">
      <div className="driver-cockpit-frame">
        <div data-testid="driver-shell" className="relative h-full w-full">
          <div className="cockpit-shell text-[#F8FAFC]" data-testid={testId}>
            <div className="cockpit-map" data-testid="experimental-map-panel">
              {map}
            </div>
            <div className="cockpit-overlay">{children}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
