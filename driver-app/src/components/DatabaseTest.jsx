import React, { useState } from 'react'
import driverAPI from '../utils/api'

export default function DatabaseTest() {
  const [testResults, setTestResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [testData, setTestData] = useState({
    driver_id: 'test-driver-123',
    action: 'test_action',
    timestamp: new Date().toISOString(),
    location: { lat: 40.7128, lng: -74.0060 },
    message: 'Test message from driver app'
  })

  // Inline styles for fallback
  const styles = {
    container: {
      minHeight: '100vh',
      backgroundColor: '#f9fafb',
      padding: '1.5rem'
    },
    card: {
      backgroundColor: 'white',
      borderRadius: '12px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      border: '1px solid #e5e7eb',
      padding: '1.5rem',
      maxWidth: '64rem',
      margin: '0 auto'
    },
    button: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '12px',
      padding: '0.75rem 1.5rem',
      fontSize: '0.875rem',
      fontWeight: '600',
      border: 'none',
      cursor: 'pointer',
      transition: 'all 0.2s',
      backgroundColor: '#2563eb',
      color: 'white'
    },
    input: {
      width: '100%',
      borderRadius: '12px',
      border: '1px solid #e5e7eb',
      padding: '0.75rem 1rem',
      fontSize: '0.875rem'
    },
    successBox: {
      backgroundColor: '#dcfce7',
      border: '1px solid #bbf7d0',
      borderRadius: '12px',
      padding: '1rem'
    },
    errorBox: {
      backgroundColor: '#fecaca',
      border: '1px solid #fca5a5',
      borderRadius: '12px',
      padding: '1rem'
    }
  }

  const runDatabaseTest = async () => {
    setLoading(true)
    try {
      console.log('Testing database connection...')
      const dbTest = await driverAPI.testDatabaseConnection()
      
      console.log('Sending test data to database...')
      const dataTest = await driverAPI.sendTestData(testData)
      
      console.log('Fetching test logs...')
      const logsTest = await driverAPI.getTestLogs()
      
      setTestResults({
        database_connection: dbTest,
        data_insertion: dataTest,
        logs_retrieval: logsTest
      })
      
      console.log('All tests completed successfully!')
    } catch (error) {
      console.error('Test failed:', error)
      setTestResults({
        error: error.message
      })
    } finally {
      setLoading(false)
    }
  }

  const updateTestData = (field, value) => {
    setTestData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6" style={styles.container}>
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6" style={styles.card}>
          <h1 className="text-2xl font-bold text-gray-900 mb-6">
            🔧 Database Connectivity Test
          </h1>
          
          <div className="space-y-6">
            {/* Test Configuration */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Test Configuration
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Driver ID
                  </label>
                  <input
                    type="text"
                    value={testData.driver_id}
                    onChange={(e) => updateTestData('driver_id', e.target.value)}
                    className="input-field"
                    style={styles.input}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Action
                  </label>
                  <input
                    type="text"
                    value={testData.action}
                    onChange={(e) => updateTestData('action', e.target.value)}
                    className="input-field"
                    style={styles.input}
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Test Message
                  </label>
                  <input
                    type="text"
                    value={testData.message}
                    onChange={(e) => updateTestData('message', e.target.value)}
                    className="input-field"
                    style={styles.input}
                  />
                </div>
              </div>
            </div>

            {/* Run Test Button */}
            <div className="flex justify-center">
              <button
                onClick={runDatabaseTest}
                disabled={loading}
                className={`btn btn-primary ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                style={styles.button}
              >
                {loading ? '🔄 Running Tests...' : '🚀 Run Database Test'}
              </button>
            </div>

            {/* Test Results */}
            {testResults && (
              <div className="mt-8">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  📊 Test Results
                </h2>
                
                {testResults.error ? (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                    <div className="flex">
                      <span className="text-red-400 mr-3 text-xl">❌</span>
                      <div>
                        <h3 className="text-sm font-medium text-red-800">Test Failed</h3>
                        <p className="text-sm text-red-700 mt-1">{testResults.error}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Database Connection Test */}
                    <div className={`rounded-xl p-4 border ${
                      testResults.database_connection?.database_connected 
                        ? 'bg-green-50 border-green-200' 
                        : 'bg-red-50 border-red-200'
                    }`}>
                      <div className="flex items-start">
                        <span className="text-xl mr-3">
                          {testResults.database_connection?.database_connected ? '✅' : '❌'}
                        </span>
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900">Database Connection</h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {testResults.database_connection?.message}
                          </p>
                          {testResults.database_connection?.current_time && (
                            <p className="text-xs text-gray-500 mt-1">
                              Time: {testResults.database_connection.current_time}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Data Insertion Test */}
                    <div className={`rounded-xl p-4 border ${
                      testResults.data_insertion?.status === 'success' 
                        ? 'bg-green-50 border-green-200' 
                        : 'bg-red-50 border-red-200'
                    }`}>
                      <div className="flex items-start">
                        <span className="text-xl mr-3">
                          {testResults.data_insertion?.status === 'success' ? '✅' : '❌'}
                        </span>
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900">Data Insertion</h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {testResults.data_insertion?.message}
                          </p>
                          {testResults.data_insertion?.timestamp && (
                            <p className="text-xs text-gray-500 mt-1">
                              Timestamp: {testResults.data_insertion.timestamp}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Logs Retrieval Test */}
                    <div className={`rounded-xl p-4 border ${
                      testResults.logs_retrieval?.status === 'success' 
                        ? 'bg-green-50 border-green-200' 
                        : 'bg-red-50 border-red-200'
                    }`}>
                      <div className="flex items-start">
                        <span className="text-xl mr-3">
                          {testResults.logs_retrieval?.status === 'success' ? '✅' : '❌'}
                        </span>
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-900">Data Retrieval</h3>
                          <p className="text-sm text-gray-600 mt-1">
                            Retrieved {testResults.logs_retrieval?.logs_count || 0} log entries
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Recent Logs */}
                    {testResults.logs_retrieval?.logs && testResults.logs_retrieval.logs.length > 0 && (
                      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                        <h3 className="font-medium text-gray-900 mb-3">📋 Recent Test Logs</h3>
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                          {testResults.logs_retrieval.logs.map((log) => (
                            <div key={log.id} className="bg-white rounded-lg p-3 text-sm">
                              <div className="flex justify-between items-start mb-1">
                                <span className="font-medium text-gray-900">ID: {log.id}</span>
                                <span className="text-gray-500">{log.timestamp}</span>
                              </div>
                              <div className="text-gray-600">
                                <strong>Driver:</strong> {log.data.driver_id} | 
                                <strong> Action:</strong> {log.data.action} |
                                <strong> Source:</strong> {log.source}
                              </div>
                              <div className="text-gray-500 text-xs mt-1">
                                {log.data.message}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Instructions */}
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mt-6">
              <h3 className="font-medium text-blue-900 mb-2">💡 Instructions</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• This tool tests database connectivity from the driver app</li>
                <li>• It verifies that data can be sent from frontend to backend to database</li>
                <li>• Green checkmarks indicate successful operations</li>
                <li>• Check browser console for detailed logs</li>
                <li>• Use this to verify the complete data flow is working</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}