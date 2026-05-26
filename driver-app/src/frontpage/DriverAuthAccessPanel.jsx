import React from 'react'
import { ALLOW_OFFLINE_MOCK } from '../utils/api.js'

export default function DriverAuthAccessPanel({
  mode,
  setMode,
  formData,
  errors,
  error,
  sessionNotice,
  showSuccess,
  isLoading,
  onInputChange,
  onSubmit,
  onForgotSubmit,
  onResetSubmit,
  resetTokenHint,
}) {
  const submitLabel = isLoading
    ? mode === 'signin'
      ? 'Checking session...'
      : 'Creating access...'
    : mode === 'signin'
      ? 'Sign in to cockpit'
      : 'Create Driver Account'

  return (
    <section className="dp-auth" id="access" data-testid="driver-auth-panel">
      <div className="dp-auth__intro">
        <p className="dp-eyebrow">Driver access</p>
        <h2>Open the closed-beta cockpit</h2>
        <p>Sign in, confirm readiness, and continue into the driver operating surface.</p>
        <div className="dp-auth-proof-row" aria-label="Closed beta operating boundaries">
          <span>Closed beta</span>
          <span>Manual readiness</span>
          <span>Recorded obligations</span>
        </div>
        {import.meta.env.DEV && ALLOW_OFFLINE_MOCK && (
          <p className="dp-auth__dev-note" data-testid="driver-auth-dev-note">
            Dev: offline mock login may be available when the backend is unreachable.
          </p>
        )}
      </div>

      <div className="dp-auth-card">
        <div className="dp-auth-tabs" role="tablist" aria-label="Auth mode">
          <button
            type="button"
            className={mode === 'signin' ? 'active' : ''}
            data-testid="auth-tab-signin"
            onClick={() => setMode('signin')}
          >
            Sign In
          </button>
          <button
            type="button"
            className={mode === 'signup' ? 'active' : ''}
            data-testid="auth-tab-signup"
            onClick={() => setMode('signup')}
          >
            Create Account
          </button>
        </div>

        {showSuccess && (
          <div className="dp-auth-alert dp-auth-alert--success">
            {mode === 'signin' ? 'Welcome back — opening the cockpit…' : 'Account created — opening the cockpit…'}
          </div>
        )}

        {sessionNotice && (
          <div className="dp-auth-alert dp-auth-alert--info" data-testid="auth-session-notice">
            {sessionNotice}
          </div>
        )}

        {(errors.general || error) && (
          <div className="dp-auth-alert dp-auth-alert--error" data-testid="auth-error-message">
            {errors.general || error}
          </div>
        )}

        {mode === 'forgot' ? (
          <form
            className="dp-form"
            onSubmit={(e) => {
              e.preventDefault()
              onForgotSubmit?.(e)
            }}
            noValidate
          >
            <p className="text-sm dp-auth__dev-note">We will email a reset link in production. Dev may return a token.</p>
            <label className="dp-field">
              <span>Email</span>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={onInputChange}
                autoComplete="email"
                data-testid="forgot-email-input"
              />
            </label>
            <button type="submit" className="dp-btn dp-btn--primary dp-btn--block" disabled={isLoading}>
              Send reset link
            </button>
            <button type="button" className="dp-btn dp-btn--ghost dp-btn--block mt-2" onClick={() => setMode('signin')}>
              Back to sign in
            </button>
          </form>
        ) : null}

        {mode === 'reset' ? (
          <form
            className="dp-form"
            onSubmit={(e) => {
              e.preventDefault()
              onResetSubmit?.(e)
            }}
            noValidate
          >
            {resetTokenHint ? (
              <p className="text-xs dp-auth__dev-note" data-testid="reset-token-hint">
                Dev token: <code>{resetTokenHint}</code>
              </p>
            ) : null}
            <label className="dp-field">
              <span>Reset token</span>
              <input
                type="text"
                name="reset_token"
                value={formData.reset_token || ''}
                onChange={onInputChange}
                data-testid="reset-token-input"
              />
            </label>
            <label className="dp-field">
              <span>New password</span>
              <input
                type="password"
                name="new_password"
                value={formData.new_password || ''}
                onChange={onInputChange}
                autoComplete="new-password"
                data-testid="reset-password-input"
              />
            </label>
            <button type="submit" className="dp-btn dp-btn--primary dp-btn--block" disabled={isLoading}>
              Set new password
            </button>
            <button type="button" className="dp-btn dp-btn--ghost dp-btn--block mt-2" onClick={() => setMode('signin')}>
              Back to sign in
            </button>
          </form>
        ) : null}

        {(mode === 'signin' || mode === 'signup') && (
        <form className="dp-form" onSubmit={onSubmit} noValidate>
          {mode === 'signup' && (
            <label className="dp-field">
              <span>Full Name</span>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={onInputChange}
                placeholder="Full Name"
                className={errors.name ? 'dp-input--error' : ''}
                autoComplete="name"
              />
              {errors.name && <span className="dp-field-error">{errors.name}</span>}
            </label>
          )}

          <label className="dp-field">
            <span>Email Address</span>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={onInputChange}
              placeholder="Email Address"
              className={errors.email ? 'dp-input--error' : ''}
              autoComplete="email"
            />
            {errors.email && <span className="dp-field-error">{errors.email}</span>}
          </label>

          <label className="dp-field">
            <span>Password</span>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={onInputChange}
              placeholder="Password"
              className={errors.password ? 'dp-input--error' : ''}
              autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
            />
            {errors.password && <span className="dp-field-error">{errors.password}</span>}
          </label>

          {mode === 'signup' && (
            <label className="dp-field">
              <span>Driver License</span>
              <input
                type="text"
                name="license_no"
                value={formData.license_no}
                onChange={onInputChange}
                placeholder="Driver license number"
                className={errors.license_no ? 'dp-input--error' : ''}
              />
              {errors.license_no && <span className="dp-field-error">{errors.license_no}</span>}
            </label>
          )}

          {mode === 'signin' ? (
            <button
              type="button"
              className="text-sm mt-2 underline"
              data-testid="forgot-password-link"
              onClick={() => setMode('forgot')}
            >
              Forgot password?
            </button>
          ) : null}

          <button
            type="submit"
            className="dp-btn dp-btn--primary dp-btn--block"
            data-testid="login-submit-btn"
            disabled={isLoading}
          >
            {submitLabel}
          </button>
        </form>
        )}
      </div>
    </section>
  )
}
