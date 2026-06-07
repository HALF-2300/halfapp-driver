import React from 'react'
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import AuthPage from './components/AuthPage.jsx'
import RequestRidePage from './components/RequestRidePage.jsx'
import RideDetailPage from './components/RideDetailPage.jsx'
import ProfilePage from './components/ProfilePage.jsx'
import HelpPage from './components/HelpPage.jsx'
import SafetyToolkitPage from './components/SafetyToolkitPage.jsx'
import NotificationsPage from './components/NotificationsPage.jsx'
import DeliveryOrderPage from './components/DeliveryOrderPage.jsx'
import DeliveryOrderDetailPage from './components/DeliveryOrderDetailPage.jsx'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('rider_token')
  return isAuthenticated || hasToken ? children : <Navigate to="/login" replace />
}

function AppRoutes() {
  const { isAuthenticated } = useAuth()
  const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('rider_token')
  const authed = isAuthenticated || hasToken

  return (
    <Routes>
      <Route path="/login" element={authed ? <Navigate to="/" replace /> : <AuthPage mode="login" />} />
      <Route path="/register" element={authed ? <Navigate to="/" replace /> : <AuthPage mode="register" />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <RequestRidePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ride/:rideId"
        element={
          <ProtectedRoute>
            <RideDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/delivery"
        element={
          <ProtectedRoute>
            <DeliveryOrderPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/delivery/:orderId"
        element={
          <ProtectedRoute>
            <DeliveryOrderDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/help"
        element={
          <ProtectedRoute>
            <HelpPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/safety"
        element={
          <ProtectedRoute>
            <SafetyToolkitPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/notifications"
        element={
          <ProtectedRoute>
            <NotificationsPage />
          </ProtectedRoute>
        }
      />
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
