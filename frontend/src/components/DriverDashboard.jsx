import React, { useState, useEffect } from 'react'

export default function DriverDashboard({ apiBase }){
  const [availableRides, setAvailableRides] = useState([])
  const [myRides, setMyRides] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchData = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const headers = { Authorization: `Bearer ${token}` }
      
      const [availableRes, myRidesRes] = await Promise.all([
        fetch(`${apiBase}/drivers/available-rides`, { headers }),
        fetch(`${apiBase}/drivers/my-rides`, { headers })
      ])
      
      if (availableRes.ok && myRidesRes.ok) {
        setAvailableRides(await availableRes.json())
        setMyRides(await myRidesRes.json())
      }
    } catch (err) {
      setError('Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  const acceptRide = async (rideId) => {
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${apiBase}/drivers/accept-ride/${rideId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (res.ok) {
        await fetchData() // Refresh data
      } else {
        const error = await res.json()
        setError(error.detail || 'Failed to accept ride')
      }
    } catch (err) {
      setError('Failed to accept ride')
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  return (
    <div>
      <h2>Driver Dashboard</h2>
      {error && <p style={{color:'crimson'}}>Error: {error}</p>}
      
      <div style={{display:'flex', gap:24}}>
        <div style={{flex:1}}>
          <h3>Available Rides ({availableRides.length})</h3>
          {loading ? <p>Loading...</p> : (
            <div style={{border:'1px solid #ccc', padding:12, borderRadius:4}}>
              {availableRides.length === 0 ? (
                <p>No rides available</p>
              ) : (
                availableRides.map(ride => (
                  <div key={ride.id} style={{marginBottom:12, padding:8, background:'#f5f5f5', borderRadius:4}}>
                    <strong>Ride #{ride.id}</strong><br/>
                    Customer: {ride.customer_name}<br/>
                    Status: {ride.status}<br/>
                    <button 
                      onClick={() => acceptRide(ride.id)}
                      style={{marginTop:8, padding:'4px 8px', background:'#007bff', color:'white', border:'none', borderRadius:3}}
                    >
                      Accept Ride
                    </button>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
        
        <div style={{flex:1}}>
          <h3>My Rides ({myRides.length})</h3>
          <div style={{border:'1px solid #ccc', padding:12, borderRadius:4}}>
            {myRides.length === 0 ? (
              <p>No rides assigned</p>
            ) : (
              myRides.map(ride => (
                <div key={ride.id} style={{marginBottom:12, padding:8, background:'#e8f5e8', borderRadius:4}}>
                  <strong>Ride #{ride.id}</strong><br/>
                  Customer: {ride.customer_name}<br/>
                  Status: {ride.status}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      
      <button 
        onClick={fetchData} 
        style={{marginTop:16, padding:'8px 12px', background:'#28a745', color:'white', border:'none', borderRadius:4}}
      >
        Refresh Data
      </button>
    </div>
  )
}