import React from 'react'
import DriverPortalCockpitPreview from './DriverPortalCockpitPreview.jsx'

export default function DriverPortalHero({ onEnterPortal, onCreateAccount }) {
  return (
    <section className="dp-hero dp-animate-in" id="top" data-testid="driver-portal-hero">
      <div className="dp-hero__copy">
        <p className="dp-eyebrow">HalfApp Driver Portal</p>
        <h1>
          Driver operations, readiness, and job execution in one focused cockpit.
        </h1>
        <p className="dp-hero__subtitle">
          A closed-beta driver surface for going online, reviewing jobs, completing trips, and recording
          operational truth without public-launch or payout claims.
        </p>
        <div className="dp-hero__actions">
          <button
            type="button"
            className="dp-btn dp-btn--primary dp-btn--large"
            data-testid="enter-driver-portal-cta"
            onClick={onEnterPortal}
          >
            Enter Driver Portal
          </button>
          <button
            type="button"
            className="dp-btn dp-btn--secondary dp-btn--large"
            data-testid="create-driver-account-cta"
            onClick={onCreateAccount}
          >
            Create Driver Account
          </button>
        </div>
      </div>
      <DriverPortalCockpitPreview />
    </section>
  )
}
