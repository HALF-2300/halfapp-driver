import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Welcome({ apiBase }){
  const [me, setMe] = useState(null)
  const [health, setHealth] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    // Check API health
    fetch(`${apiBase}/health`).then(r=>r.json()).then(setHealth).catch(() => {})
    
    // Get current user info
    const token = localStorage.getItem('token')
    const role = localStorage.getItem('role')
    
    if(!token) {
      navigate('/landing')
      return
    }
    
    fetch(`${apiBase}/auth/me`, { headers: { Authorization: `Bearer ${token}` }})
      .then(r => r.ok ? r.json() : null)
      .then(setMe)
      .catch(() => {})
  }, [apiBase, navigate])

  const containerStyle = {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f8f9fa',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  }

  const cardStyle = {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '48px',
    maxWidth: '500px',
    width: '100%',
    textAlign: 'center',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    border: '1px solid #e1e5e9'
  }

  const titleStyle = {
    fontSize: '28px',
    fontWeight: '600',
    color: '#212529',
    marginBottom: '16px'
  }

  const statusStyle = {
    padding: '8px 16px',
    borderRadius: '20px',
    fontSize: '14px',
    fontWeight: '500',
    marginBottom: '24px',
    display: 'inline-block'
  }

  const healthStatusStyle = {
    ...statusStyle,
    backgroundColor: health ? '#d4edda' : '#f8d7da',
    color: health ? '#155724' : '#721c24'
  }

  const userInfoStyle = {
    backgroundColor: '#e9ecef',
    padding: '16px',
    borderRadius: '6px',
    marginBottom: '24px'
  }

  const buttonStyle = {
    display: 'inline-block',
    padding: '12px 24px',
    backgroundColor: '#007bff',
    color: 'white',
    textDecoration: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: '500',
    border: 'none',
    cursor: 'pointer',
    boxSizing: 'border-box'
  }

  const getDashboardLink = () => {
    const role = localStorage.getItem('role')
    switch(role) {
      case 'admin': return '/admin'
      case 'driver': return '/driver'
      case 'customer': return '/customer'
      default: return '/customer'
    }
  }

  const getRoleDisplayName = () => {
    const role = localStorage.getItem('role')
    switch(role) {
      case 'admin': return 'Administrator'
      case 'driver': return 'Driver'
      case 'customer': return 'Customer'
      default: return 'User'
    }
  }

  if (!me) {
    return (
      <div style={containerStyle}>
        <div style={cardStyle}>
          <h1 style={titleStyle}>Loading...</h1>
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h1 style={titleStyle}>Welcome to HalfApp</h1>
        
        <div style={healthStatusStyle}>
          API Status: {health ? '✅ Online' : '❌ Offline'}
        </div>

        <div style={userInfoStyle}>
          <div style={{ fontSize: '18px', fontWeight: '500', marginBottom: '8px' }}>
            {me.name}
          </div>
          <div style={{ fontSize: '14px', color: '#6c757d', marginBottom: '8px' }}>
            {me.email}
          </div>
          <div style={{ fontSize: '14px', color: '#495057' }}>
            Role: {getRoleDisplayName()}
          </div>
        </div>

        <button 
          onClick={() => navigate(getDashboardLink())}
          style={buttonStyle}
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  )
}