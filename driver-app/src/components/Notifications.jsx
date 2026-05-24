import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import driverAPI from '../utils/api.js'
import AppShellLayout from './AppShellLayout.jsx'
import { useDriverPreferences } from '../context/DriverPreferencesContext.jsx'
import {
  formatNotificationTime,
  isNotificationRead,
  normalizeNotification,
} from '../utils/notificationDisplay.js'

const SHOW_DEMO_MESSAGES_TAB = import.meta.env.DEV

const DEMO_MESSAGES = [
  {
    name: 'Sample rider',
    message: 'Example message — rider chat is not connected to a live backend yet.',
    time: 'demo',
    avatar: 'SR',
    isRead: true,
  },
]

export default function Notifications() {
  const navigate = useNavigate()
  const { refreshUnreadNotifications } = useDriverPreferences()
  const [activeTab, setActiveTab] = useState('notifications')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [items, setItems] = useState([])
  const [markingIds, setMarkingIds] = useState(() => new Set())

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await driverAPI.getNotifications()
      const list = Array.isArray(data) ? data : data?.notifications ?? []
      setItems(list)
    } catch (err) {
      setItems([])
      setError(err?.message || 'Could not load notifications.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const unreadCount = useMemo(() => {
    return items.filter((n) => !isNotificationRead(n)).length
  }, [items])

  const subtitle = loading
    ? 'Loading…'
    : unreadCount > 0
      ? `${unreadCount} unread · in-app only (no push)`
      : 'All caught up · in-app only (no push)'

  const markRead = async (notification) => {
    const normalized = normalizeNotification(notification)
    if (!normalized.id || normalized.isRead) return

    setItems((prev) =>
      prev.map((row) => {
        const rowId = row?.id ?? row?.notification_id
        if (rowId !== normalized.id) return row
        return { ...row, read: true, is_read: true }
      })
    )

    setMarkingIds((prev) => new Set(prev).add(normalized.id))
    try {
      await driverAPI.markNotificationRead(normalized.id)
      await refreshUnreadNotifications()
    } catch (err) {
      await load()
      setError(err?.message || 'Could not mark notification as read.')
    } finally {
      setMarkingIds((prev) => {
        const next = new Set(prev)
        next.delete(normalized.id)
        return next
      })
    }
  }

  const headerAction = (
    <button type="button" className="ha-btn ha-btn--ghost" onClick={() => navigate('/driver')}>
      Cockpit
    </button>
  )

  return (
    <AppShellLayout
      testId="notifications-screen"
      title="Notifications"
      subtitle={subtitle}
      headerAction={headerAction}
    >
      {SHOW_DEMO_MESSAGES_TAB ? (
        <section className="ha-section">
          <div className="flex gap-2">
            <button
              type="button"
              data-testid="tab-notifications"
              className={`ha-btn flex-1 ${activeTab === 'notifications' ? 'ha-btn--primary' : 'ha-btn--ghost'}`}
              onClick={() => setActiveTab('notifications')}
            >
              Notifications
            </button>
            <button
              type="button"
              data-testid="tab-messages"
              className={`ha-btn flex-1 ${activeTab === 'messages' ? 'ha-btn--primary' : 'ha-btn--ghost'}`}
              onClick={() => setActiveTab('messages')}
            >
              Messages (dev)
            </button>
          </div>
        </section>
      ) : null}

      {activeTab === 'notifications' && (
        <section className="ha-section" data-testid="notifications-panel">
          {error ? (
            <div className="ha-alert ha-alert--error" data-testid="notifications-api-error">
              {error}
            </div>
          ) : null}

          {loading ? (
            <div className="ha-card ha-empty">Loading notifications…</div>
          ) : null}

          {!loading && !error && items.length === 0 ? (
            <div className="ha-card ha-empty" data-testid="notifications-empty">
              <p className="font-medium">No notifications</p>
              <p className="text-sm ha-truth-note mt-2">
                In-app updates appear here when rides change. Push delivery is not enabled in this
                build.
              </p>
              <Link to="/driver/settings" className="text-sm mt-3 inline-block" style={{ color: 'var(--ha-green)' }}>
                Notification preferences →
              </Link>
            </div>
          ) : null}

          {!loading && !error && items.length > 0 ? (
            <ul className="ha-list" data-testid="notifications-api-list">
              {items.map((row, index) => {
                const n = normalizeNotification(row, index)
                const marking = markingIds.has(n.id)
                return (
                  <li key={n.id}>
                    <button
                      type="button"
                      className="ha-list-item w-full text-left"
                      style={
                        n.isRead
                          ? { opacity: 0.85 }
                          : { borderColor: 'rgba(59, 130, 246, 0.45)' }
                      }
                      data-testid={`notification-row-${n.id}`}
                      aria-label={`notification-${n.id}`}
                      disabled={marking || n.isRead}
                      onClick={() => markRead(row)}
                    >
                      <div className="flex justify-between gap-3 w-full">
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold text-sm">{n.title}</div>
                          {n.message ? (
                            <p className="text-sm mt-1" style={{ color: 'var(--ha-muted)' }}>
                              {n.message}
                            </p>
                          ) : null}
                          <p className="ha-truth-note mt-1">
                            {formatNotificationTime(n.createdAt)}
                            {n.type ? ` · ${n.type}` : ''}
                          </p>
                        </div>
                        {!n.isRead ? (
                          <span
                            className="shrink-0 mt-1 w-2 h-2 rounded-full"
                            style={{ background: 'var(--ha-green)' }}
                            aria-hidden
                          />
                        ) : (
                          <span className="text-xs ha-truth-note shrink-0">Read</span>
                        )}
                      </div>
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : null}
        </section>
      )}

      {SHOW_DEMO_MESSAGES_TAB && activeTab === 'messages' ? (
        <section className="ha-section" data-testid="inbox-messages-panel">
          <div
            className="ha-alert mb-3"
            data-testid="inbox-messages-demo"
            role="status"
          >
            Development only — not live rider chat.
          </div>
          <ul className="ha-list">
            {DEMO_MESSAGES.map((message, index) => (
              <li key={index} className="ha-list-item">
                <div className="font-semibold text-sm">{message.name}</div>
                <p className="text-sm mt-1" style={{ color: 'var(--ha-muted)' }}>
                  {message.message}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {!SHOW_DEMO_MESSAGES_TAB ? (
        <section className="ha-section">
          <p className="text-xs ha-truth-note">
            Rider messaging is not available. See{' '}
            <Link to="/driver/profile" style={{ color: 'var(--ha-green)' }}>
              Profile
            </Link>{' '}
            for account details.
          </p>
        </section>
      ) : null}
    </AppShellLayout>
  )
}
