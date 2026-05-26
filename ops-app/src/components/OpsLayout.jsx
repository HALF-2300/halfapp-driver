import React from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'

export default function OpsLayout() {
  const { user, logout } = useAuth()

  const navClass = ({ isActive }) =>
    `px-3 py-2 rounded-lg text-sm ${isActive ? 'bg-orange-500/20 text-orange-200' : 'text-slate-300 hover:bg-white/5'}`

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/10 bg-[var(--ops-surface)]">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <div>
            <Link to="/" className="text-lg font-semibold text-orange-300">
              HalfApp Ops
            </Link>
            <p className="text-xs text-[var(--ops-muted)]">Internal control plane</p>
          </div>
          <nav className="flex items-center gap-2">
            <NavLink to="/" end className={navClass}>
              Rides
            </NavLink>
            <NavLink to="/drivers" className={navClass}>
              Drivers
            </NavLink>
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-[var(--ops-muted)]">{user?.email}</span>
            <button type="button" className="ops-btn" onClick={logout}>
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
