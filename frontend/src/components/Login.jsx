import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login({ apiBase }){
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const nav = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try{
      const res = await fetch(`${apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      if(!res.ok){
        const msg = await res.json()
        throw new Error(msg.detail || 'Login failed')
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
      <h2>Login</h2>
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
          placeholder="Password" 
          type="password" 
          value={password} 
          onChange={e=>setPassword(e.target.value)}
          style={{width:'100%', padding:8}} 
        />
      </div>
      <button type="submit" style={{padding:8}}>Login</button>
    </form>
  )
}