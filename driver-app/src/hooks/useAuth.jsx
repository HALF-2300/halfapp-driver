import React, { useState, useEffect, createContext, useContext } from 'react'
import driverAPI from '../utils/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // `isLoading` is the spinner/disabled state for **explicit user actions**
  // (login/register). The startup token-rehydration check below runs in the
  // background and must not gate the login form, otherwise a slow ERR_CONNECTION_REFUSED
  // on the initial /auth/me probe leaves the submit button disabled for ~1.5s after
  // logout in the offline-mock dev lane.
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const checkAuth = async () => {
      try {
        const driverToken = localStorage.getItem('driver_token')
        const driverRole = localStorage.getItem('driver_role')

        if (driverToken && driverRole === 'driver') {
          const profile = await driverAPI.getProfile()
          if (cancelled) return
          if (profile.role === 'driver') {
            setUser(profile)
          } else {
            driverAPI.logout()
            setUser(null)
          }
        }
      } catch (err) {
        if (cancelled) return
        console.error('Auth check failed:', err)
        driverAPI.logout()
        setUser(null)
      }
    }

    checkAuth()
    return () => {
      cancelled = true
    }
  }, [])

  const login = async (email, password) => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await driverAPI.login(email, password)

      if (response.role !== 'driver') {
        throw new Error(`Access denied: This is a driver app. Only drivers can login here (got ${response.role}).`)
      }

      const profile = response.user
      if (!profile || profile.role !== 'driver') {
        throw new Error('Access denied: Invalid driver profile from server.')
      }

      setUser(profile)
      return response
    } catch (err) {
      driverAPI.logout()
      setUser(null)
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (userData) => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await driverAPI.register(userData)

      if (response.role !== 'driver') {
        throw new Error('Registration failed: Only driver accounts can be created in this app')
      }

      const profile = response.user
      if (!profile || profile.role !== 'driver') {
        throw new Error('Registration failed: Profile role mismatch')
      }

      setUser(profile)
      return response
    } catch (err) {
      driverAPI.logout()
      setUser(null)
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    driverAPI.logout()
    setUser(null)
    setError(null)
  }

  const clearError = () => {
    setError(null)
  }

  const value = {
    user,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
    isAuthenticated: !!user
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
