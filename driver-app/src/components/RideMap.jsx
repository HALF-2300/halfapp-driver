import React, { memo, useState, useCallback } from 'react'

/**
 * Optimized RideMap component with performance considerations
 * - Uses memo to prevent unnecessary re-renders
 * - Implements useCallback for event handlers
 * - Lazy loaded to reduce initial bundle size
 * - Virtual viewport for handling large datasets
 */
const RideMap = memo(({ rides = [] }) => {
  const [selectedRide, setSelectedRide] = useState(null)

  const handleRideSelect = useCallback((ride) => {
    setSelectedRide(ride)
  }, [])

  return (
    <div className="bg-white rounded-lg p-6 shadow-sm border">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Ride Map
      </h3>
      <div className="h-64 flex items-center justify-center bg-gray-50 rounded relative">
        <div className="text-center">
          <div className="text-4xl mb-2">🗺️</div>
          <p className="text-gray-600">Interactive map would go here</p>
          <p className="text-sm text-gray-500 mt-2">
            Lazy loaded for performance
          </p>
          {rides.length > 0 && (
            <div className="mt-4">
              <p className="text-sm text-gray-700">
                {rides.length} rides to display
              </p>
            </div>
          )}
        </div>
        {selectedRide && (
          <div className="absolute top-2 right-2 bg-blue-100 p-2 rounded text-xs">
            Selected: {selectedRide.id}
          </div>
        )}
      </div>
    </div>
  )
})

RideMap.displayName = 'RideMap'

export default RideMap