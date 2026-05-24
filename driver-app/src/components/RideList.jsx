import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import driverAPI from '../utils/api'
import { normalizeRideForDisplay } from '../utils/rideModel.js'

const ACTIVE_TRIP_STATUSES = new Set([
  'accepted',
  'driver_arrived',
  'in_progress',
])

export default function RideList() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [availableRides, setAvailableRides] = useState([])
  const [myRides, setMyRides] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [actionNotice, setActionNotice] = useState(null)
  const [activeTab, setActiveTab] = useState('available')

  useEffect(() => {
    fetchRides()
  }, [])

  const fetchRides = async () => {
    try {
      setLoading(true)
      setError(null)
      const [availableRidesData, myRidesData] = await Promise.all([
        driverAPI.getAvailableRides(),
        driverAPI.getMyRides()
      ])

      setAvailableRides(Array.isArray(availableRidesData) ? availableRidesData : [])
      setMyRides(Array.isArray(myRidesData) ? myRidesData : [])
    } catch (err) {
      setAvailableRides([])
      setMyRides([])
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAcceptRide = async (rideId) => {
    setActionError(null)
    setActionNotice(null)
    try {
      await driverAPI.acceptRide(rideId)
      await fetchRides()
    } catch (err) {
      setActionError(err?.message || 'Failed to accept ride.')
    }
  }

  const handleCompleteRide = async (rideId) => {
    setActionError(null)
    setActionNotice(null)
    try {
      const result = await driverAPI.completeRide(rideId)
      const fare = result?.fare_earned
      setActionNotice(
        typeof fare === 'number' && Number.isFinite(fare)
          ? `Ride completed. Fare recorded: $${fare.toFixed(2)}`
          : 'Ride completed.'
      )
      await fetchRides()
    } catch (err) {
      setActionError(err?.message || 'Failed to complete ride.')
    }
  }

  const handleDeclineRide = async (rideId) => {
    setActionError(null)
    setActionNotice(null)
    try {
      await driverAPI.declineRide(rideId, {})
      setActionNotice('Ride returned to the pool.')
      await fetchRides()
    } catch (err) {
      setActionError(err?.message || 'Failed to decline ride.')
    }
  }

  const handleArrivePickup = async (rideId) => {
    setActionError(null)
    setActionNotice(null)
    try {
      await driverAPI.arrivePickup(rideId)
      setActionNotice('Arrival recorded.')
      await fetchRides()
    } catch (err) {
      setActionError(err?.message || 'Failed to record arrival.')
    }
  }

  const handleStartRide = async (rideId) => {
    setActionError(null)
    setActionNotice(null)
    try {
      await driverAPI.startRide(rideId)
      setActionNotice('Trip started.')
      await fetchRides()
    } catch (err) {
      setActionError(err?.message || 'Failed to start ride.')
    }
  }

  const RideCard = ({ ride, display, showActions = false, actionType = 'accept' }) => (
    <div className="bg-slate-900 rounded-2xl p-4 shadow-xl shadow-black/20 border border-slate-800">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center mb-2">
            <span className="mr-2 h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_16px_rgba(52,211,153,0.7)]" />
            <h3 className="font-semibold text-slate-100">{display.customerName}</h3>
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center text-sm text-slate-400">
              <span>Ride ID: #{ride.id}</span>
            </div>
            
            <div className="flex items-center">
              <span
                className={`status-badge status-${display.normalizedStatus === 'unknown' ? 'unknown' : display.normalizedStatus}`}
              >
                {display.statusLabel}
              </span>
            </div>

            <div className="flex items-center text-sm text-slate-400">
              <span>Pickup: {display.pickup}</span>
            </div>

            <div className="flex items-center text-sm text-slate-400">
              <span>Destination: {display.destination}</span>
            </div>

            <div className="flex items-center text-sm text-slate-400">
              <span>Backend fare: {display.fareLabel}</span>
            </div>
          </div>
        </div>
        
        {showActions && (
          <div className="ml-4 flex flex-col gap-2 items-end">
            {actionType === 'accept' && (
              <button
                type="button"
                onClick={() => handleAcceptRide(ride.id)}
                className="btn btn-success btn-sm"
              >
                Accept Ride
              </button>
            )}
            {actionType === 'active' && ride.status === 'accepted' && (
              <>
                <button
                  type="button"
                  onClick={() => handleArrivePickup(ride.id)}
                  className="btn btn-primary btn-sm"
                >
                  Arrived at pickup
                </button>
                <button
                  type="button"
                  onClick={() => handleDeclineRide(ride.id)}
                  className="btn btn-secondary btn-sm"
                >
                  Decline (return to pool)
                </button>
              </>
            )}
            {actionType === 'active' &&
              ride.status === 'driver_arrived' && (
                <button
                  type="button"
                  onClick={() => handleStartRide(ride.id)}
                  className="btn btn-primary btn-sm"
                >
                  Start trip
                </button>
              )}
            {actionType === 'active' && ride.status === 'in_progress' && (
              <button
                type="button"
                onClick={() => handleCompleteRide(ride.id)}
                className="btn btn-primary btn-sm"
              >
                Complete ride
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mx-auto"></div>
          <p className="mt-4 text-slate-400">Loading backend rides...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <div className="bg-slate-950 border-b border-slate-800 shadow-2xl shadow-black/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <p className="text-[10px] uppercase tracking-[0.24em] text-blue-300 font-semibold">
                Driver Marketplace Core
              </p>
              <h1 className="text-xl font-bold text-slate-100">Backend Rides</h1>
              <p className="text-sm text-slate-400">Manage backend marketplace requests and lifecycle state</p>
            </div>
            <div className="flex items-center space-x-4">
              <button
                type="button"
                onClick={() => navigate('/#/')}
                className="btn btn-secondary btn-sm"
              >
                Cockpit
              </button>
              <button
                onClick={fetchRides}
                className="btn btn-secondary btn-sm"
              >
                Refresh
              </button>
              <button
                onClick={logout}
                className="btn btn-secondary btn-sm"
              >
                Logout
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('available')}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'available'
                  ? 'border-blue-400 text-blue-300'
                  : 'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-700'
              }`}
            >
              Available Rides ({availableRides.length})
            </button>
            <button
              onClick={() => setActiveTab('active')}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'active'
                  ? 'border-blue-400 text-blue-300'
                  : 'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-700'
              }`}
            >
              My Active Rides ({myRides.length})
            </button>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 bg-rose-950/40 border border-rose-800 rounded-xl p-4">
            <div className="flex">
              <div>
                <h3 className="text-sm font-medium text-rose-200">Backend error</h3>
                <p className="text-sm text-rose-300 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {actionError && (
          <div className="mb-6 bg-rose-950/40 border border-rose-800 rounded-xl p-4" data-testid="ride-list-action-error">
            <p className="text-sm font-medium text-rose-200">Backend action failed</p>
            <p className="text-sm text-rose-300 mt-1">{actionError}</p>
            <button type="button" className="mt-2 text-sm underline text-rose-100" onClick={() => setActionError(null)}>
              Dismiss
            </button>
          </div>
        )}

        {actionNotice && (
          <div className="mb-6 bg-emerald-950/40 border border-emerald-800 rounded-xl p-4" data-testid="ride-list-action-notice">
            <p className="text-sm text-emerald-200">{actionNotice}</p>
            <button type="button" className="mt-2 text-sm underline text-emerald-100" onClick={() => setActionNotice(null)}>
              Dismiss
            </button>
          </div>
        )}

        {/* Available Rides Tab */}
        {activeTab === 'available' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-slate-100">
                Backend Marketplace Requests
              </h2>
              <p className="text-sm text-slate-400">
                {availableRides.length} backend rides visible to this driver
              </p>
            </div>

            {availableRides.length === 0 ? (
              <div className="bg-slate-900 rounded-2xl p-12 text-center border border-slate-800">
                <h3 className="text-xl font-medium text-slate-100 mb-2">
                  No Backend Rides Visible
                </h3>
                <p className="text-slate-400 mb-6">
                  There are currently no backend marketplace requests visible to this driver.
                </p>
                <button
                  onClick={fetchRides}
                  className="btn btn-primary"
                >
                  Refresh Backend Rides
                </button>
              </div>
            ) : (
              <div className="grid gap-4">
                {availableRides.map(ride => (
                  <RideCard
                    key={ride.id}
                    ride={ride}
                    display={normalizeRideForDisplay(ride)}
                    showActions={true}
                    actionType="accept"
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* My Active Rides Tab */}
        {activeTab === 'active' && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-slate-100">
                My Active Backend Rides
              </h2>
              <p className="text-sm text-slate-400">
                {myRides.length} rides in progress
              </p>
            </div>

            {myRides.length === 0 ? (
              <div className="bg-slate-900 rounded-2xl p-12 text-center border border-slate-800">
                <h3 className="text-xl font-medium text-slate-100 mb-2">
                  No Active Rides
                </h3>
                <p className="text-slate-400 mb-6">
                  This driver has no active backend lifecycle ride at the moment.
                </p>
                <button
                  onClick={() => setActiveTab('available')}
                  className="btn btn-primary"
                >
                  Browse Available Rides
                </button>
              </div>
            ) : (
              <div className="grid gap-4">
                {myRides.map(ride => (
                  <RideCard
                    key={ride.id}
                    ride={ride}
                    display={normalizeRideForDisplay(ride)}
                    showActions={ACTIVE_TRIP_STATUSES.has(ride.status)}
                    actionType="active"
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Quick Stats */}
        <div className="mt-8 bg-slate-900 rounded-2xl p-6 border border-slate-800">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">
            Marketplace Snapshot
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{availableRides.length}</p>
              <p className="text-sm text-slate-400">Available</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">{myRides.length}</p>
              <p className="text-sm text-slate-400">Active</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-600">
                {myRides.filter(ride => ACTIVE_TRIP_STATUSES.has(ride.status)).length}
              </p>
              <p className="text-sm text-slate-400">Active trip</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-indigo-600">
                {myRides.filter(ride => ride.status === 'completed').length}
              </p>
              <p className="text-sm text-slate-400">Completed</p>
            </div>
          </div>
        </div>

        {/* Driver Tips */}
        <div className="mt-6 bg-slate-900 rounded-2xl p-6 border border-slate-800">
          <h3 className="text-lg font-semibold text-slate-100 mb-4">
            Showcase Notes
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-start">
              <span className="text-2xl mr-3">✅</span>
              <div>
                <h4 className="font-medium text-slate-100">Backend visibility</h4>
                <p className="text-sm text-slate-400">
                  Available rides are retrieved from backend marketplace state.
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <span className="text-2xl mr-3">🚗</span>
              <div>
                <h4 className="font-medium text-slate-100">Canonical lifecycle</h4>
                <p className="text-sm text-slate-400">
                  Active rides move through backend lifecycle transitions.
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <span className="text-2xl mr-3">💬</span>
              <div>
                <h4 className="font-medium text-slate-100">No fake claims</h4>
                <p className="text-sm text-slate-400">
                  No live ETA, nearest-driver, or payment processing is claimed.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}