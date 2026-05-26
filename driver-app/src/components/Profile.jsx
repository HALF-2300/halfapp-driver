import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import AppShellLayout from './AppShellLayout.jsx'
import driverAPI from '../utils/api'
import { useDriverPreferences } from '../context/DriverPreferencesContext.jsx'
import { formatDistanceKm } from '../utils/formatDistance.js'
import { isNotificationRead } from '../utils/notificationDisplay.js'

const TABS = [
  { id: 'profile', label: 'Profile' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'statistics', label: 'Stats' },
]

function ProfileRow({ label, value, testId, valueColor }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 border-b last:border-b-0" style={{ borderColor: 'var(--ha-border)' }}>
      <span className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--ha-muted)' }}>{label}</span>
      <span
        className="text-sm font-medium text-right"
        style={{ color: valueColor || 'var(--ha-text)', maxWidth: '65%' }}
        data-testid={testId}
      >
        {value || 'Not registered'}
      </span>
    </div>
  )
}

function formatStatNumber(value, digits = 0) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  return digits > 0 ? num.toFixed(digits) : String(num)
}

export default function Profile() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { units } = useDriverPreferences()
  const [profile, setProfile] = useState(null)
  const [stats, setStats] = useState(null)
  const [insights, setInsights] = useState([])
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('profile')

  const [editingContact, setEditingContact] = useState(false)
  const [phoneInput, setPhoneInput] = useState('')
  const [emergencyInput, setEmergencyInput] = useState('')
  const [savingContact, setSavingContact] = useState(false)
  const [saveError, setSaveError] = useState(null)

  const fetchProfileData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const [profileData, statsData, notificationsData, earningsData, insightsData] =
        await Promise.all([
          driverAPI.getDriverSettingsProfile(),
          driverAPI.getStatistics(),
          driverAPI.getNotifications().catch(() => null),
          driverAPI.getEarnings().catch(() => null),
          driverAPI.getInsights().catch(() => null),
        ])

      setProfile(profileData)
      setPhoneInput(profileData?.phone || '')
      setEmergencyInput(profileData?.emergency_contact || '')

      const rawList =
        notificationsData == null
          ? []
          : Array.isArray(notificationsData)
            ? notificationsData
            : notificationsData?.notifications || []
      setNotifications(rawList)
      setInsights(Array.isArray(insightsData?.insights) ? insightsData.insights : [])

      const ps = statsData?.performance_stats || statsData || {}
      const es = earningsData?.earnings_summary
      setStats({
        total_rides: ps.total_rides_completed ?? null,
        total_earnings: es?.total_earnings ?? null,
        average_rating: ps.average_rating ?? null,
        total_distance: ps.total_distance_km ?? ps.total_distance ?? null,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchProfileData()
  }, [fetchProfileData])

  const saveContact = async () => {
    setSavingContact(true)
    setSaveError(null)
    try {
      await driverAPI.updateProfile({
        phone: phoneInput.trim() || null,
        emergency_contact: emergencyInput.trim() || null,
      })
      await fetchProfileData()
      setEditingContact(false)
    } catch (err) {
      setSaveError(err?.message || 'Could not save contact info')
    } finally {
      setSavingContact(false)
    }
  }

  const cancelContact = () => {
    setEditingContact(false)
    setSaveError(null)
    setPhoneInput(profile?.phone || '')
    setEmergencyInput(profile?.emergency_contact || '')
  }

  const markNotificationRead = async (notificationId) => {
    try {
      await driverAPI.markNotificationRead(notificationId)
      await fetchProfileData()
    } catch {
      /* best effort */
    }
  }

  const unreadCount = notifications.filter((n) => !isNotificationRead(n)).length

  const approvalStatus = String(profile?.approval_status || '').toLowerCase()
  const approvalApproved = approvalStatus === 'approved'
  const vehicleReady = Boolean(profile?.vehicle_ready)

  const headerAction = (
    <div className="flex gap-2">
      <button type="button" className="ha-btn ha-btn--ghost" onClick={() => navigate('/driver/settings')}>
        Settings
      </button>
      <button type="button" className="ha-btn ha-btn--ghost" onClick={logout}>
        Log out
      </button>
    </div>
  )

  return (
    <AppShellLayout
      testId="account-screen"
      title="Account"
      subtitle="Driver account, contact, and status."
      headerAction={headerAction}
    >
      <section className="ha-section" style={{ paddingTop: '1rem' }}>
        <div className="ha-chip-row" role="tablist" aria-label="Account sections">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`ha-chip ${activeTab === tab.id ? 'ha-chip--active' : ''}`}
              data-testid={`account-tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
              {tab.id === 'notifications' && unreadCount > 0 ? ` · ${unreadCount}` : ''}
            </button>
          ))}
        </div>
      </section>

      {error ? (
        <section className="ha-section">
          <div className="ha-alert ha-alert--error">{error}</div>
        </section>
      ) : null}

      {activeTab === 'profile' && (
        <section className="ha-section" data-testid="driver-profile-page">
          {loading ? (
            <div className="ha-card ha-empty">Loading driver profile…</div>
          ) : (
            <div className="space-y-3">

              {/* Account identifiers */}
              <div className="ha-card" style={{ padding: '0.75rem 1rem' }}>
                <p className="ha-section-title" style={{ marginBottom: '0.5rem' }}>Account</p>
                <ProfileRow label="Name" value={profile?.name} testId="profile-name" />
                <ProfileRow label="Email" value={profile?.email} testId="profile-email" />
                <ProfileRow label="Role" value={profile?.role} />
              </div>

              {/* Status */}
              <div className="ha-card" style={{ padding: '0.75rem 1rem' }}>
                <p className="ha-section-title" style={{ marginBottom: '0.5rem' }}>Status</p>
                <div className="flex items-center justify-between gap-3 py-2">
                  <span className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--ha-muted)' }}>Approval</span>
                  <span
                    data-testid="driver-profile-approval-status"
                    className="rounded-full px-3 py-0.5 text-xs font-semibold border"
                    style={
                      approvalApproved
                        ? { background: 'rgba(52,211,153,0.12)', borderColor: 'rgba(52,211,153,0.35)', color: '#34d399' }
                        : { background: 'rgba(245,158,11,0.1)', borderColor: 'rgba(245,158,11,0.35)', color: '#fcd34d' }
                    }
                  >
                    {profile?.approval_status || 'pending'}
                  </span>
                </div>
              </div>

              {/* Contact — editable */}
              <div className="ha-card" style={{ padding: '0.75rem 1rem' }}>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <p className="ha-section-title" style={{ marginBottom: 0 }}>Contact</p>
                  {!editingContact ? (
                    <button
                      type="button"
                      className="ha-btn ha-btn--ghost"
                      style={{ fontSize: '0.75rem', padding: '0.2rem 0.55rem' }}
                      onClick={() => setEditingContact(true)}
                    >
                      Edit
                    </button>
                  ) : null}
                </div>
                {!editingContact ? (
                  <div>
                    <ProfileRow label="Phone" value={profile?.phone || 'Not added'} />
                    <ProfileRow label="Emergency contact" value={profile?.emergency_contact || 'Not added'} />
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div>
                      <label className="ha-field-label" htmlFor="profile-phone">Phone number</label>
                      <input
                        id="profile-phone"
                        type="tel"
                        className="ha-input"
                        value={phoneInput}
                        onChange={(e) => setPhoneInput(e.target.value)}
                        placeholder="+1 503 555 0100"
                        autoComplete="tel"
                      />
                    </div>
                    <div>
                      <label className="ha-field-label" htmlFor="profile-emergency">Emergency contact</label>
                      <input
                        id="profile-emergency"
                        type="text"
                        className="ha-input"
                        value={emergencyInput}
                        onChange={(e) => setEmergencyInput(e.target.value)}
                        placeholder="Name · phone number"
                        autoComplete="off"
                      />
                    </div>
                    {saveError ? (
                      <p className="text-xs" style={{ color: 'var(--ha-danger)' }}>{saveError}</p>
                    ) : null}
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="ha-btn ha-btn--ghost flex-1"
                        onClick={cancelContact}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        className="ha-btn ha-btn--primary flex-1"
                        disabled={savingContact}
                        onClick={saveContact}
                        data-testid="profile-save-contact"
                      >
                        {savingContact ? 'Saving…' : 'Save'}
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Vehicle */}
              <div className="ha-card" style={{ padding: '0.75rem 1rem' }}>
                <p className="ha-section-title" style={{ marginBottom: '0.5rem' }}>Vehicle</p>
                <ProfileRow
                  label="Make"
                  value={profile?.vehicle?.make || profile?.vehicle_make}
                />
                <ProfileRow
                  label="Model"
                  value={profile?.vehicle?.model || profile?.vehicle_model}
                />
                <ProfileRow
                  label="Year"
                  value={profile?.vehicle?.year || profile?.vehicle_year}
                />
                <ProfileRow
                  label="Plate"
                  value={profile?.vehicle?.plate || profile?.license_plate}
                />
                <ProfileRow
                  label="Ready"
                  value={vehicleReady ? 'Confirmed' : 'Needs ops review'}
                  valueColor={vehicleReady ? 'var(--ha-green)' : 'var(--ha-warning)'}
                />
              </div>

              <div
                data-testid="driver-profile-readonly-note"
                className="rounded-xl border px-3 py-2.5 text-xs"
                style={{
                  borderColor: 'rgba(59,130,246,0.22)',
                  background: 'rgba(59,130,246,0.05)',
                  color: 'var(--ha-muted)',
                }}
              >
                Approval, vehicle compliance, and insurance are managed by operations. No payment or bank information is collected here.
              </div>
            </div>
          )}
        </section>
      )}

      {activeTab === 'notifications' && (
        <section className="ha-section" data-testid="account-notifications-panel">
          <h2 className="ha-section-title">
            Notifications
            {unreadCount > 0 ? ` · ${unreadCount} unread` : ''}
          </h2>
          {loading ? (
            <div className="ha-card ha-empty">Loading…</div>
          ) : notifications.length === 0 ? (
            <div className="ha-card ha-empty">No notifications from the backend.</div>
          ) : (
            <ul className="ha-list">
              {notifications.map((notification) => (
                <li
                  key={notification.id}
                  className="ha-list-item"
                  style={
                    isNotificationRead(notification)
                      ? undefined
                      : { borderColor: 'rgba(59, 130, 246, 0.45)' }
                  }
                >
                  <div className="flex justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-sm">{notification.title}</div>
                      <p className="text-sm mt-1" style={{ color: 'var(--ha-muted)' }}>
                        {notification.message}
                      </p>
                      <p className="ha-truth-note">
                        {notification.created_at
                          ? new Date(notification.created_at).toLocaleString()
                          : '—'}
                      </p>
                    </div>
                    {!isNotificationRead(notification) && (
                      <button
                        type="button"
                        className="ha-btn ha-btn--ghost shrink-0 self-start"
                        style={{ fontSize: '0.72rem', padding: '0.2rem 0.55rem' }}
                        onClick={() => markNotificationRead(notification.id)}
                      >
                        Mark read
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {activeTab === 'statistics' && (
        <section className="ha-section" data-testid="account-stats-panel">
          <h2 className="ha-section-title">Measured stats</h2>
          {loading ? (
            <div className="ha-card ha-empty">Loading…</div>
          ) : !stats ? (
            <div className="ha-card ha-empty">Statistics unavailable.</div>
          ) : (
            <>
              <div className="ha-stat-grid">
                <div className="ha-stat">
                  <div className="ha-stat-label">Total jobs</div>
                  <div className="ha-stat-value">{formatStatNumber(stats.total_rides)}</div>
                </div>
                <div className="ha-stat">
                  <div className="ha-stat-label">Total earnings</div>
                  <div className="ha-stat-value">
                    {stats.total_earnings != null
                      ? `$${formatStatNumber(stats.total_earnings, 2)}`
                      : '—'}
                  </div>
                </div>
                <div className="ha-stat">
                  <div className="ha-stat-label">Avg rating</div>
                  <div className="ha-stat-value">
                    {stats.average_rating != null && Number(stats.average_rating) > 0
                      ? formatStatNumber(stats.average_rating, 1)
                      : '—'}
                  </div>
                  <div className="ha-stat-meta">Backend only</div>
                </div>
                <div className="ha-stat">
                  <div className="ha-stat-label">Distance</div>
                  <div className="ha-stat-value">
                    {stats.total_distance != null
                      ? formatDistanceKm(Number(stats.total_distance), units)
                      : '—'}
                  </div>
                </div>
              </div>

              {insights.length > 0 ? (
                <div className="ha-card mt-3">
                  <h3 className="ha-section-title">Dispatch insights</h3>
                  <ul className="space-y-3">
                    {insights.map((insight, index) => (
                      <li
                        key={`${insight.type || 'insight'}-${index}`}
                        className="rounded-xl border p-3"
                        style={{ borderColor: 'var(--ha-border)' }}
                      >
                        <div className="flex justify-between gap-2 text-sm font-medium">
                          <span>{insight.type || 'dispatch_insight'}</span>
                          <span style={{ color: 'var(--ha-muted)' }}>{insight.status || 'measured'}</span>
                        </div>
                        <p className="text-sm mt-1" style={{ color: 'var(--ha-muted)' }}>
                          {insight.message}
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </>
          )}
        </section>
      )}
    </AppShellLayout>
  )
}
