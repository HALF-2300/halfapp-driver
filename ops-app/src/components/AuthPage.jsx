import React, { useState } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'

export default function AuthPage() {
  const { login, isLoading, error, clearError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const onSubmit = async (event) => {
    event.preventDefault()
    clearError()
    await login(email.trim(), password)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md rounded-2xl border border-white/10 bg-[var(--ops-surface)] p-8"
      >
        <p className="text-xs uppercase tracking-widest text-orange-400">HalfApp Ops</p>
        <h1 className="mt-2 text-2xl font-semibold">Operator sign in</h1>
        <p className="mt-2 text-sm text-[var(--ops-muted)]">
          Internal control plane — live backend data only.
        </p>

        <label className="mt-6 block text-sm">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2"
          />
        </label>

        <label className="mt-4 block text-sm">
          Password
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2"
          />
        </label>

        {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}

        <button type="submit" disabled={isLoading} className="ops-btn ops-btn-primary mt-6 w-full">
          {isLoading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
