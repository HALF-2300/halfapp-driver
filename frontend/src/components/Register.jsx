import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Register({ apiBase }){
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('customer')
  const [licenseNo, setLicenseNo] = useState('')
  const [error, setError] = useState('')
  const nav = useNavigate()

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
          role,
          license_no: role === 'driver' ? licenseNo : null
        })
      })
      if(!res.ok){
        const msg = await res.json()
        throw new Error(msg.detail || 'Registration failed')
      }
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('role', data.role)
      // Navigate based on role
      if (data.role === 'admin') {
        nav('/admin')
      } else if (data.role === 'driver') {
        nav('/driver')
      } else {
        nav('/home')
      }
    }catch(err){ setError(err.message) }
  }

  return (
    <form onSubmit={submit} style={{maxWidth:360}}>
      <h2>Register</h2>
      {error && <p style={{color:'crimson'}}>{error}</p>}
      <div style={{marginBottom:12}}>
        <input 
          placeholder="Email" 
          type="email"
          value={email} 
          onChange={e=>setEmail(e.target.value)}
          style={{width:'100%', padding:8}} 
        />
      </div>
      <div style={{marginBottom:12}}>
        <input 
          placeholder="Name" 
          value={name} 
          onChange={e=>setName(e.target.value)}
          style={{width:'100%', padding:8}} 
        />
      </div>
      <div style={{marginBottom:12}}>
        <input 
          placeholder="Password" 
          type="password" 
          value={password} 
          onChange={e=>setPassword(e.target.value)}
          style={{width:'100%', padding:8}} 
        />
      </div>
      <div style={{marginBottom:12}}>
        <select 
          value={role} 
          onChange={e=>setRole(e.target.value)}
          style={{width:'100%', padding:8}}
        >
          <option value="customer">Customer</option>
          <option value="driver">Driver</option>
          <option value="admin">Admin</option>
        </select>
      </div>
      {role === 'driver' && (
        <div style={{marginBottom:12}}>
          <input 
            placeholder="License Number (required for drivers)" 
            value={licenseNo} 
            onChange={e=>setLicenseNo(e.target.value)}
            style={{width:'100%', padding:8}} 
          />
        </div>
      )}
      <button type="submit" style={{padding:8}}>Create Account</button>
    </form>
  )
}