import React from 'react'
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import AuthPage from './components/AuthPage.jsx'
import OpsLayout from './components/OpsLayout.jsx'
import RideListPage from './components/RideListPage.jsx'
import RideDetailPage from './components/RideDetailPage.jsx'
import DriverListPage from './components/DriverListPage.jsx'
import ReadinessBoardPage from './components/ReadinessBoardPage.jsx'
import SupportCasesListPage from './components/SupportCasesListPage.jsx'
import SupportCaseDetailPage from './components/SupportCaseDetailPage.jsx'
import DeliveryOpsPage from './components/DeliveryOpsPage.jsx'
import DeliveryOpsDetailPage from './components/DeliveryOpsDetailPage.jsx'
import MerchantDeliveryPortal from './components/MerchantDeliveryPortal.jsx'

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
      <Route path="/merchant" element={<MerchantDeliveryPortal />} />
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
        <Route path="deliveries" element={<DeliveryOpsPage />} />
        <Route path="deliveries/:orderId" element={<DeliveryOpsDetailPage />} />
        <Route path="readiness" element={<ReadinessBoardPage />} />
        <Route path="support" element={<SupportCasesListPage />} />
        <Route path="support/:caseId" element={<SupportCaseDetailPage />} />
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
