import React, { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import driverAPI from '../utils/api.js'
import { validateLoginData, validateRegistrationData } from '../utils/validation.js'
import DriverPortalNav from './DriverPortalNav.jsx'
import DriverPortalHero from './DriverPortalHero.jsx'
import DriverPortalCapabilities from './DriverPortalCapabilities.jsx'
import DriverAuthAccessPanel from './DriverAuthAccessPanel.jsx'
import DriverPortalFooter from './DriverPortalFooter.jsx'
import './driver-portal.css'

const COCKPIT_PATH = '/driver'

function scrollToAuth() {
  document.getElementById('access')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export default function HalfAppDriverPortalFrontPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState('signin')
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    license_no: '',
    reset_token: '',
    new_password: '',
  })
  const [resetTokenHint, setResetTokenHint] = useState('')
  const [authBusy, setAuthBusy] = useState(false)
  const [errors, setErrors] = useState({})
  const [showSuccess, setShowSuccess] = useState(false)
  const { login, register, isLoading, error, clearError, isAuthenticated } = useAuth()

  useEffect(() => {
    if (isAuthenticated) {
      navigate(COCKPIT_PATH, { replace: true })
    }
  }, [isAuthenticated, navigate])

  useEffect(() => {
    if (location.pathname === '/login' || location.hash.includes('/login')) {
      requestAnimationFrame(() => scrollToAuth())
    }
  }, [location.pathname, location.hash])

  useEffect(() => {
    setErrors({})
    setShowSuccess(false)
    clearError()
    if (mode === 'signin') {
      setFormData((prev) => ({ ...prev, name: '', license_no: '' }))
    }
  }, [mode, clearError])

  const focusAuth = useCallback((nextMode) => {
    if (nextMode) setMode(nextMode)
    scrollToAuth()
  }, [])

  const handleInputChange = useCallback(
    (e) => {
      const { name, value } = e.target
      setFormData((prev) => ({ ...prev, [name]: value }))
      if (errors[name]) {
        setErrors((prev) => {
          const next = { ...prev }
          delete next[name]
          return next
        })
      }
    },
    [errors],
  )

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault()
      setErrors({})
      setShowSuccess(false)
      clearError()
      if (isLoading) return

      if (!formData.email || !formData.password) {
        setErrors({
          general: 'Please fill in all required fields',
          email: !formData.email ? 'Email is required' : '',
          password: !formData.password ? 'Password is required' : '',
        })
        return
      }

      try {
        if (mode === 'signin') {
          validateLoginData({ email: formData.email, password: formData.password })
          await login(formData.email, formData.password)
          setShowSuccess(true)
          navigate(COCKPIT_PATH, { replace: true })
        } else {
          const validated = validateRegistrationData({ ...formData, role: 'driver' })
          await register(validated)
          setShowSuccess(true)
          navigate(COCKPIT_PATH, { replace: true })
        }
      } catch (err) {
        setShowSuccess(false)
        if (err.validationErrors) {
          setErrors(err.validationErrors)
        } else {
          setErrors({ general: err.message || 'Authentication failed. Please try again.' })
        }
      }
    },
    [isLoading, formData, mode, login, register, navigate, clearError],
  )

  const handleForgotSubmit = useCallback(async () => {
    setAuthBusy(true)
    setErrors({})
    clearError()
    try {
      const res = await driverAPI.forgotPassword(formData.email)
      if (res?.reset_token) {
        setResetTokenHint(res.reset_token)
        setFormData((prev) => ({ ...prev, reset_token: res.reset_token }))
      }
      setMode('reset')
      setErrors({ general: 'If the account exists, a reset token was issued. Enter it below.' })
    } catch (err) {
      setErrors({ general: err.message || 'Could not request password reset' })
    } finally {
      setAuthBusy(false)
    }
  }, [formData.email, clearError])

  const handleResetSubmit = useCallback(async () => {
    setAuthBusy(true)
    setErrors({})
    clearError()
    try {
      await driverAPI.resetPassword(formData.reset_token, formData.new_password)
      setMode('signin')
      setErrors({ general: 'Password updated — sign in with your new password.' })
    } catch (err) {
      setErrors({ general: err.message || 'Could not reset password' })
    } finally {
      setAuthBusy(false)
    }
  }, [formData.reset_token, formData.new_password, clearError])

  const devBannerOffset = import.meta.env.DEV ? ' dp-portal--with-dev-banner' : ''

  return (
    <div className={`dp-portal${devBannerOffset}`} data-testid="driver-portal-frontpage">
      <span className="sr-only" data-testid="halfapp-frontpage">
        HalfApp Driver Portal
      </span>
      <div className="dp-portal__bg" aria-hidden />

      <DriverPortalNav
        onSignIn={() => focusAuth('signin')}
        onGetStarted={() => focusAuth('signup')}
      />

      <main className="dp-main">
        <DriverPortalHero
          onEnterPortal={() => focusAuth('signin')}
          onCreateAccount={() => focusAuth('signup')}
        />

        <section className="dp-trust" id="safety" data-testid="driver-portal-trust">
          <h2>Safety &amp; trust</h2>
          <p>
            HalfApp Driver Portal is built for clarity: backend-owned availability, auditable ride visibility,
            and diagnostics when you need them — without cluttering your map-first work surface.
          </p>
        </section>

        <DriverPortalCapabilities />

        <DriverAuthAccessPanel
          mode={mode}
          setMode={setMode}
          formData={formData}
          errors={errors}
          error={error}
          showSuccess={showSuccess}
          isLoading={isLoading || authBusy}
          onInputChange={handleInputChange}
          onSubmit={handleSubmit}
          onForgotSubmit={handleForgotSubmit}
          onResetSubmit={handleResetSubmit}
          resetTokenHint={resetTokenHint}
        />
      </main>

      <DriverPortalFooter />
    </div>
  )
}
