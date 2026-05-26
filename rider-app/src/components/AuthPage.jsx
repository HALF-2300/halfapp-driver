import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'

export default function AuthPage({ mode = 'login' }) {
  const isRegister = mode === 'register'
  const { login, register, isLoading, error, clearError } = useAuth()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [localError, setLocalError] = useState(null)

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLocalError(null)
    clearError()
    try {
      if (isRegister) {
        await register({ email, name, password })
      } else {
        await login(email, password)
      }
    } catch (err) {
      setLocalError(err.message)
    }
  }

  const message = localError || error

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__left">
          <span className="logo">
            Half<span className="logo-accent">App</span>
          </span>
          <span className="header-tag">Rider</span>
        </div>
      </header>
      <main className="app-main">
        <div className="auth-panel">
          <h1 className="panel-title">{isRegister ? 'Create account' : 'Sign in'}</h1>
          <p className="fare-label" style={{ marginBottom: 8 }}>
            Book rides on the open board. Driver completes the trip in the driver app.
          </p>

          <form onSubmit={handleSubmit} className="field-group" style={{ gap: 12 }}>
            {isRegister && (
              <label className="field-group">
                <span className="field-label">Name</span>
                <input value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" />
              </label>
            )}
            <label className="field-group">
              <span className="field-label">Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </label>
            <label className="field-group">
              <span className="field-label">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
              />
            </label>

            {message && <p className="error-text">{message}</p>}

            <button type="submit" className="btn btn--primary" disabled={isLoading}>
              {isLoading ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}
            </button>
          </form>

          <p className="fare-label" style={{ textAlign: 'center' }}>
            {isRegister ? (
              <>
                Already have an account? <Link to="/login" className="auth-link">Sign in</Link>
              </>
            ) : (
              <>
                New here? <Link to="/register" className="auth-link">Create account</Link>
              </>
            )}
          </p>
        </div>
      </main>
    </div>
  )
}
