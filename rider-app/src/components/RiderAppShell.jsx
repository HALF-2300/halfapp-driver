import { useAuth } from '../hooks/useAuth.jsx'

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
