import React, { createContext, useContext, useEffect, useState } from 'react'
import { clearSession, fetchProfile, getStoredToken, loginAdmin } from '../utils/api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const token = getStoredToken()
    if (!token) return undefined

    fetchProfile()
      .then((profile) => {
        if (cancelled) return
        if (profile.role === 'admin') {
          setUser(profile)
        } else {
          clearSession()
        }
      })
      .catch(() => {
        if (!cancelled) clearSession()
      })

    return () => {
      cancelled = true
    }
  }, [])

  const login = async (email, password) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await loginAdmin(email, password)
      setUser(response.user)
      return response
    } catch (err) {
      clearSession()
      setUser(null)
      setError(err.message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    clearSession()
    setUser(null)
    setError(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        error,
        login,
        logout,
        clearError: () => setError(null),
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
