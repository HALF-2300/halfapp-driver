import React from 'react'

export default function DriverPortalFooter() {
  return (
    <footer className="dp-footer" data-testid="driver-portal-footer">
      <div className="dp-footer__brand">
        <strong>HalfApp Driver Portal</strong>
        <span>Driver-side product · map-first work surface</span>
      </div>
      <div className="dp-footer__links">
        <a href="#safety">Safety</a>
        <a href="#support" id="support">
          Support
        </a>
        <a href="#terms">Terms</a>
        <a href="#privacy">Privacy</a>
      </div>
    </footer>
  )
}
