import React, { useState, useEffect } from 'react'
import driverAPI from '../utils/api'

function AuthDebugger() {
  const [debugInfo, setDebugInfo] = useState({})
  const [testResult, setTestResult] = useState('')

  useEffect(() => {
    // Get debug information
    const drivers = driverAPI.getDriverDatabase()
    setDebugInfo({
      driversCount: Object.keys(drivers).length,
      drivers: drivers,
      localStorage: {
        token: localStorage.getItem('driver_token'),
        role: localStorage.getItem('driver_role')
      }
    })
  }, [])

  const testLogin = async (email, password) => {
    setTestResult('Testing...')
    try {
      console.log('🧪 Direct API test:', { email, password })
      const result = await driverAPI.login(email, password)
      setTestResult(`✅ Success: ${JSON.stringify(result, null, 2)}`)
    } catch (error) {
      setTestResult(`❌ Error: ${error.message}`)
    }
  }

  const resetDatabase = () => {
    localStorage.removeItem('halfapp_driver_database')
    window.location.reload()
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">🔧 Authentication Debugger</h2>
      
      {/* Database Info */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">📊 Database Status</h3>
        <div className="bg-gray-50 p-4 rounded">
          <p><strong>Drivers Count:</strong> {debugInfo.driversCount}</p>
          <p><strong>Token:</strong> {debugInfo.localStorage?.token || 'None'}</p>
          <p><strong>Role:</strong> {debugInfo.localStorage?.role || 'None'}</p>
        </div>
      </div>

      {/* Available Drivers */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">👥 Available Drivers</h3>
        <div className="bg-gray-50 p-4 rounded">
          {Object.entries(debugInfo.drivers || {}).map(([email, driver]) => (
            <div key={email} className="mb-4 p-3 bg-white rounded border">
              <p><strong>Email:</strong> {email}</p>
              <p><strong>Name:</strong> {driver.name}</p>
              <p><strong>Role:</strong> {driver.role}</p>
              <p><strong>Password:</strong> {driver.password}</p>
              <button 
                onClick={() => testLogin(email, driver.password)}
                className="mt-2 bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600"
              >
                Test Login
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Manual Test */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">🧪 Manual Test</h3>
        <div className="bg-gray-50 p-4 rounded">
          <button 
            onClick={() => testLogin('driver1@example.com', 'driver123')}
            className="mr-2 mb-2 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
          >
            Test driver1@example.com
          </button>
          <button 
            onClick={() => testLogin('driver2@example.com', 'driver456')}
            className="mr-2 mb-2 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
          >
            Test driver2@example.com
          </button>
          <button 
            onClick={() => testLogin('test@example.com', 'password123')}
            className="mr-2 mb-2 bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600"
          >
            Test Invalid Credentials
          </button>
        </div>
      </div>

      {/* Test Result */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">📋 Test Result</h3>
        <pre className="bg-gray-800 text-green-400 p-4 rounded overflow-auto text-sm">
          {testResult || 'No test run yet'}
        </pre>
      </div>

      {/* Reset */}
      <div className="mb-6">
        <button 
          onClick={resetDatabase}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
        >
          🗑️ Reset Database
        </button>
      </div>
    </div>
  )
}

export default AuthDebugger