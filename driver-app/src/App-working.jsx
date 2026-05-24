import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import HalfAppDriverPortalFrontPage from './frontpage/HalfAppDriverPortalFrontPage.jsx'
import Dashboard from './components/Dashboard'

// Protected Route Component
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth()
  // Instant render: while auth state is resolving (isLoading), optimistically render children.
  // Once loading finishes, if unauthenticated, redirect.
  if (!isLoading && !isAuthenticated) return <Navigate to="/login" replace />
  return children
}

// Main App Component
function App() {
  console.log('🚀 Half-App Driver starting... [UPDATED]')
  
  return (
    <BrowserRouter>
      <AuthProvider>
        <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb' }}>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<HalfAppDriverPortalFrontPage />} />
            
            {/* Protected Routes */}
            <Route path="/" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            
            {/* Fallback */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </div>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App