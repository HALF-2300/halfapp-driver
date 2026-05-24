import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import driverAPI from '../utils/api.js'
import { applyTheme } from '../state/useTheme.js'
import { useAuth } from '../hooks/useAuth.jsx'

const DriverPreferencesContext = createContext(null)

const DEFAULT_PREFS = {
  units: 'mi',
  locale: 'en-US',
  theme: 'system',
  notif_push_enabled: false,
  notif_sound_enabled: true,
  notif_quiet_hours: null,
}

export function DriverPreferencesProvider({ children }) {
  const { isAuthenticated } = useAuth()
  const [preferences, setPreferences] = useState(DEFAULT_PREFS)
  const [loading, setLoading] = useState(false)
  const [unreadNotifications, setUnreadNotifications] = useState(0)

  const refreshPreferences = useCallback(async () => {
    if (!isAuthenticated) {
      setPreferences(DEFAULT_PREFS)
      applyTheme('system')
      return
    }
    setLoading(true)
    try {
      const settings = await driverAPI.getDriverAppSettings()
      const next = { ...DEFAULT_PREFS, ...(settings || {}) }
      setPreferences(next)
      applyTheme(next.theme)
      if (next.locale && typeof document !== 'undefined') {
        document.documentElement.lang = next.locale.split('-')[0] || 'en'
      }
    } catch {
      applyTheme('system')
    } finally {
      setLoading(false)
    }
  }, [isAuthenticated])

  const refreshUnreadNotifications = useCallback(async () => {
    if (!isAuthenticated) {
      setUnreadNotifications(0)
      return
    }
    try {
      const data = await driverAPI.getNotifications()
      const list = Array.isArray(data) ? data : data?.notifications || []
      const unread =
        typeof data?.unread_count === 'number'
          ? data.unread_count
          : list.filter((n) => !n.read && !n.is_read && !n.read_at).length
      setUnreadNotifications(unread)
    } catch {
      setUnreadNotifications(0)
    }
  }, [isAuthenticated])

  useEffect(() => {
    refreshPreferences()
  }, [refreshPreferences])

  useEffect(() => {
    refreshUnreadNotifications()
    if (!isAuthenticated) return undefined
    const id = window.setInterval(refreshUnreadNotifications, 60_000)
    return () => window.clearInterval(id)
  }, [isAuthenticated, refreshUnreadNotifications])

  const updatePreferences = useCallback(
    async (patch) => {
      const next = await driverAPI.putDriverAppSettings(patch)
      setPreferences((prev) => ({ ...prev, ...(next || {}) }))
      if (patch.theme != null) applyTheme(next?.theme ?? patch.theme)
      if (next?.locale) document.documentElement.lang = next.locale.split('-')[0] || 'en'
      return next
    },
    []
  )

  const value = useMemo(
    () => ({
      preferences,
      units: preferences.units || 'mi',
      locale: preferences.locale || 'en-US',
      theme: preferences.theme || 'system',
      loading,
      unreadNotifications,
      refreshPreferences,
      refreshUnreadNotifications,
      updatePreferences,
    }),
    [
      preferences,
      loading,
      unreadNotifications,
      refreshPreferences,
      refreshUnreadNotifications,
      updatePreferences,
    ]
  )

  return (
    <DriverPreferencesContext.Provider value={value}>
      {children}
    </DriverPreferencesContext.Provider>
  )
}

export function useDriverPreferences() {
  const ctx = useContext(DriverPreferencesContext)
  if (!ctx) {
    throw new Error('useDriverPreferences must be used within DriverPreferencesProvider')
  }
  return ctx
}
