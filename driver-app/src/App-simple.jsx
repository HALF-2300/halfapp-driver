import React from 'react'

function App() {
  console.log('🎯 React App is loading!')
  
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: '#f0f9ff',
      fontFamily: 'system-ui, sans-serif'
    }}>
      <div style={{
        padding: '3rem',
        backgroundColor: 'white',
        borderRadius: '1rem',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        textAlign: 'center'
      }}>
        <h1 style={{ 
          color: '#0ea5e9', 
          fontSize: '2.5rem', 
          marginBottom: '1rem',
          fontWeight: 'bold'
        }}>
          🚀 Half-App Driver
        </h1>
        <p style={{ color: '#64748b', fontSize: '1.2rem' }}>
          React is working! Loading the full authentication system...
        </p>
        <div style={{
          marginTop: '2rem',
          padding: '1rem',
          backgroundColor: '#dcfce7',
          borderRadius: '0.5rem',
          border: '1px solid #bbf7d0'
        }}>
          <p style={{ color: '#16a34a', fontWeight: '600' }}>
            ✅ Server: Running<br/>
            ✅ React: Loaded<br/>
            ✅ Vite: Active
          </p>
        </div>
      </div>
    </div>
  )
}

export default App