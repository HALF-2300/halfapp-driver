import React from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import InternalBetaRibbon from './platform/InternalBetaRibbon.jsx'

export default function OpsLayout() {
  const { user, logout } = useAuth()

  const navClass = ({ isActive }) =>
    `ops-nav-link ${isActive ? 'ops-nav-link--active' : ''}`

  return (
    <div className="min-h-screen ops-command-shell" data-testid="ops-command-shell">
      <header className="ops-command-header border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="ops-command-eyebrow">HalfApp Command Platform</p>
            <Link to="/" className="ops-command-title" data-testid="ops-command-title">
              Ops control room
            </Link>
            <p className="text-xs text-[var(--ops-muted)] mt-0.5">Live truth for every people-transport ride · operator console</p>
          </div>
          <nav className="flex items-center gap-2">
            <NavLink to="/" end className={navClass}>
              Rides
            </NavLink>
            <NavLink to="/drivers" className={navClass}>
              Drivers
            </NavLink>
            <NavLink to="/deliveries" className={navClass} data-testid="ops-nav-deliveries">
              Deliveries
            </NavLink>
            <NavLink to="/readiness" className={navClass}>
              Readiness
            </NavLink>
            <NavLink to="/support" className={navClass} data-testid="ops-nav-support">
              Support
            </NavLink>
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-[var(--ops-muted)]">{user?.email}</span>
            <button type="button" className="ops-btn" onClick={logout}>
              Log out
            </button>
          </div>
          </div>
          <InternalBetaRibbon detail="Truth board · not public launch" />
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 ops-command-main">
        <Outlet />
      </main>
    </div>
  )
}
