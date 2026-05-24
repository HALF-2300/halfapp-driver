import React from 'react'
import { Link } from 'react-router-dom'

export default function LandingPage() {
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
    maxWidth: '400px',
    width: '100%',
    textAlign: 'center',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    border: '1px solid #e1e5e9'
  }

  const titleStyle = {
    fontSize: '32px',
    fontWeight: '600',
    color: '#212529',
    marginBottom: '16px'
  }

  const subtitleStyle = {
    fontSize: '16px',
    color: '#6c757d',
    marginBottom: '32px',
    lineHeight: '1.5'
  }

  const linkStyle = {
    display: 'inline-block',
    padding: '12px 24px',
    margin: '8px',
    backgroundColor: '#007bff',
    color: 'white',
    textDecoration: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: '500',
    minWidth: '120px'
  }

  const adminLinkStyle = {
    ...linkStyle,
    backgroundColor: '#6c757d'
  }

  const driverButtonStyle = {
    ...linkStyle,
    backgroundColor: '#007bff',
    width: '100%',
    marginBottom: '12px',
    boxSizing: 'border-box'
  }

  const riderButtonStyle = {
    ...linkStyle,
    backgroundColor: '#28a745',
    width: '100%',
    marginBottom: '24px',
    boxSizing: 'border-box'
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h1 style={titleStyle}>HalfApp</h1>
        <p style={subtitleStyle}>
          Choose your experience: Drive to earn or ride in comfort
        </p>
        
        <div style={{ marginBottom: '32px' }}>
          <h3 style={{ color: '#495057', marginBottom: '16px', fontSize: '18px' }}>
            🚗 For Drivers
          </h3>
          <Link to="/driver/login" style={driverButtonStyle}>Drive with us - Sign In</Link>
          <Link to="/driver/register" style={driverButtonStyle}>Drive with us - Register</Link>
        </div>
        
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ color: '#495057', marginBottom: '16px', fontSize: '18px' }}>
            🏃 For Riders
          </h3>
          <Link to="/rider/login" style={riderButtonStyle}>Ride with us - Sign In</Link>
          <Link to="/rider/register" style={riderButtonStyle}>Ride with us - Register</Link>
        </div>
        
        <div>
          <Link to="/admin-access" style={adminLinkStyle}>Admin Access</Link>
        </div>
      </div>
    </div>
  )
}