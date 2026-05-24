import React from 'react'

export default function DriverPortalNav({ onSignIn, onGetStarted }) {
  return (
    <header className="dp-nav" data-testid="driver-portal-nav">
      <a href="#top" className="dp-brand">
        <div className="dp-brand__logo" aria-hidden>
          H
        </div>
        <div className="dp-brand__text">
          <strong>HalfApp</strong>
          <span>Driver Portal</span>
        </div>
      </a>

      <nav className="dp-nav__links" aria-label="Driver portal">
        <a href="#how">How it works</a>
        <a href="#safety">Safety / Trust</a>
      </nav>

      <div className="dp-nav__actions">
        <button type="button" className="dp-btn dp-btn--ghost" onClick={onSignIn}>
          Sign In
        </button>
        <button type="button" className="dp-btn dp-btn--primary" onClick={onGetStarted}>
          Get Started
        </button>
      </div>
    </header>
  )
}
