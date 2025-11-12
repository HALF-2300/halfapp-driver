import React, { useState, useEffect } from 'react'

export default function CustomerDashboard({ apiBase }) {
  const [rides, setRides] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [newRide, setNewRide] = useState({ pickup: '', destination: '' })

  const containerStyle = {
    minHeight: '100vh',
    backgroundColor: '#f8f9fa',
    padding: '20px',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  }

  const headerStyle = {
    textAlign: 'center',
    marginBottom: '40px'
  }

  const titleStyle = {
    fontSize: '32px',
    fontWeight: '600',
    color: '#212529',
    marginBottom: '8px'
  }

  const subtitleStyle = {
    fontSize: '16px',
    color: '#6c757d'
  }

  const cardStyle = {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '24px',
    marginBottom: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    border: '1px solid #e1e5e9',
    maxWidth: '800px',
    margin: '0 auto 20px auto'
  }

  const inputStyle = {
    width: '100%',
    padding: '12px',
    marginBottom: '12px',
    border: '1px solid #ced4da',
    borderRadius: '6px',
    fontSize: '16px',
    boxSizing: 'border-box'
  }

  const buttonStyle = {
    padding: '12px 24px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    width: '100%',
    boxSizing: 'border-box'
  }

  const fetchRides = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${apiBase}/rides/my-rides`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        setRides(await res.json())
      }
    } catch (err) {
      setError('Failed to fetch rides')
    } finally {
      setLoading(false)
    }
  }

  const requestRide = async () => {
    if (!newRide.pickup || !newRide.destination) {
      setError('Please fill in both pickup and destination')
      return
    }

    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${apiBase}/rides/request`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          pickup_location: newRide.pickup,
          destination: newRide.destination
        })
      })

      if (res.ok) {
        setNewRide({ pickup: '', destination: '' })
        await fetchRides()
        setError('')
      } else {
        const error = await res.json()
        setError(error.detail || 'Failed to request ride')
      }
    } catch (err) {
      setError('Failed to request ride')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRides()
  }, [])

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={titleStyle}>Customer Dashboard</h1>
        <p style={subtitleStyle}>Request rides and track your journey</p>
      </div>

      {error && (
        <div style={{
          ...cardStyle,
          backgroundColor: '#f8d7da',
          borderColor: '#f5c6cb',
          color: '#721c24'
        }}>
          {error}
        </div>
      )}

      {/* Request New Ride */}
      <div style={cardStyle}>
        <h3 style={{ marginBottom: '20px', fontSize: '20px', fontWeight: '600' }}>
          Request a New Ride
        </h3>
        
        <input
          type="text"
          placeholder="Pickup Location"
          value={newRide.pickup}
          onChange={(e) => setNewRide({ ...newRide, pickup: e.target.value })}
          style={inputStyle}
          disabled={loading}
        />

        <input
          type="text"
          placeholder="Destination"
          value={newRide.destination}
          onChange={(e) => setNewRide({ ...newRide, destination: e.target.value })}
          style={inputStyle}
          disabled={loading}
        />

        <button 
          onClick={requestRide}
          disabled={loading}
          style={buttonStyle}
        >
          {loading ? 'Requesting...' : 'Request Ride'}
        </button>
      </div>

      {/* My Rides */}
      <div style={cardStyle}>
        <h3 style={{ marginBottom: '20px', fontSize: '20px', fontWeight: '600' }}>
          My Rides
        </h3>

        {loading && <p>Loading rides...</p>}

        {rides.length === 0 && !loading ? (
          <p style={{ color: '#6c757d', textAlign: 'center', padding: '20px' }}>
            No rides found. Request your first ride above!
          </p>
        ) : (
          <div style={{ display: 'grid', gap: '16px' }}>
            {rides.map(ride => (
              <div key={ride.id} style={{
                padding: '16px',
                border: '1px solid #e1e5e9',
                borderRadius: '6px',
                backgroundColor: '#f8f9fa'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: '500', marginBottom: '8px' }}>
                      Ride #{ride.id}
                    </div>
                    <div style={{ fontSize: '14px', color: '#6c757d', marginBottom: '4px' }}>
                      📍 From: {ride.pickup_location}
                    </div>
                    <div style={{ fontSize: '14px', color: '#6c757d', marginBottom: '4px' }}>
                      🎯 To: {ride.destination}
                    </div>
                    {ride.driver_id && (
                      <div style={{ fontSize: '14px', color: '#6c757d', marginBottom: '4px' }}>
                        🚗 Driver: ID {ride.driver_id}
                      </div>
                    )}
                  </div>
                  <span style={{
                    padding: '4px 12px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    fontWeight: '500',
                    backgroundColor: 
                      ride.status === 'requested' ? '#fff3cd' :
                      ride.status === 'accepted' ? '#d1ecf1' :
                      ride.status === 'completed' ? '#d4edda' : '#f8d7da',
                    color:
                      ride.status === 'requested' ? '#856404' :
                      ride.status === 'accepted' ? '#0c5460' :
                      ride.status === 'completed' ? '#155724' : '#721c24'
                  }}>
                    {ride.status.charAt(0).toUpperCase() + ride.status.slice(1)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}