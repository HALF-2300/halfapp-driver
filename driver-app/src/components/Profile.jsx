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

function SettingsField({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-medium text-slate-900">{value || 'Not registered'}</div>
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
  const { user, logout } = useAuth()
  const { units } = useDriverPreferences()
  const [profile, setProfile] = useState(null)
  const [stats, setStats] = useState(null)
  const [insights, setInsights] = useState([])
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('profile')

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
      const rawList =
        notificationsData == null
          ? []
          : Array.isArray(notificationsData)
            ? notificationsData
            : notificationsData?.notifications || []
      setNotifications(rawList)
      setInsights(Array.isArray(insightsData?.insights) ? insightsData.insights : [])

      const ps = statsData.performance_stats || statsData || {}
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

  const markNotificationRead = async (notificationId) => {
    try {
      await driverAPI.markNotificationRead(notificationId)
      await fetchProfileData()
    } catch (err) {
      console.error('Failed to mark notification as read:', err)
    }
  }

  const unreadCount = notifications.filter((n) => !isNotificationRead(n)).length

  const headerAction = (
    <div className="flex flex-col gap-2 sm:flex-row">
      <button type="button" className="ha-btn ha-btn--ghost" onClick={() => navigate('/driver/settings')}>
        Settings
      </button>
      <button type="button" className="ha-btn ha-btn--ghost" onClick={() => navigate('/driver')}>
        Cockpit
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
      subtitle="Read-only driver settings from the backend. Go online/offline from the map cockpit."
      headerAction={headerAction}
    >
      <section className="ha-section">
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
              {tab.id === 'notifications' && unreadCount > 0 ? ` (${unreadCount})` : ''}
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
              <p className="text-sm" style={{ color: 'var(--ha-muted)' }}>
                Read-only account and vehicle status for the current driver.
              </p>
              <SettingsField label="Email" value={profile?.email} />
              <SettingsField label="Name" value={profile?.name} />
              <SettingsField label="Role" value={profile?.role} />
              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Approval status
                </div>
                <div
                  data-testid="driver-profile-approval-status"
                  className={
                    String(profile?.approval_status || '').toLowerCase() === 'approved'
                      ? 'mt-2 inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800'
                      : 'mt-2 inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800'
                  }
                >
                  {profile?.approval_status || 'pending'}
                </div>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Vehicle
                </div>
                <div className="mt-2 space-y-1 text-sm text-slate-800">
                  <div>Make: {profile?.vehicle?.make || 'Not registered'}</div>
                  <div>Model: {profile?.vehicle?.model || 'Not registered'}</div>
                  <div>Plate: {profile?.vehicle?.plate || 'Not registered'}</div>
                </div>
              </div>
              <div
                data-testid="driver-profile-readonly-note"
                className="rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900"
              >
                Read-only mode: account, approval, and vehicle details are managed by the system.
                No payment, bank, insurance, or dossier information is collected here.
              </div>
            </div>
          )}
        </section>
      )}

      {activeTab === 'notifications' && (
        <section className="ha-section" data-testid="account-notifications-panel">
          <h2 className="ha-section-title">
            Backend notifications
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
                        className="ha-btn ha-btn--ghost"
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
          <h2 className="ha-section-title">Measured stats (backend)</h2>
          {loading ? (
            <div className="ha-card ha-empty">Loading statistics…</div>
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
                  <div className="ha-stat-label">Average rating</div>
                  <div className="ha-stat-value">
                    {stats.average_rating != null && Number(stats.average_rating) > 0
                      ? formatStatNumber(stats.average_rating, 1)
                      : '—'}
                  </div>
                  <div className="ha-stat-meta">Shown only when backend provides a value</div>
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

              <div className="ha-card mt-3">
                <h3 className="ha-section-title">Dispatch insights</h3>
                {insights.length === 0 ? (
                  <p className="text-sm" style={{ color: 'var(--ha-muted)' }}>
                    No measured dispatch insights yet. The backend returns empty states until
                    rides are seen and claimed.
                  </p>
                ) : (
                  <ul className="space-y-3 mt-2">
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
                )}
              </div>
            </>
          )}
        </section>
      )}
    </AppShellLayout>
  )
}
