import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function RiderRegister({ apiBase }){
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const nav = useNavigate()

  const inputStyle = {
    width: '100%', 
    padding: '12px', 
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '16px',
    boxSizing: 'border-box'
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    
    try{
      const res = await fetch(`${apiBase}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email, 
          name, 
          password, 
          role: 'customer'
        })
      })
      if(!res.ok){
        const msg = await res.json()
        throw new Error(msg.detail || 'Registration failed')
      }
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('role', data.role)
      nav('/customer')
    }catch(err){ setError(err.message) }
  }

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '20px',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <div style={{
        background: 'white',
        padding: '40px',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
        width: '100%',
        maxWidth: '400px'
      }}>
        <h1 style={{
          textAlign: 'center',
          marginBottom: '30px',
          color: '#333',
          fontSize: '28px',
          fontWeight: '600'
        }}>
          Ride with us
        </h1>
        
        <form onSubmit={submit}>
          {error && (
            <div style={{
              color: '#dc3545',
              marginBottom: '20px',
              padding: '10px',
              backgroundColor: '#f8d7da',
              border: '1px solid #f5c6cb',
              borderRadius: '4px'
            }}>
              {error}
            </div>
          )}
          
          <div style={{marginBottom: '20px'}}>
            <label style={{ display: 'block', marginBottom: '5px', color: '#555' }}>
              Full Name
            </label>
            <input 
              placeholder="Enter your full name" 
              value={name} 
              onChange={e=>setName(e.target.value)}
              required
              style={inputStyle}
            />
          </div>
          
          <div style={{marginBottom: '20px'}}>
            <label style={{ display: 'block', marginBottom: '5px', color: '#555' }}>
              Email
            </label>
            <input 
              placeholder="Enter your email" 
              type="email"
              value={email} 
              onChange={e=>setEmail(e.target.value)}
              required
              style={inputStyle}
            />
          </div>
          
          <div style={{marginBottom: '30px'}}>
            <label style={{ display: 'block', marginBottom: '5px', color: '#555' }}>
              Password
            </label>
            <input 
              placeholder="Create a password" 
              type="password" 
              value={password} 
              onChange={e=>setPassword(e.target.value)}
              required
              style={inputStyle} 
            />
          </div>
          
          <button 
            type="submit" 
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '16px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Create Rider Account
          </button>
        </form>
        
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <span style={{ color: '#666' }}>Already have an account? </span>
          <button
            onClick={() => nav('/rider/login')}
            style={{
              background: 'none',
              border: 'none',
              color: '#28a745',
              textDecoration: 'underline',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Sign In as Rider
          </button>
        </div>
        
        <div style={{ textAlign: 'center', marginTop: '15px' }}>
          <button
            onClick={() => nav('/')}
            style={{
              background: 'none',
              border: 'none',
              color: '#666',
              textDecoration: 'underline',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Back to Home
          </button>
        </div>
      </div>
    </div>
  )
}