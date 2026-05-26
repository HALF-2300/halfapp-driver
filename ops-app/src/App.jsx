import React from 'react'
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import AuthPage from './components/AuthPage.jsx'
import OpsLayout from './components/OpsLayout.jsx'
import RideListPage from './components/RideListPage.jsx'
import RideDetailPage from './components/RideDetailPage.jsx'
import DriverListPage from './components/DriverListPage.jsx'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('ops_token')
  return isAuthenticated || hasToken ? children : <Navigate to="/login" replace />
}

function AppRoutes() {
  const { isAuthenticated } = useAuth()
  const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('ops_token')
  const authed = isAuthenticated || hasToken

  return (
    <Routes>
      <Route path="/login" element={authed ? <Navigate to="/" replace /> : <AuthPage />} />
      <Route
        element={
          <ProtectedRoute>
            <OpsLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<RideListPage />} />
        <Route path="rides/:rideId" element={<RideDetailPage />} />
        <Route path="drivers" element={<DriverListPage />} />
      </Route>
      <Route path="*" element={<Navigate to={authed ? '/' : '/login'} replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <AppRoutes />
      </HashRouter>
    </AuthProvider>
  )
}
