import React, { Suspense, lazy } from 'react'

import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'

import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import { DriverPreferencesProvider } from './context/DriverPreferencesContext.jsx'

import ErrorBoundary from './components/ErrorBoundary'



import HalfAppDriverPortalFrontPage from './frontpage/HalfAppDriverPortalFrontPage.jsx'

import DevBanner from './components/DevBanner'

import MockModeBanner from './components/MockModeBanner'
import BetaTruthNotice from './components/BetaTruthNotice'

import MapHome from './components/MapHome'

import TripsList from './components/TripsList'
import TripAuditReceipt from './components/TripAuditReceipt.jsx'

import Earnings from './components/Earnings'

import Notifications from './components/Notifications'

import Profile from './components/Profile'
import DriverSettings from './components/DriverSettings.jsx'

import { isEngineeringIntelligenceEnabled } from './utils/engineeringIntelligenceContext.js'

const HalfAppEngineeringIntelligence = lazy(
  () => import('./components/HalfAppEngineeringIntelligence.jsx')
)



const COCKPIT_PATH = '/driver'



const ALLOW_ROUTE_GUARD_BYPASS =

  import.meta.env.MODE !== 'production' && import.meta.env.VITE_ENABLE_GUARD_BYPASS === 'true'



function ProtectedRoute({ children }) {

  const { isAuthenticated } = useAuth()

  const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('driver_token')

  const disableGuard =

    ALLOW_ROUTE_GUARD_BYPASS &&

    typeof window !== 'undefined' &&

    localStorage.getItem('disable_guard') === 'true'

  if (disableGuard) return children

  return (isAuthenticated || hasToken) ? children : <Navigate to="/" replace />

}



function AppRoutes() {

  const { isAuthenticated } = useAuth()

  const hasToken = typeof window !== 'undefined' && !!localStorage.getItem('driver_token')

  const authed = isAuthenticated || hasToken



  return (

    <Routes>

      <Route

        path="/login"

        element={authed ? <Navigate to={COCKPIT_PATH} replace /> : <HalfAppDriverPortalFrontPage />}

      />



      <Route

        path="/"

        element={authed ? <Navigate to={COCKPIT_PATH} replace /> : <HalfAppDriverPortalFrontPage />}

      />



      <Route

        path={COCKPIT_PATH}

        element={

          <ProtectedRoute>

            <MapHome />

          </ProtectedRoute>

        }

      />



      <Route path="/driver/cockpit" element={<Navigate to={COCKPIT_PATH} replace />} />



      <Route

        path="/driver/trips"

        element={

          <ProtectedRoute>

            <TripsList />

          </ProtectedRoute>

        }

      />

      <Route
        path="/driver/trips/:rideId/audit"
        element={
          <ProtectedRoute>
            <TripAuditReceipt />
          </ProtectedRoute>
        }
      />

      <Route path="/driver/earnings" element={<ProtectedRoute><Earnings /></ProtectedRoute>} />

      <Route path="/driver/settings" element={<ProtectedRoute><DriverSettings /></ProtectedRoute>} />
      <Route path="/driver/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />

      <Route path="/driver/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />



      {isEngineeringIntelligenceEnabled() ? (
        <Route
          path="/engineering-intelligence"
          element={
            <Suspense fallback={null}>
              <HalfAppEngineeringIntelligence />
            </Suspense>
          }
        />
      ) : null}



      <Route path="/rides" element={<Navigate to="/driver/trips" replace />} />

      <Route path="/trips" element={<Navigate to="/driver/trips" replace />} />

      <Route path="/earnings" element={<Navigate to="/driver/earnings" replace />} />

      <Route path="/profile" element={<Navigate to="/driver/settings" replace />} />

      <Route path="/notifications" element={<Navigate to="/driver/notifications" replace />} />



      <Route path="*" element={<Navigate to="/" replace />} />

    </Routes>

  )

}



function App() {

  return (

    <ErrorBoundary>

      <div className="min-h-screen bg-[#050814]">

        <DevBanner />

        <MockModeBanner />
        <div className="px-4 pt-2">
          <BetaTruthNotice variant="compact" />
        </div>

        <HashRouter>

          <AuthProvider>

            <DriverPreferencesProvider>

              <AppRoutes />

            </DriverPreferencesProvider>

          </AuthProvider>

        </HashRouter>

      </div>

    </ErrorBoundary>

  )

}



export default App


