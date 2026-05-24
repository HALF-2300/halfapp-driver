import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Button, 
  Input, 
  Card, 
  CardHeader, 
  CardContent,
  Container,
  Stack,
  Flex
} from '../design/index.jsx'

export default function AdminLogin({ apiBase }) {
  const [mode, setMode] = useState('login') // 'login', 'register', 'generate'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [accessCode, setAccessCode] = useState('')
  const [generatedCode, setGeneratedCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const containerStyle = {
    minHeight: '100vh',
    backgroundColor: '#f8f9fa',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '20px',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  }

  const cardStyle = {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '40px',
    maxWidth: '400px',
    width: '100%',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    border: '1px solid #e1e5e9'
  }

  const inputStyle = {
    width: '100%',
    padding: '14px',
    margin: '8px 0',
    border: '2px solid #e1e5e9',
    borderRadius: '8px',
    fontSize: '16px',
    fontFamily: 'inherit',
    boxSizing: 'border-box'
  }

  const buttonStyle = {
    width: '100%',
    padding: '12px',
    margin: '12px 0',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    boxSizing: 'border-box'
  }

  const errorStyle = {
    backgroundColor: '#f8d7da',
    border: '1px solid #f5c6cb',
    color: '#721c24',
    padding: '12px',
    borderRadius: '6px',
    marginBottom: '16px'
  }



  const handleLogin = async () => {
    if (!email || !password) {
      setError('Please enter your email and password')
      return
    }

    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      const data = await res.json()

      if (res.ok) {
        if (data.role !== 'admin') {
          setError('This account does not have administrator privileges')
          return
        }

        localStorage.setItem('token', data.access_token)
        localStorage.setItem('role', data.role)
        navigate('/admin')
      } else {
        const errorDetail = data.detail
        if (typeof errorDetail === 'object') {
          setError(errorDetail.message || 'Login failed')
        } else {
          setError(errorDetail || 'Invalid credentials')
        }
      }
    } catch (err) {
      setError('Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const generateCode = async () => {
    if (!email) {
      setError('Please enter an email address for the new admin')
      return
    }

    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${apiBase}/admin-access/generate-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      })

      const data = await res.json()

      if (res.ok) {
        setGeneratedCode(data.access_code)
        setEmail('') // Clear email for next code generation
      } else {
        const errorDetail = data.detail
        setError(errorDetail?.message || errorDetail || 'Failed to generate code')
      }
    } catch (err) {
      setError('Failed to connect to server. Please check if the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const registerAdmin = async () => {
    if (!accessCode || !email || !name || !password) {
      setError('Please fill in all fields')
      return
    }

    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${apiBase}/admin-access/register-admin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_code: accessCode, email, name, password })
      })

      const data = await res.json()

      if (res.ok) {
        setMode('login')
        setError('')
        alert('Admin account created! Please login.')
      } else {
        const errorDetail = data.detail
        setError(errorDetail.message || 'Registration failed')
      }
    } catch (err) {
      setError('Registration failed')
    } finally {
      setLoading(false)
    }
  }



  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        {mode === 'login' && (
          <>
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
              <h1 style={{ color: '#333', marginBottom: '8px', fontSize: '28px' }}>🏢 Admin Sign In</h1>
              <p style={{ color: '#666', fontSize: '16px' }}>Access your administrator dashboard</p>
            </div>

            {error && <div style={errorStyle}>{error}</div>}

            <input
              type="email"
              placeholder="Admin Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={inputStyle}
              disabled={loading}
            />

            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={inputStyle}
              disabled={loading}
            />

            <button 
              onClick={handleLogin}
              disabled={loading}
              style={buttonStyle}
            >
              {loading ? 'Signing In...' : 'Sign In'}
            </button>

            <div style={{ textAlign: 'center', marginTop: '20px' }}>
              <button 
                onClick={() => setMode('register')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#007bff',
                  textDecoration: 'underline',
                  cursor: 'pointer',
                  marginRight: '16px'
                }}
              >
                Register with Code
              </button>
              <button 
                onClick={() => setMode('generate')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#007bff',
                  textDecoration: 'underline',
                  cursor: 'pointer'
                }}
              >
                Generate Code
              </button>
            </div>
          </>
        )}

        {mode === 'register' && (
          <>
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
              <h1 style={{ color: '#333', marginBottom: '8px', fontSize: '28px' }}>🎯 Register as Admin</h1>
              <p style={{ color: '#666', fontSize: '16px' }}>Use your access code to create an admin account</p>
            </div>

            {error && <div style={errorStyle}>{error}</div>}

            <input
              type="text"
              placeholder="Access Code"
              value={accessCode}
              onChange={(e) => setAccessCode(e.target.value.toUpperCase())}
              style={inputStyle}
              disabled={loading}
            />

            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={inputStyle}
              disabled={loading}
            />

            <input
              type="text"
              placeholder="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={inputStyle}
              disabled={loading}
            />

            <input
              type="password"
              placeholder="Password (min 6 chars)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={inputStyle}
              disabled={loading}
            />

            <button 
              onClick={registerAdmin}
              disabled={loading}
              style={buttonStyle}
            >
              {loading ? 'Creating Account...' : 'Create Admin Account'}
            </button>

            <div style={{ textAlign: 'center', marginTop: '20px' }}>
              <button 
                onClick={() => setMode('login')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#007bff',
                  textDecoration: 'underline',
                  cursor: 'pointer'
                }}
              >
                ← Back to Login
              </button>
            </div>
          </>
        )}

        {mode === 'generate' && (
          <>
            <div style={{ textAlign: 'center', marginBottom: '32px' }}>
              <h1 style={{ color: '#333', marginBottom: '8px', fontSize: '28px' }}>🔑 Generate Access Code</h1>
              <p style={{ color: '#666', fontSize: '16px' }}>Create a code for someone to register as admin</p>
            </div>

            {error && <div style={errorStyle}>{error}</div>}

            <input
              type="email"
              placeholder="Email for new admin"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={inputStyle}
              disabled={loading}
            />

            <button 
              onClick={generateCode}
              disabled={loading}
              style={buttonStyle}
            >
              {loading ? 'Generating...' : 'Generate Access Code'}
            </button>

            {generatedCode && (
              <div style={{
                backgroundColor: '#d4edda',
                border: '1px solid #c3e6cb',
                padding: '20px',
                borderRadius: '6px',
                margin: '20px 0',
                textAlign: 'center'
              }}>
                <h3 style={{ color: '#155724', marginBottom: '12px' }}>Access Code Generated!</h3>
                <div style={{
                  fontSize: '28px',
                  fontWeight: 'bold',
                  fontFamily: 'monospace',
                  letterSpacing: '3px',
                  color: '#007bff',
                  backgroundColor: '#f8f9fa',
                  padding: '12px',
                  borderRadius: '4px',
                  border: '2px dashed #007bff',
                  marginBottom: '12px'
                }}>
                  {generatedCode}
                </div>
                <p style={{ fontSize: '14px', color: '#155724', marginBottom: '12px' }}>
                  Share this code with the person who needs admin access
                </p>
                <button 
                  onClick={() => {
                    navigator.clipboard.writeText(generatedCode)
                  }}
                  style={{
                    ...buttonStyle,
                    backgroundColor: '#28a745',
                    marginTop: '0px',
                    marginBottom: '8px'
                  }}
                >
                  📋 Copy Code
                </button>
                <button 
                  onClick={() => {
                    setGeneratedCode('')
                    setEmail('')
                  }}
                  style={{
                    ...buttonStyle,
                    backgroundColor: '#6c757d',
                    marginTop: '0px'
                  }}
                >
                  Generate Another
                </button>
              </div>
            )}

            <div style={{ textAlign: 'center', marginTop: '20px' }}>
              <button 
                onClick={() => setMode('login')}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#007bff',
                  textDecoration: 'underline',
                  cursor: 'pointer'
                }}
              >
                ← Back to Login
              </button>
            </div>
          </>
        )}

        <div style={{ textAlign: 'center', marginTop: '24px', paddingTop: '20px', borderTop: '1px solid #e1e5e9' }}>
          <button 
            onClick={() => navigate('/landing')}
            style={{
              background: 'none',
              border: 'none',
              color: '#6c757d',
              textDecoration: 'underline',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            ← Back to main site
          </button>
        </div>
      </div>
    </div>
  )
}