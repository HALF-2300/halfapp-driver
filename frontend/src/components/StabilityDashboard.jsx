import React, { useState, useEffect } from 'react'
import stabilityTracker from '../utils/stabilityTracker'

export default function StabilityDashboard() {
  const [healthStatus, setHealthStatus] = useState(null)
  const [sessionSummary, setSummary] = useState(null)
  const [refreshInterval, setRefreshInterval] = useState(null)

  const containerStyle = {
    padding: '20px',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  }

  const cardStyle = {
    backgroundColor: 'white',
    border: '1px solid #e1e5e9',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
  }

  const statusBadgeStyle = (status) => ({
    display: 'inline-block',
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: '600',
    textTransform: 'uppercase',
    backgroundColor: status === 'healthy' ? '#d4edda' : '#f8d7da',
    color: status === 'healthy' ? '#155724' : '#721c24'
  })

  const metricStyle = {
    display: 'inline-block',
    margin: '8px 16px 8px 0',
    padding: '8px 12px',
    backgroundColor: '#f8f9fa',
    border: '1px solid #e9ecef',
    borderRadius: '4px',
    fontSize: '14px'
  }

  const refreshData = () => {
    setHealthStatus(stabilityTracker.getHealthStatus())
    setSummary(stabilityTracker.getSessionSummary())
  }

  useEffect(() => {
    refreshData()
    
    // Set up auto-refresh every 5 seconds
    const interval = setInterval(refreshData, 5000)
    setRefreshInterval(interval)
    
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [])

  const exportData = () => {
    const data = stabilityTracker.exportData()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `stability-report-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!healthStatus || !sessionSummary) {
    return <div style={containerStyle}>Loading stability data...</div>
  }

  return (
    <div style={containerStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ margin: 0 }}>Application Stability Dashboard</h2>
        <button 
          onClick={exportData}
          style={{
            padding: '8px 16px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Export Report
        </button>
      </div>

      {/* Health Status */}
      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>System Health</h3>
        <div style={{ marginBottom: '16px' }}>
          <span style={statusBadgeStyle(healthStatus.status)}>
            {healthStatus.status}
          </span>
        </div>
        <div>
          <span style={metricStyle}>Uptime: {sessionSummary.uptime}</span>
          <span style={metricStyle}>Error Rate: {(healthStatus.errorRate * 100).toFixed(1)}%</span>
          <span style={metricStyle}>Total Errors: {healthStatus.totalErrors}</span>
          <span style={metricStyle}>Total Events: {sessionSummary.totalEvents}</span>
        </div>
      </div>

      {/* Session Summary */}
      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>Session Summary</h3>
        <div>
          <p><strong>Session ID:</strong> {sessionSummary.sessionId}</p>
          <p><strong>Duration:</strong> {sessionSummary.uptime}</p>
          <p><strong>Total Events:</strong> {sessionSummary.totalEvents}</p>
          <p><strong>Total Errors:</strong> {sessionSummary.totalErrors}</p>
        </div>
      </div>

      {/* API Metrics */}
      {Object.keys(sessionSummary.apiMetrics).length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0 }}>API Performance</h3>
          {Object.entries(sessionSummary.apiMetrics).map(([endpoint, metrics]) => (
            <div key={endpoint} style={{ marginBottom: '12px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
              <div style={{ fontWeight: '600', marginBottom: '8px' }}>{endpoint}</div>
              <div>
                <span style={metricStyle}>Calls: {metrics.calls || 0}</span>
                <span style={metricStyle}>
                  Avg Duration: {metrics.calls ? (metrics.totalDuration / metrics.calls).toFixed(0) : 0}ms
                </span>
                <span style={metricStyle}>Errors: {metrics.errors || 0}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recent Errors */}
      {sessionSummary.recentErrors && sessionSummary.recentErrors.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0 }}>Recent Errors</h3>
          {sessionSummary.recentErrors.map((error, index) => (
            <div key={index} style={{ 
              marginBottom: '12px', 
              padding: '12px', 
              backgroundColor: '#fff5f5', 
              border: '1px solid #fed7d7',
              borderRadius: '4px' 
            }}>
              <div style={{ fontWeight: '600', color: '#c53030' }}>{error.type}</div>
              <div style={{ fontSize: '14px', marginTop: '4px' }}>{error.message}</div>
              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                {new Date(error.timestamp).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Recent Events */}
      {sessionSummary.recentEvents && sessionSummary.recentEvents.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ marginTop: 0 }}>Recent Events</h3>
          <div style={{ fontSize: '14px' }}>
            {sessionSummary.recentEvents.map((event, index) => (
              <div key={index} style={{ 
                padding: '8px', 
                marginBottom: '4px',
                backgroundColor: '#f8f9fa',
                borderRadius: '3px',
                display: 'flex',
                justifyContent: 'space-between'
              }}>
                <span>{event.type}</span>
                <span style={{ color: '#666' }}>
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ fontSize: '12px', color: '#666', textAlign: 'center', marginTop: '20px' }}>
        Auto-refreshes every 5 seconds • Session started {new Date(sessionSummary.sessionId.split('_')[1] * 1).toLocaleString()}
      </div>
    </div>
  )
}