import { NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import InternalBetaRibbon from './platform/InternalBetaRibbon.jsx'

const navLinkStyle = ({ isActive }) => ({
  color: isActive ? 'var(--blue)' : 'var(--t2)',
  fontSize: 12,
  textDecoration: 'none',
  fontWeight: isActive ? 600 : 500,
  padding: '4px 8px',
  borderRadius: 6,
  background: isActive ? 'var(--surface2)' : 'transparent',
})

export default function RiderAppShell({ children, onSignOut }) {
  const { user } = useAuth()

  return (
    <div className="app rider-command-shell" data-testid="rider-app-shell">
      <header className="app-header rider-command-header">
        <div className="rider-command-header__row">
          <div className="app-header__left">
            <div>
              <p className="rider-command-eyebrow">HalfApp rider</p>
              <span className="logo">
                Half<span className="logo-accent">App</span>
              </span>
              <span className="header-tag">Rider</span>
              <p className="rider-command-tagline">Clear status · honest receipt</p>
            </div>
            <nav className="rider-command-nav">
              <NavLink to="/" end style={navLinkStyle} data-testid="rider-nav-home">
                Home
              </NavLink>
              <NavLink to="/profile" style={navLinkStyle} data-testid="rider-nav-profile">
                Account
              </NavLink>
              <NavLink to="/delivery" style={navLinkStyle} data-testid="rider-nav-delivery">
                Delivery
              </NavLink>
              <NavLink to="/help" style={navLinkStyle} data-testid="rider-nav-help">
                Help
              </NavLink>
              <NavLink to="/notifications" style={navLinkStyle} data-testid="rider-nav-notifications">
                Updates
              </NavLink>
            </nav>
          </div>
          <div className="rider-command-header__actions">
            <span className="header-user">{user?.name || user?.email}</span>
            {onSignOut && (
              <button type="button" className="btn btn--ghost btn--small" onClick={onSignOut}>
                Sign out
              </button>
            )}
          </div>
        </div>
        <InternalBetaRibbon detail="Simulated payment only when labeled · no guaranteed ETA" />
      </header>
      <main className="app-main">{children}</main>
    </div>
  )
}
