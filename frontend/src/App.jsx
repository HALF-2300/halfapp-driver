import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Link, Navigate, useNavigate } from 'react-router-dom'
import LandingPage from './components/LandingPage'
import Login from './components/Login'
import Register from './components/Register'
import DriverLogin from './components/DriverLogin'
import DriverRegister from './components/DriverRegister'
import RiderLogin from './components/RiderLogin'
import RiderRegister from './components/RiderRegister'
import Welcome from './components/Welcome'
import CustomerDashboard from './components/CustomerDashboard'
import DriverDashboard from './components/DriverDashboard'
import AdminDashboard from './components/AdminDashboard'
import AdminLogin from './components/AdminLogin'
import StabilityDashboard from './components/StabilityDashboard'
import stabilityTracker from './utils/stabilityTracker'

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function Nav(){
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role')
  const nav = useNavigate()
  const logout = () => { 
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    nav('/landing') 
  }
  
  // Only show nav if user is logged in
  if (!token) return null
  
  const navStyle = {
    display: 'flex',
    gap: 16,
    marginBottom: 20,
    alignItems: 'center',
    padding: '12px 20px',
    backgroundColor: 'white',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    borderBottom: '1px solid #e1e5e9'
  }

  const linkStyle = {
    textDecoration: 'none',
    color: '#007bff',
    fontWeight: '500'
  }

  const userInfoStyle = {
    marginLeft: 'auto',
    fontSize: '14px',
    color: '#6c757d'
  }

  const buttonStyle = {
    padding: '6px 12px',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer'
  }
  
  return (
    <nav style={navStyle}>
      <Link to="/" style={linkStyle}>Dashboard</Link>
      {role === 'admin' && <Link to="/admin" style={linkStyle}>Admin Panel</Link>}
      {role === 'driver' && <Link to="/driver" style={linkStyle}>Driver Dashboard</Link>}
      {role === 'customer' && <Link to="/customer" style={linkStyle}>Customer Dashboard</Link>}
      
      <span style={userInfoStyle}>
        Logged in as {role}
      </span>
      <button onClick={logout} style={buttonStyle}>Logout</button>
    </nav>
  )
}

function Protected({children, requiredRole = null}){
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role')
  
  if (!token) return <Navigate to="/" replace />
  if (requiredRole && role !== requiredRole) return <Navigate to="/" replace />
  
  return children
}

export default function App(){
  useEffect(() => {
    // Initialize stability tracking
    stabilityTracker.logEvent('app_start', {
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    })
    
    // Track route changes
    const handleRouteChange = () => {
      stabilityTracker.logEvent('route_change', {
        path: window.location.pathname,
        timestamp: new Date().toISOString()
      })
    }
    
    // Listen for popstate events (back/forward navigation)
    window.addEventListener('popstate', handleRouteChange)
    
    return () => {
      window.removeEventListener('popstate', handleRouteChange)
      stabilityTracker.logEvent('app_unmount', {
        timestamp: new Date().toISOString()
      })
    }
  }, [])

  return (
    <BrowserRouter>
      <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
        <Nav />
        <Routes>
          {/* Main landing page for unauthenticated users */}
          <Route path="/" element={<LandingPage />} />
          
          {/* Legacy routes - redirect to new structure */}
          <Route path="/landing" element={<Navigate to="/" replace />} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="/register" element={<Navigate to="/" replace />} />
          
          {/* Driver routes */}
          <Route path="/driver/login" element={<DriverLogin apiBase={apiBase} />} />
          <Route path="/driver/register" element={<DriverRegister apiBase={apiBase} />} />
          <Route path="/driver" element={<Protected requiredRole="driver"><DriverDashboard apiBase={apiBase} /></Protected>} />
          
          {/* Rider/Customer routes */}
          <Route path="/rider/login" element={<RiderLogin apiBase={apiBase} />} />
          <Route path="/rider/register" element={<RiderRegister apiBase={apiBase} />} />
          <Route path="/customer" element={<Protected requiredRole="customer"><CustomerDashboard apiBase={apiBase} /></Protected>} />
          
          {/* Admin routes */}
          <Route path="/admin-access" element={<AdminLogin apiBase={apiBase} />} />
          <Route path="/admin" element={<Protected requiredRole="admin"><AdminDashboard apiBase={apiBase} /></Protected>} />
          <Route path="/admin/stability" element={<Protected requiredRole="admin"><StabilityDashboard /></Protected>} />
          
          {/* Authenticated dashboard (redirects to role-specific dashboard) */}
          <Route path="/home" element={<Welcome apiBase={apiBase} />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}