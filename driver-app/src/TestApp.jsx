import React from 'react'

function TestApp() {
  return (
    <div className="min-h-screen bg-blue-50 flex items-center justify-center">
      <div className="text-center p-8 bg-white rounded-lg shadow-lg max-w-md">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          🚗 Half-App Driver
        </h1>
        <p className="text-lg text-gray-600 mb-6">
          Test Mode - React is Working!
        </p>
        <div className="space-y-2 text-sm">
          <p className="text-green-600">✅ React rendering successfully</p>
          <p className="text-green-600">✅ Tailwind CSS loaded</p>
          <p className="text-green-600">✅ Vite dev server running</p>
        </div>
        <button 
          className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          onClick={() => {
            alert('Button works! React is functioning properly.')
          }}
        >
          Test Button
        </button>
      </div>
    </div>
  )
}

export default TestApp