import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import driverAPI from '../utils/api.js'
import AppShellLayout from './AppShellLayout.jsx'
import { useDriverPreferences } from '../context/DriverPreferencesContext.jsx'
import {
  formatNotificationTime,
  isNotificationRead,
  normalizeNotification,
} from '../utils/notificationDisplay.js'

const SHOW_DEMO_MESSAGES_TAB = import.meta.env.DEV && false

export default function Notifications() {
  const { refreshUnreadNotifications } = useDriverPreferences()
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
      ? `${unreadCount} unread · in-app only`
      : 'All caught up'

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

  const markAllRead = async () => {
    const unread = items.filter((n) => !isNotificationRead(n))
    if (unread.length === 0) return
    await Promise.all(unread.map((n) => markRead(n).catch(() => null)))
    await refreshUnreadNotifications()
  }

  const headerAction = unreadCount > 0 ? (
    <button type="button" className="ha-btn ha-btn--ghost" onClick={markAllRead}>
      Mark all read
    </button>
  ) : null

  return (
    <AppShellLayout
      testId="notifications-screen"
      title="Notifications"
      subtitle={subtitle}
      headerAction={headerAction}
    >
      <section className="ha-section" style={{ paddingTop: '1rem' }} data-testid="notifications-panel">
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
            <div
              className="mx-auto mb-3 w-10 h-10 rounded-full flex items-center justify-center"
              style={{ background: 'rgba(255,255,255,0.06)' }}
            >
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none" style={{ color: 'var(--ha-muted)' }}>
                <path d="M10 2a5 5 0 00-5 5v2.5c0 .7-.3 1.4-.8 1.9L3 13.5h14l-1.2-2.1c-.5-.5-.8-1.2-.8-1.9V7a5 5 0 00-5-5zm0 16a2.5 2.5 0 01-2.45-2h4.9A2.5 2.5 0 0110 18z" fill="currentColor" />
              </svg>
            </div>
            <p className="font-medium">No notifications</p>
            <p className="ha-truth-note mt-2">
              Ride lifecycle updates appear here. Push delivery is not enabled in this build.
            </p>
            <Link
              to="/driver/settings"
              className="text-sm mt-3 inline-block"
              style={{ color: 'var(--ha-green)' }}
            >
              Notification preferences →
            </Link>
          </div>
        ) : null}

        {!loading && !error && items.length > 0 ? (
          <ul className="ha-list" data-testid="notifications-api-list">
            {items.map((row, index) => {
              const n = normalizeNotification(row, index)
              const marking = markingIds.has(n.id)
              const unread = !n.isRead
              return (
                <li key={n.id}>
                  <button
                    type="button"
                    className="w-full text-left"
                    style={{
                      background: unread ? 'rgba(59,130,246,0.07)' : 'var(--ha-surface)',
                      border: `1px solid ${unread ? 'rgba(59,130,246,0.35)' : 'var(--ha-border)'}`,
                      borderRadius: 'var(--ha-radius-lg)',
                      padding: '0.85rem 1rem',
                      backdropFilter: 'blur(18px)',
                      display: 'block',
                      width: '100%',
                    }}
                    data-testid={`notification-row-${n.id}`}
                    aria-label={`notification-${n.id}`}
                    disabled={marking || n.isRead}
                    onClick={() => markRead(row)}
                  >
                    <div className="flex justify-between gap-3 w-full">
                      <div className="min-w-0 flex-1">
                        <div
                          className="text-sm font-semibold leading-snug"
                          style={{ color: unread ? 'var(--ha-text)' : 'var(--ha-muted)' }}
                        >
                          {n.title}
                        </div>
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
                      <div className="shrink-0 flex flex-col items-end gap-1 mt-0.5">
                        {unread ? (
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ background: 'var(--ha-blue)', flexShrink: 0, marginTop: '3px' }}
                            aria-hidden
                          />
                        ) : (
                          <span className="text-[10px]" style={{ color: 'var(--ha-muted)' }}>Read</span>
                        )}
                      </div>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : null}

        {!loading && (
          <p className="ha-truth-note text-center mt-4">
            In-app notifications only · push delivery not enabled
          </p>
        )}
      </section>
    </AppShellLayout>
  )
}
