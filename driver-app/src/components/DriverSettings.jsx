import React, { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import AppShellLayout from './AppShellLayout.jsx'
import driverAPI from '../utils/api.js'
import { useDriverPreferences } from '../context/DriverPreferencesContext.jsx'
import { applyTheme } from '../state/useTheme.js'
import { BETA_OBLIGATION_NOT_PAYOUT } from '../utils/betaTruthCopy.js'

const DEFAULT_QUIET = { enabled: false, start: '22:00', end: '07:00' }

function normalizeQuietHours(value) {
  if (!value || typeof value !== 'object') return { ...DEFAULT_QUIET }
  return {
    enabled: Boolean(value.enabled),
    start: value.start || DEFAULT_QUIET.start,
    end: value.end || DEFAULT_QUIET.end,
  }
}

function Field({ label, value, testId }) {
  return (
    <div className="ha-card p-3" data-testid={testId}>
      <div className="ha-stat-label">{label}</div>
      <div className="text-sm font-medium mt-1" style={{ color: 'var(--ha-text)' }}>
        {value ?? '—'}
      </div>
    </div>
  )
}

function ToggleRow({ label, checked, disabled, onChange, testId }) {
  return (
    <label className="ha-card p-3 flex items-center justify-between gap-3 cursor-pointer" data-testid={testId}>
      <span className="text-sm font-medium" style={{ color: 'var(--ha-text)' }}>
        {label}
      </span>
      <input
        type="checkbox"
        checked={Boolean(checked)}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        aria-label={label}
      />
    </label>
  )
}

function formatSeenAt(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString()
}

export default function DriverSettings() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [meStatus, setMeStatus] = useState(null)
  const [connectStatus, setConnectStatus] = useState(null)
  const [appSettings, setAppSettings] = useState(null)
  const [meProfile, setMeProfile] = useState(null)
  const [accountProfile, setAccountProfile] = useState(null)
  const [profileDraft, setProfileDraft] = useState({ display_name: '', phone_e164: '' })
  const [vehicleDraft, setVehicleDraft] = useState({
    vehicle_make: '',
    vehicle_model: '',
    vehicle_year: '',
    license_plate: '',
    insurance_policy: '',
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [prefsError, setPrefsError] = useState(null)
  const [prefsSaving, setPrefsSaving] = useState(false)
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileSaved, setProfileSaved] = useState(false)
  const [vehicleSaving, setVehicleSaving] = useState(false)
  const [vehicleSaved, setVehicleSaved] = useState(false)
  const [vehicleError, setVehicleError] = useState(null)
  const [logoutBusy, setLogoutBusy] = useState(false)
  const [passwordDraft, setPasswordDraft] = useState({ current: '', next: '' })
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordSaved, setPasswordSaved] = useState(false)
  const [quietHours, setQuietHours] = useState(() => ({ ...DEFAULT_QUIET }))
  const { updatePreferences, refreshPreferences } = useDriverPreferences()

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setPrefsError(null)
    try {
      const [status, connect, settings, profile, account] = await Promise.all([
        driverAPI.getDriverMeStatus(),
        driverAPI.getStripeConnectStatus().catch(() => null),
        driverAPI.getDriverAppSettings(),
        driverAPI.getDriverMeProfile(),
        driverAPI.getDriverSettingsProfile().catch(() => null),
      ])
      setMeStatus(status || null)
      setConnectStatus(connect || null)
      setAppSettings(settings || null)
      setMeProfile(profile || null)
      setAccountProfile(account || null)
      setProfileDraft({
        display_name: profile?.display_name ?? '',
        phone_e164: profile?.phone_e164 ?? '',
      })
      const v = account?.vehicle || {}
      const stringField = (raw) => {
        const s = String(raw ?? '').trim()
        // Backend serializes empty fields as "Not registered" — treat as blank in the form.
        return s.toLowerCase() === 'not registered' ? '' : s
      }
      setVehicleDraft({
        vehicle_make: stringField(v.make),
        vehicle_model: stringField(v.model),
        vehicle_year:
          account?.vehicle_year != null ? String(account.vehicle_year) : '',
        license_plate: stringField(v.plate),
        insurance_policy: stringField(account?.insurance_policy),
      })
      setQuietHours(normalizeQuietHours(settings?.notif_quiet_hours))
      if (settings?.theme) applyTheme(settings.theme)
    } catch (err) {
      setError(err?.message || 'Could not load settings')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const patchAppSettings = async (patch) => {
    setPrefsSaving(true)
    setPrefsError(null)
    try {
      const next = await updatePreferences(patch)
      setAppSettings(next)
      if (patch.theme != null) applyTheme(next?.theme)
    } catch (err) {
      setPrefsError(err?.message || 'Could not save preferences')
    } finally {
      setPrefsSaving(false)
    }
  }

  const saveQuietHours = async () => {
    const payload = quietHours.enabled
      ? {
          enabled: true,
          start: quietHours.start,
          end: quietHours.end,
        }
      : null
    await patchAppSettings({ notif_quiet_hours: payload })
  }

  const saveVehicle = async () => {
    setVehicleSaving(true)
    setVehicleSaved(false)
    setVehicleError(null)
    try {
      const yearStr = vehicleDraft.vehicle_year.trim()
      let yearValue = null
      if (yearStr) {
        const n = Number(yearStr)
        if (!Number.isFinite(n) || n < 1900 || n > 2100) {
          throw new Error('Vehicle year must be between 1900 and 2100')
        }
        yearValue = Math.trunc(n)
      }
      const payload = {
        vehicle_make: vehicleDraft.vehicle_make.trim() || null,
        vehicle_model: vehicleDraft.vehicle_model.trim() || null,
        vehicle_year: yearValue,
        license_plate: vehicleDraft.license_plate.trim() || null,
        insurance_policy: vehicleDraft.insurance_policy.trim() || null,
      }
      await driverAPI.updateProfile(payload)
      // Re-fetch the canonical account profile so the readiness gate updates everywhere.
      const account = await driverAPI.getDriverSettingsProfile().catch(() => null)
      if (account) {
        setAccountProfile(account)
        const v = account.vehicle || {}
        const norm = (raw) => {
          const s = String(raw ?? '').trim()
          return s.toLowerCase() === 'not registered' ? '' : s
        }
        setVehicleDraft({
          vehicle_make: norm(v.make),
          vehicle_model: norm(v.model),
          vehicle_year:
            account.vehicle_year != null ? String(account.vehicle_year) : '',
          license_plate: norm(v.plate),
          insurance_policy: norm(account.insurance_policy),
        })
      }
      setVehicleSaved(true)
    } catch (err) {
      setVehicleError(err?.message || 'Could not save vehicle & documents')
    } finally {
      setVehicleSaving(false)
    }
  }

  const saveMeProfile = async () => {
    setProfileSaving(true)
    setProfileSaved(false)
    setPrefsError(null)
    try {
      const next = await driverAPI.putDriverMeProfile({
        display_name: profileDraft.display_name.trim() || null,
        phone_e164: profileDraft.phone_e164.trim() || null,
      })
      setMeProfile(next)
      setProfileDraft({
        display_name: next?.display_name ?? '',
        phone_e164: next?.phone_e164 ?? '',
      })
      setProfileSaved(true)
    } catch (err) {
      setPrefsError(err?.message || 'Could not save profile')
    } finally {
      setProfileSaving(false)
    }
  }

  const handleLogout = async () => {
    setLogoutBusy(true)
    try {
      await logout()
      await refreshPreferences()
      navigate('/')
    } finally {
      setLogoutBusy(false)
    }
  }

  const handleLogoutAllDevices = async () => {
    setLogoutBusy(true)
    try {
      await logout()
      await refreshPreferences()
      navigate('/')
    } finally {
      setLogoutBusy(false)
    }
  }

  const hasRefresh = Boolean(localStorage.getItem('driver_refresh_token'))
  const paymentsConfigured = connectStatus?.payments_enabled
  const activeRideId = meStatus?.current_ride_id

  const headerAction = (
    <div className="flex flex-col gap-2 sm:flex-row">
      <button type="button" className="ha-btn ha-btn--ghost" onClick={() => navigate('/driver')}>
        Cockpit
      </button>
      <button
        type="button"
        className="ha-btn ha-btn--ghost"
        onClick={handleLogout}
        disabled={logoutBusy}
        data-testid="settings-logout-btn"
      >
        {logoutBusy ? 'Signing out…' : 'Sign out'}
      </button>
      <button
        type="button"
        className="ha-btn ha-btn--ghost"
        onClick={handleLogoutAllDevices}
        disabled={logoutBusy}
        data-testid="settings-logout-all-btn"
        title="Revokes refresh tokens on the server"
      >
        Sign out all devices
      </button>
    </div>
  )

  return (
    <AppShellLayout
      testId="driver-settings-screen"
      title="Settings"
      subtitle="Session, preferences, provider connection, and app flags. Go online from the map cockpit."
      headerAction={headerAction}
    >
      {error ? (
        <section className="ha-section">
          <div className="ha-alert ha-alert--error">{error}</div>
        </section>
      ) : null}

      {prefsError ? (
        <section className="ha-section">
          <div className="ha-alert ha-alert--error">{prefsError}</div>
        </section>
      ) : null}

      {loading ? (
        <section className="ha-section">
          <div className="ha-card ha-empty">Loading settings…</div>
        </section>
      ) : (
        <>
          <section className="ha-section" data-testid="settings-password-section">
            <h2 className="ha-section-title">Password</h2>
            <div className="space-y-3">
              <label className="ha-card p-3 block">
                <span className="ha-stat-label">Current password</span>
                <input
                  type="password"
                  className="mt-2 w-full text-sm"
                  value={passwordDraft.current}
                  onChange={(e) =>
                    setPasswordDraft((d) => ({ ...d, current: e.target.value }))
                  }
                  autoComplete="current-password"
                />
              </label>
              <label className="ha-card p-3 block">
                <span className="ha-stat-label">New password</span>
                <input
                  type="password"
                  className="mt-2 w-full text-sm"
                  value={passwordDraft.next}
                  onChange={(e) => setPasswordDraft((d) => ({ ...d, next: e.target.value }))}
                  autoComplete="new-password"
                />
              </label>
              <button
                type="button"
                className="ha-btn ha-btn--primary"
                disabled={passwordSaving}
                data-testid="settings-change-password-btn"
                onClick={async () => {
                  setPasswordSaving(true)
                  setPasswordSaved(false)
                  setPrefsError(null)
                  try {
                    await driverAPI.changePassword(passwordDraft.current, passwordDraft.next)
                    setPasswordDraft({ current: '', next: '' })
                    setPasswordSaved(true)
                  } catch (err) {
                    setPrefsError(err?.message || 'Could not change password')
                  } finally {
                    setPasswordSaving(false)
                  }
                }}
              >
                {passwordSaving ? 'Updating…' : 'Change password'}
              </button>
              {passwordSaved ? (
                <p className="text-xs" style={{ color: 'var(--ha-green)' }}>
                  Password updated. Other devices were signed out.
                </p>
              ) : null}
            </div>
          </section>

          <section className="ha-section" data-testid="settings-session-section">
            <h2 className="ha-section-title">Session</h2>
            <div className="space-y-3">
              <Field label="Signed in as" value={user?.email || user?.name} testId="settings-user-email" />
              <Field label="Driver ID" value={user?.id != null ? String(user.id) : '—'} />
              <Field
                label="Refresh token stored"
                value={hasRefresh ? 'Yes (rotation enabled)' : 'No'}
                testId="settings-refresh-token"
              />
              <Field label="Online (cockpit)" value={meStatus?.online ? 'Yes' : 'No'} />
              <Field
                label="Active job (backend)"
                value={activeRideId != null ? `#${activeRideId}` : 'None'}
                testId="settings-active-ride-id"
              />
              <Field label="Last seen" value={formatSeenAt(meStatus?.last_seen_at)} />
              <p className="text-xs ha-truth-note">
                Sign out revokes refresh tokens on the server when connected. Use cockpit to finish an
                active job before going offline.
              </p>
            </div>
          </section>

          <section className="ha-section" data-testid="settings-preferences-section">
            <h2 className="ha-section-title">Preferences</h2>
            <div className="space-y-3">
              <label className="ha-card p-3 block" data-testid="settings-units-select">
                <span className="ha-stat-label">Distance units</span>
                <select
                  className="mt-2 w-full text-sm"
                  value={appSettings?.units ?? 'mi'}
                  disabled={prefsSaving || !appSettings}
                  onChange={(e) => patchAppSettings({ units: e.target.value })}
                >
                  <option value="mi">Miles</option>
                  <option value="km">Kilometers</option>
                </select>
              </label>

              <label className="ha-card p-3 block" data-testid="settings-theme-select">
                <span className="ha-stat-label">Theme</span>
                <select
                  className="mt-2 w-full text-sm"
                  value={appSettings?.theme ?? 'system'}
                  disabled={prefsSaving || !appSettings}
                  onChange={(e) => patchAppSettings({ theme: e.target.value })}
                >
                  <option value="system">System</option>
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </label>

              <label className="ha-card p-3 block" data-testid="settings-locale-select">
                <span className="ha-stat-label">Language / locale</span>
                <select
                  className="mt-2 w-full text-sm"
                  value={appSettings?.locale ?? 'en-US'}
                  disabled={prefsSaving || !appSettings}
                  onChange={(e) => patchAppSettings({ locale: e.target.value })}
                >
                  <option value="en-US">English (US)</option>
                  <option value="es-ES">Español</option>
                </select>
              </label>

              <div className="ha-card p-3 space-y-3" data-testid="settings-quiet-hours">
                <label className="flex items-center justify-between gap-3 cursor-pointer">
                  <span className="text-sm font-medium" style={{ color: 'var(--ha-text)' }}>
                    Quiet hours
                  </span>
                  <input
                    type="checkbox"
                    checked={quietHours.enabled}
                    disabled={prefsSaving}
                    onChange={(e) =>
                      setQuietHours((q) => ({ ...q, enabled: e.target.checked }))
                    }
                  />
                </label>
                {quietHours.enabled ? (
                  <div className="flex flex-wrap gap-3">
                    <label className="text-xs ha-truth-note flex flex-col gap-1">
                      Start
                      <input
                        type="time"
                        className="text-sm"
                        value={quietHours.start}
                        disabled={prefsSaving}
                        onChange={(e) =>
                          setQuietHours((q) => ({ ...q, start: e.target.value }))
                        }
                      />
                    </label>
                    <label className="text-xs ha-truth-note flex flex-col gap-1">
                      End
                      <input
                        type="time"
                        className="text-sm"
                        value={quietHours.end}
                        disabled={prefsSaving}
                        onChange={(e) =>
                          setQuietHours((q) => ({ ...q, end: e.target.value }))
                        }
                      />
                    </label>
                  </div>
                ) : null}
                <button
                  type="button"
                  className="ha-btn ha-btn--ghost text-sm"
                  disabled={prefsSaving}
                  onClick={saveQuietHours}
                >
                  Save quiet hours
                </button>
              </div>

              <ToggleRow
                label="Push notifications (preference only)"
                checked={appSettings?.notif_push_enabled}
                disabled={prefsSaving || !appSettings}
                onChange={(v) => patchAppSettings({ notif_push_enabled: v })}
                testId="settings-notif-push-toggle"
              />
              <ToggleRow
                label="Notification sounds"
                checked={appSettings?.notif_sound_enabled}
                disabled={prefsSaving || !appSettings}
                onChange={(v) => patchAppSettings({ notif_sound_enabled: v })}
                testId="settings-notif-sound-toggle"
              />
              <p className="text-xs ha-truth-note">
                Push delivery is not enabled in this build — preferences are stored for a future slice.
              </p>
            </div>
          </section>

          <section className="ha-section" data-testid="settings-app-profile-section">
            <h2 className="ha-section-title">App profile</h2>
            <div className="space-y-3">
              <label className="ha-card p-3 block">
                <span className="ha-stat-label">Display name</span>
                <input
                  type="text"
                  className="mt-2 w-full text-sm"
                  value={profileDraft.display_name}
                  disabled={profileSaving}
                  onChange={(e) => setProfileDraft((d) => ({ ...d, display_name: e.target.value }))}
                  placeholder={user?.name || 'Display name'}
                  data-testid="settings-display-name-input"
                />
              </label>
              <label className="ha-card p-3 block">
                <span className="ha-stat-label">Phone (E.164)</span>
                <input
                  type="tel"
                  className="mt-2 w-full text-sm"
                  value={profileDraft.phone_e164}
                  disabled={profileSaving}
                  onChange={(e) => setProfileDraft((d) => ({ ...d, phone_e164: e.target.value }))}
                  placeholder="+15551234567"
                  data-testid="settings-phone-input"
                />
              </label>
              {meProfile?.photo_url ? (
                <Field label="Photo URL" value={meProfile.photo_url} />
              ) : null}
              <button
                type="button"
                className="ha-btn ha-btn--primary"
                disabled={profileSaving}
                onClick={saveMeProfile}
                data-testid="settings-profile-save-btn"
              >
                {profileSaving ? 'Saving…' : 'Save app profile'}
              </button>
              {profileSaved ? (
                <p className="text-xs" style={{ color: 'var(--ha-green)' }}>
                  App profile saved.
                </p>
              ) : null}
              <p className="text-xs ha-truth-note">
                Display name + phone are stored on the in-app overlay. Vehicle and document fields
                below are the canonical account record used by the readiness gate.
              </p>
            </div>
          </section>

          <section className="ha-section" data-testid="settings-vehicle-section">
            <h2 className="ha-section-title">Vehicle &amp; documents</h2>
            <p className="text-xs ha-truth-note mb-2">
              Fields used by the pre-online readiness check. The cockpit will block Go-online while
              any are missing.
            </p>
            <div className="space-y-3">
              <label className="ha-card p-3 block">
                <span className="ha-stat-label">Make</span>
                <input
                  type="text"
                  className="mt-2 w-full text-sm"
                  value={vehicleDraft.vehicle_make}
                  disabled={vehicleSaving}
                  onChange={(e) =>
                    setVehicleDraft((d) => ({ ...d, vehicle_make: e.target.value }))
                  }
                  placeholder="Toyota"
                  data-testid="settings-vehicle-make-input"
                />
              </label>
              <label className="ha-card p-3 block">
                <span className="ha-stat-label">Model</span>
                <input
                  type="text"
                  className="mt-2 w-full text-sm"
                  value={vehicleDraft.vehicle_model}
                  disabled={vehicleSaving}
                  onChange={(e) =>
                    setVehicleDraft((d) => ({ ...d, vehicle_model: e.target.value }))
                  }
                  placeholder="Prius"
                  data-testid="settings-vehicle-model-input"
                />
              </label>
              <label className="ha-card p-3 block">
                <span className="ha-stat-label">Year</span>
                <input
                  type="number"
                  inputMode="numeric"
                  min="1900"
                  max="2100"
                  className="mt-2 w-full text-sm"
                  value={vehicleDraft.vehicle_year}
                  disabled={vehicleSaving}
                  onChange={(e) =>
                    setVehicleDraft((d) => ({ ...d, vehicle_year: e.target.value }))
                  }
                  placeholder="2020"
                  data-testid="settings-vehicle-year-input"
                />
              </label>
              <label className="ha-card p-3 block">
                <span className="ha-stat-label">License plate</span>
                <input
                  type="text"
                  className="mt-2 w-full text-sm"
                  value={vehicleDraft.license_plate}
                  disabled={vehicleSaving}
                  onChange={(e) =>
                    setVehicleDraft((d) => ({ ...d, license_plate: e.target.value }))
                  }
                  placeholder="ABC-1234"
                  data-testid="settings-license-plate-input"
                />
              </label>
              <label className="ha-card p-3 block">
                <span className="ha-stat-label">Insurance policy number</span>
                <input
                  type="text"
                  className="mt-2 w-full text-sm"
                  value={vehicleDraft.insurance_policy}
                  disabled={vehicleSaving}
                  onChange={(e) =>
                    setVehicleDraft((d) => ({ ...d, insurance_policy: e.target.value }))
                  }
                  placeholder="INS-XXXX-YYYY"
                  data-testid="settings-insurance-policy-input"
                />
              </label>
              <Field
                label="Driver license number (from registration)"
                value={accountProfile?.license_no || '—'}
                testId="settings-license-no-readonly"
              />
              {vehicleError ? (
                <p className="text-xs" style={{ color: 'var(--ha-red, #fca5a5)' }} data-testid="settings-vehicle-error">
                  {vehicleError}
                </p>
              ) : null}
              <button
                type="button"
                className="ha-btn ha-btn--primary"
                disabled={vehicleSaving}
                onClick={saveVehicle}
                data-testid="settings-vehicle-save-btn"
              >
                {vehicleSaving ? 'Saving…' : 'Save vehicle & documents'}
              </button>
              {vehicleSaved ? (
                <p className="text-xs" style={{ color: 'var(--ha-green)' }} data-testid="settings-vehicle-saved">
                  Vehicle &amp; documents saved. Open the cockpit to re-run the readiness check.
                </p>
              ) : null}
              <p className="text-xs ha-truth-note">
                License number is locked at registration. Real document upload (photo, verification)
                is not part of this internal product — see launch blockers D1–D5.
              </p>
            </div>
          </section>

          <section className="ha-section" data-testid="settings-connect-section">
            <h2 className="ha-section-title">Payment provider (read-only)</h2>
            <div className="space-y-3">
              <Field
                label="Payments feature flag"
                value={paymentsConfigured ? 'Enabled on server' : 'Disabled on server'}
              />
              <Field
                label="Payout visibility flag"
                value={connectStatus?.payouts_enabled_flag ? 'Enabled' : 'Disabled'}
              />
              <Field
                label="Connect account"
                value={
                  connectStatus?.has_connect_account
                    ? connectStatus.stripe_account_id
                    : 'Not linked'
                }
                testId="settings-provider-account-id"
              />
              <Field
                label="Charges enabled (provider)"
                value={connectStatus?.charges_enabled ? 'Yes' : 'No'}
              />
              <Field
                label="Provider payouts enabled (account)"
                value={connectStatus?.provider_payouts_enabled ? 'Yes' : 'No'}
              />
              <p className="text-xs ha-truth-note">{BETA_OBLIGATION_NOT_PAYOUT}</p>
              {paymentsConfigured && !connectStatus?.has_connect_account ? (
                <p className="text-xs" style={{ color: '#fcd34d' }}>
                  Payments are enabled but this driver has no Connect account row yet. Onboarding is
                  ops/admin — not started from this screen.
                </p>
              ) : null}
            </div>
          </section>

          <section className="ha-section" data-testid="settings-links-section">
            <h2 className="ha-section-title">Account &amp; records</h2>
            <ul className="ha-list">
              <li className="ha-list-item">
                <Link to="/driver/notifications" className="text-sm font-medium" style={{ color: 'var(--ha-green)' }}>
                  Notifications inbox →
                </Link>
              </li>
              <li className="ha-list-item">
                <Link to="/driver/profile" className="text-sm font-medium" style={{ color: 'var(--ha-green)' }}>
                  Profile, vehicle &amp; stats →
                </Link>
              </li>
              <li className="ha-list-item">
                <Link to="/driver/earnings" className="text-sm font-medium" style={{ color: 'var(--ha-green)' }}>
                  Earnings &amp; payment visibility →
                </Link>
              </li>
              <li className="ha-list-item">
                <Link to="/driver/trips" className="text-sm font-medium" style={{ color: 'var(--ha-green)' }}>
                  Trips &amp; audit receipts →
                </Link>
              </li>
              <li className="ha-list-item">
                <Link to="/driver/help" className="text-sm font-medium" style={{ color: 'var(--ha-green)' }} data-testid="settings-help-link">
                  Help &amp; support →
                </Link>
              </li>
            </ul>
          </section>

          {import.meta.env.DEV ? (
            <section className="ha-section" data-testid="settings-dev-flags">
              <h2 className="ha-section-title">Development flags</h2>
              <div className="space-y-2 text-xs ha-truth-note font-mono">
                <div>VITE_ALLOW_OFFLINE_MOCK={String(import.meta.env.VITE_ALLOW_OFFLINE_MOCK)}</div>
                <div>VITE_ENABLE_RIDE_SIMULATION={String(import.meta.env.VITE_ENABLE_RIDE_SIMULATION)}</div>
                <div>VITE_BETA_NO_MONEY_TRUTH={String(import.meta.env.VITE_BETA_NO_MONEY_TRUTH)}</div>
              </div>
            </section>
          ) : null}
        </>
      )}
    </AppShellLayout>
  )
}
