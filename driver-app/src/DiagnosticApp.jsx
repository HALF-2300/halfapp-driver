import React from 'react'

// Simple diagnostic component to test if React is working
function DiagnosticApp() {
  const [count, setCount] = React.useState(0)
  
  React.useEffect(() => {
    console.log('✅ React is rendering successfully!')
    console.log('✅ Vite dev server is working')
    console.log('✅ JavaScript is executing')
  }, [])

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
        padding: '2rem',
        backgroundColor: 'white',
        borderRadius: '1rem',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        textAlign: 'center',
        maxWidth: '400px'
      }}>
        <h1 style={{ color: '#1e40af', marginBottom: '1rem' }}>
          🚗 Half-App Driver
        </h1>
        <p style={{ color: '#374151', marginBottom: '1.5rem' }}>
          Diagnostic Mode - Testing Components
        </p>
        
        <div style={{ marginBottom: '1.5rem' }}>
          <p style={{ color: '#059669', fontSize: '0.875rem', margin: '0.25rem 0' }}>
            ✅ React Hook System Working
          </p>
          <p style={{ color: '#059669', fontSize: '0.875rem', margin: '0.25rem 0' }}>
            ✅ Component Rendering Active
          </p>
          <p style={{ color: '#059669', fontSize: '0.875rem', margin: '0.25rem 0' }}>
            ✅ Event Handling Functional
          </p>
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <p style={{ color: '#374151', marginBottom: '0.5rem' }}>
            Interactive Test Counter: <strong>{count}</strong>
          </p>
          <button 
            onClick={() => setCount(c => c + 1)}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            Click Me (+1)
          </button>
        </div>

        <p style={{ color: '#6b7280', fontSize: '0.75rem' }}>
          If you can see this and the button works, React is functioning properly.
          <br />
          Check browser console for additional diagnostic information.
        </p>
      </div>
    </div>
  )
}

export default DiagnosticApp