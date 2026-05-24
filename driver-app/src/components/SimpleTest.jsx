import React from 'react'

// Simple test component to verify React is working
function SimpleTest() {
  return (
    <div className="min-h-screen bg-blue-50 flex items-center justify-center">
      <div className="text-center p-8 bg-white rounded-lg shadow-lg">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          🚗 Half-App Driver
        </h1>
        <p className="text-lg text-gray-600 mb-6">
          Application is running successfully!
        </p>
        <div className="space-y-2">
          <p className="text-sm text-green-600">✅ React is working</p>
          <p className="text-sm text-green-600">✅ Tailwind CSS is loaded</p>
          <p className="text-sm text-green-600">✅ Vite dev server is running</p>
        </div>
        <button 
          className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          onClick={() => alert('Button works!')}
        >
          Test Interaction
        </button>
      </div>
    </div>
  )
}

export default SimpleTest