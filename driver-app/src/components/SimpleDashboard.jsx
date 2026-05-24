import React from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import BottomNavigation from './BottomNavigation'

// Simple Dashboard for testing
function SimpleDashboard() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm px-4 py-4">
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-900">
            Dashboard
          </h1>
          <button
            onClick={logout}
            className="text-red-600 text-sm font-medium"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="bg-white rounded-lg p-6 shadow-sm mb-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Welcome, {user?.name || 'Driver'}!
          </h2>
          
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h3 className="font-semibold text-blue-900">Total Rides</h3>
              <p className="text-2xl font-bold text-blue-600">0</p>
            </div>
            
            <div className="bg-green-50 p-4 rounded-lg">
              <h3 className="font-semibold text-green-900">Earnings</h3>
              <p className="text-2xl font-bold text-green-600">$0</p>
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg text-center">
            <p className="text-gray-600 mb-2">No rides available</p>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Refresh
            </button>
          </div>
        </div>
      </div>

      <BottomNavigation />
    </div>
  )
}

export default SimpleDashboard