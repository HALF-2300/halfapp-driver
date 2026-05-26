import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import RiderAppShell from './RiderAppShell.jsx'

function FaqRow({ q, a }) {
  return (
    <div className="fare-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
      <span className="fare-value" style={{ fontWeight: 600 }}>{q}</span>
      <span className="fare-label" style={{ fontSize: 12 }}>{a}</span>
    </div>
  )
}

export default function HelpPage() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  return (
    <RiderAppShell onSignOut={() => { logout(); navigate('/login') }}>
      <div className="book-panel" data-testid="rider-help-page">
        <h2 className="panel-title">Help & safety</h2>
        <p className="fare-label">
          HalfApp is an internal test product. The information below reflects current behavior, not
          public-launch policy.
        </p>

        <div className="fare-estimate" style={{ gap: 10 }}>
          <FaqRow
            q="How do I cancel a ride?"
            a="Open the ride card while it is requesting or matched and tap Cancel ride. Once the trip is in progress, contact the driver directly."
          />
          <div className="fare-divider" />
          <FaqRow
            q="My driver hasn't moved — what should I do?"
            a="Refresh the page; the driver app may have lost network briefly. If it persists, cancel the ride and request again."
          />
          <div className="fare-divider" />
          <FaqRow
            q="Is the fare a real charge?"
            a="No. Fares are calculated test values — no real money is collected through this app. A receipt is generated for testing only."
          />
          <div className="fare-divider" />
          <FaqRow
            q="Where does my ETA come from?"
            a="ETA is an estimate from stored route fields. Live road-network routing is not enabled in this build."
          />
          <div className="fare-divider" />
          <FaqRow
            q="What if there is an emergency?"
            a="HalfApp does not provide emergency response. Use your local emergency number directly."
          />
        </div>

        <div className="fare-estimate">
          <p className="field-label" style={{ marginBottom: 6 }}>Contact</p>
          <div className="fare-row">
            <span className="fare-label">Support channel</span>
            <span className="fare-value">Owner-configured (internal)</span>
          </div>
          <div className="fare-row">
            <span className="fare-label">Trip issues</span>
            <span className="fare-value">Logged via ops console</span>
          </div>
        </div>

        <Link to="/" className="btn btn--secondary" style={{ textDecoration: 'none' }}>
          ← Back to booking
        </Link>
      </div>
    </RiderAppShell>
  )
}
