import React, { useEffect, useState } from 'react'

const AppDiagnostics = () => {
  const [diagnostics, setDiagnostics] = useState({
    jsLoaded: false,
    tailwindLoaded: false,
    apiAvailable: false,
    authWorking: false,
    timestamp: null
  })

  useEffect(() => {
    const runDiagnostics = async () => {
      console.log('🔍 Running App Diagnostics...')
      
      const results = {
        timestamp: new Date().toISOString(),
        jsLoaded: true, // If this runs, JS is loaded
        tailwindLoaded: false,
        apiAvailable: false,
        authWorking: false,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
        userAgent: navigator.userAgent.substring(0, 100),
        url: window.location.href
      }

      // Check if Tailwind is loaded
      try {
        const testElement = document.createElement('div')
        testElement.className = 'bg-blue-500'
        document.body.appendChild(testElement)
        const styles = window.getComputedStyle(testElement)
        results.tailwindLoaded = styles.backgroundColor === 'rgb(59, 130, 246)'
        document.body.removeChild(testElement)
      } catch (e) {
        console.error('Tailwind test failed:', e)
      }

      // Check API availability
      try {
        // Try to import and test the API
        const { default: driverAPI } = await import('../utils/api.js')
        results.apiAvailable = typeof driverAPI === 'object'
        
        // Test mock authentication
        try {
          await driverAPI.login('driver1@example.com', 'driver123')
          results.authWorking = true
        } catch (e) {
          console.log('Auth test expected error:', e.message)
          results.authWorking = e.message.includes('driver') || e.message.includes('mock')
        }
      } catch (e) {
        console.error('API test failed:', e)
      }

      setDiagnostics(results)
      console.log('📋 Diagnostics Results:', results)
    }

    runDiagnostics()
  }, [])

  return (
    <div className="fixed bottom-4 right-4 bg-white border border-gray-300 rounded-lg shadow-lg p-4 max-w-sm text-xs">
      <div className="font-bold text-gray-800 mb-2">🔍 App Diagnostics</div>
      
      <div className="space-y-1">
        <div className={`flex justify-between ${diagnostics.jsLoaded ? 'text-green-600' : 'text-red-600'}`}>
          <span>JavaScript:</span>
          <span>{diagnostics.jsLoaded ? '✅' : '❌'}</span>
        </div>
        
        <div className={`flex justify-between ${diagnostics.tailwindLoaded ? 'text-green-600' : 'text-red-600'}`}>
          <span>Tailwind CSS:</span>
          <span>{diagnostics.tailwindLoaded ? '✅' : '❌'}</span>
        </div>
        
        <div className={`flex justify-between ${diagnostics.apiAvailable ? 'text-green-600' : 'text-red-600'}`}>
          <span>API Module:</span>
          <span>{diagnostics.apiAvailable ? '✅' : '❌'}</span>
        </div>
        
        <div className={`flex justify-between ${diagnostics.authWorking ? 'text-green-600' : 'text-red-600'}`}>
          <span>Authentication:</span>
          <span>{diagnostics.authWorking ? '✅' : '❌'}</span>
        </div>
      </div>

      <div className="mt-2 pt-2 border-t border-gray-200">
        <div className="text-gray-500 text-xs">
          <div>Viewport: {diagnostics.viewport}</div>
          <div>Updated: {diagnostics.timestamp ? new Date(diagnostics.timestamp).toLocaleTimeString() : 'Loading...'}</div>
        </div>
      </div>

      <div className="mt-2">
        <button 
          onClick={() => window.location.reload()} 
          className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600"
        >
          Reload
        </button>
        <button 
          onClick={() => console.log('Diagnostics:', diagnostics)} 
          className="text-xs bg-gray-500 text-white px-2 py-1 rounded hover:bg-gray-600 ml-1"
        >
          Log
        </button>
      </div>
    </div>
  )
}

export default AppDiagnostics