import React, { useState } from 'react'

export default function Home({ apiBase }){
  const [name, setName] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const requestRide = async () => {
    setError('')
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${apiBase}/rides/`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ customer_name: name || 'Demo' })
      })
      
      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || 'Failed to create ride')
      }
      
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h2>Homepage</h2>
      <p>Create a ride to test authenticated flow.</p>
      
      <div style={{marginBottom:12}}>
        <input 
          placeholder="Customer name" 
          value={name} 
          onChange={e=>setName(e.target.value)}
          style={{padding:8, marginRight:8}} 
        />
        <button onClick={requestRide} style={{padding:8}}>Request Ride</button>
      </div>
      
      {error && <p style={{color:'crimson'}}>Error: {error}</p>}
      {result && (
        <div>
          <h3>Ride Created Successfully!</h3>
          <pre style={{background:'#f5f5f5', padding:12, borderRadius:4}}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}