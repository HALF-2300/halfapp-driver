import { NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'

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
    <div className="app">
      <header className="app-header">
        <div className="app-header__left">
          <span className="logo">
            Half<span className="logo-accent">App</span>
          </span>
          <span className="header-tag">Rider</span>
          <nav style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 8 }}>
            <NavLink to="/" end style={navLinkStyle} data-testid="rider-nav-home">
              Home
            </NavLink>
            <NavLink to="/profile" style={navLinkStyle} data-testid="rider-nav-profile">
              Account
            </NavLink>
            <NavLink to="/help" style={navLinkStyle} data-testid="rider-nav-help">
              Help
            </NavLink>
          </nav>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="header-user">{user?.name || user?.email}</span>
          {onSignOut && (
            <button type="button" className="btn btn--ghost btn--small" onClick={onSignOut}>
              Sign out
            </button>
          )}
        </div>
      </header>
      <main className="app-main">{children}</main>
    </div>
  )
}
