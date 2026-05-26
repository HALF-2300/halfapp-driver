import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import RiderAppShell from './RiderAppShell.jsx'

export default function ProfilePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = () => {
    logout()
    navigate('/login')
  }

  return (
    <RiderAppShell onSignOut={handleSignOut}>
      <div className="book-panel" data-testid="rider-profile-page">
        <h2 className="panel-title">Account</h2>
        <p className="fare-label">Read-only — backend account record for this rider.</p>

        <div className="fare-estimate">
          <div className="fare-row">
            <span className="fare-label">Name</span>
            <span className="fare-value">{user?.name || '—'}</span>
          </div>
          <div className="fare-row">
            <span className="fare-label">Email</span>
            <span className="fare-value">{user?.email || '—'}</span>
          </div>
          <div className="fare-row">
            <span className="fare-label">Rider ID</span>
            <span className="fare-value mono">#{user?.id ?? '—'}</span>
          </div>
        </div>

        <div className="field-group">
          <span className="field-label">Quick links</span>
          <Link to="/" className="btn btn--secondary" style={{ textDecoration: 'none' }}>
            ← Back to booking
          </Link>
          <Link to="/help" className="btn btn--ghost" style={{ textDecoration: 'none', marginTop: 8 }}>
            Help & safety
          </Link>
        </div>

        <button type="button" className="btn btn--ghost" onClick={handleSignOut}>
          Sign out
        </button>

        <p className="fare-label" style={{ textAlign: 'center', fontSize: 11 }}>
          HalfApp is an internal test product. No real money moves through this app.
        </p>
      </div>
    </RiderAppShell>
  )
}
