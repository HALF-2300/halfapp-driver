import React, { useState } from 'react'

export default function AdminCodeGenerator({ apiBase }) {
  const [email, setEmail] = useState('')
  const [generatedCode, setGeneratedCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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
    maxWidth: '500px',
    width: '100%',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    border: '1px solid #e1e5e9',
    textAlign: 'center'
  }

  const inputStyle = {
    width: '100%',
    padding: '12px',
    margin: '8px 0',
    border: '1px solid #ced4da',
    borderRadius: '6px',
    fontSize: '16px',
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

  const codeDisplayStyle = {
    backgroundColor: '#e9ecef',
    padding: '20px',
    borderRadius: '6px',
    margin: '20px 0',
    fontSize: '24px',
    fontWeight: 'bold',
    fontFamily: 'monospace',
    letterSpacing: '2px'
  }

  const generateCode = async () => {
    if (!email) {
      setError('Please enter an email address')
      return
    }

    setLoading(true)
    setError('')
    setGeneratedCode('')

    try {
      const res = await fetch(`${apiBase}/admin-access/generate-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      })

      const data = await res.json()

      if (res.ok) {
        setGeneratedCode(data.access_code)
        setError('')
      } else {
        const errorDetail = data.detail
        if (typeof errorDetail === 'object') {
          setError(errorDetail.message || 'Failed to generate code')
        } else {
          setError(errorDetail || 'Failed to generate code')
        }
      }
    } catch (err) {
      setError('Failed to generate code. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(generatedCode)
      .then(() => alert('Code copied to clipboard!'))
      .catch(() => alert('Failed to copy code'))
  }

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h1 style={{ fontSize: '28px', fontWeight: '600', marginBottom: '16px' }}>
          Admin Access Code Generator
        </h1>
        <p style={{ color: '#6c757d', marginBottom: '32px' }}>
          Generate a secure access code for admin registration
        </p>

        {error && (
          <div style={{
            backgroundColor: '#f8d7da',
            border: '1px solid #f5c6cb',
            color: '#721c24',
            padding: '12px',
            borderRadius: '6px',
            marginBottom: '16px'
          }}>
            {error}
          </div>
        )}

        <input
          type="email"
          placeholder="Enter email for admin account"
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
          <div>
            <h3 style={{ marginTop: '24px', marginBottom: '16px' }}>
              Access Code Generated!
            </h3>
            <div style={codeDisplayStyle}>
              {generatedCode}
            </div>
            <button 
              onClick={copyToClipboard}
              style={{
                ...buttonStyle,
                backgroundColor: '#28a745',
                marginTop: '0'
              }}
            >
              Copy to Clipboard
            </button>
            <p style={{ fontSize: '14px', color: '#6c757d', marginTop: '16px' }}>
              Share this code with the person who needs admin access. 
              They can use it at the admin registration page.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}