import React from 'react'

/** Abstract cockpit preview — visualization only, no marketplace claims */
export default function DriverPortalCockpitPreview() {
  return (
    <div className="dp-cockpit-preview dp-float-subtle" aria-hidden data-testid="driver-portal-cockpit-preview">
      <div className="dp-cockpit-preview__map">
        <div className="dp-cockpit-preview__grid" />
        <div className="dp-cockpit-preview__route" />
        <div className="dp-cockpit-preview__pin dp-cockpit-preview__pin--driver" />
        <div className="dp-cockpit-preview__pin dp-cockpit-preview__pin--pickup" />
      </div>
      <div className="dp-cockpit-preview__header">
        <span className="dp-cockpit-preview__brand">HalfApp</span>
        <span className="dp-cockpit-preview__pill">Online</span>
      </div>
      <div className="dp-cockpit-preview__sheet">
        <strong>Available</strong>
        <span>Backend-owned · Device location</span>
        <div className="dp-cockpit-preview__metrics">
          <span>Trips 0</span>
          <span>$0.00 today</span>
        </div>
      </div>
      <div className="dp-cockpit-preview__dock" />
    </div>
  )
}
