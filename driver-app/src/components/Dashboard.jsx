import React, { useState, useEffect, useCallback, useMemo, memo, useRef } from 'react'
import { useAuth } from '../hooks/useAuth.jsx'
import driverAPI, { ALLOW_OFFLINE_MOCK } from '../utils/api'
import BottomNavigation from './BottomNavigation'
import { normalizeRideForDisplay, NA } from '../utils/rideModel.js'

function parseFareNumber(ride) {
  if (ride == null) return 0
  if (ride.fare_amount != null && ride.fare_amount !== '') {
    const n = Number(ride.fare_amount)
    return Number.isFinite(n) ? n : 0
  }
  return 0
}

function Dashboard() {
  const { user, logout } = useAuth()
  const [stats, setStats] = useState(null)
  const [availableRides, setAvailableRides] = useState([])
  const [myRides, setMyRides] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [acceptError, setAcceptError] = useState(null)
  const hasInitialized = useRef(false)

  const fetchDashboardData = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const [availableRidesData, myRidesData, statisticsData] = await Promise.all([
        driverAPI.getAvailableRides(),
        driverAPI.getMyRides(),
        driverAPI.getStatistics().catch(() => ({ performance_stats: {} })),
      ])

      setAvailableRides(Array.isArray(availableRidesData) ? availableRidesData : [])
      setMyRides(Array.isArray(myRidesData) ? myRidesData : [])
      setStats(statisticsData?.performance_stats || {})
    } catch (err) {
      console.error('Dashboard fetch failed:', err)
      setAvailableRides([])
      setMyRides([])
      setStats({})
      setLoadError(
        err?.message ||
          'Could not load dashboard data. Check your connection and API (VITE_API_BASE).'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!hasInitialized.current) {
      hasInitialized.current = true
      fetchDashboardData()
    }
  }, [fetchDashboardData])

  const handleAcceptRide = useCallback(
    async (rideId) => {
      setAcceptError(null)
      try {
        await driverAPI.acceptRide(rideId)
        await fetchDashboardData()
      } catch (err) {
        const msg = err?.message || 'Could not accept this ride.'
        setAcceptError(msg)
      }
    },
    [fetchDashboardData]
  )

  const memoizedStats = useMemo(() => {
    const completedRides = myRides.filter((ride) => ride.status === 'completed')
    const todays = myRides.filter((ride) => {
      if (!ride.created_at) return false
      const d = new Date(ride.created_at)
      return !Number.isNaN(d.getTime()) && d.toDateString() === new Date().toDateString()
    })
    const todaysEarnings = todays.reduce((t, ride) => t + parseFareNumber(ride), 0)
    const totalDistance = completedRides.reduce((t, ride) => {
      const km = ride.distance_km != null ? Number(ride.distance_km) : NaN
      return t + (Number.isFinite(km) ? km : 0)
    }, 0)

    return {
      completedRides: completedRides.length,
      todaysEarnings: todaysEarnings.toFixed(0),
      totalDistance: totalDistance > 0 ? `${totalDistance.toFixed(1)} km` : NA,
      averageRating: stats?.rating ?? stats?.average_rating ?? NA,
      totalRides: stats?.total_rides_completed ?? completedRides.length,
    }
  }, [myRides, stats])

  const StatCard = memo(({ title, value, icon, bgColor = 'bg-blue-500/10' }) => (
    <div className="bg-slate-900 rounded-2xl p-4 shadow-xl shadow-black/20 border border-slate-800">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400 mb-2">{title}</p>
          <p className="text-xl font-bold text-slate-100">{value !== undefined && value !== null ? value : NA}</p>
        </div>
        <div className={`w-10 h-10 ${bgColor} rounded-full flex items-center justify-center`}>
          <span className="text-sm">{icon}</span>
        </div>
      </div>
    </div>
  ))

  const RideCard = memo(({ ride, display, onAccept, showAcceptButton = false }) => (
    <div className="bg-slate-900 rounded-2xl p-4 shadow-xl shadow-black/20 border border-slate-800 mb-4">
      <div className="flex justify-between items-start gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center mb-3">
            <div className="w-10 h-10 bg-blue-500/15 rounded-full flex items-center justify-center mr-3 flex-shrink-0 ring-1 ring-blue-400/20">
              <svg className="w-5 h-5 text-blue-300" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-slate-100 truncate">{display.customerName}</h3>
              <p className="text-xs text-slate-500">Ride #{ride.id}</p>
            </div>
          </div>

          <div className="space-y-1 text-xs text-slate-400 mb-2">
            <p>
              <span className="font-medium text-slate-300">Pickup:</span> {display.pickup}
            </p>
            <p>
              <span className="font-medium text-slate-300">Destination:</span> {display.destination}
            </p>
            <p>
              <span className="font-medium text-slate-300">Backend fare:</span> {display.fareLabel} ·{' '}
              <span className="font-medium text-slate-300">Stored distance:</span> {display.distanceLabel}
            </p>
          </div>

          <div className="flex items-center">
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                display.normalizedStatus === 'requested'
                  ? 'bg-emerald-500/15 text-emerald-300'
                  : display.normalizedStatus === 'accepted' ||
                      display.normalizedStatus === 'driver_arrived'
                    ? 'bg-blue-500/15 text-blue-300'
                    : display.normalizedStatus === 'in_progress'
                      ? 'bg-indigo-500/15 text-indigo-300'
                      : display.normalizedStatus === 'completed'
                        ? 'bg-emerald-500/15 text-emerald-300'
                        : 'bg-slate-700 text-slate-300'
              }`}
            >
              {display.statusLabel}
            </span>
          </div>
        </div>

        {showAcceptButton && (
          <button
            type="button"
            onClick={() => onAccept(ride.id)}
            className="px-4 py-2 bg-emerald-500 text-slate-950 rounded-xl font-semibold text-sm hover:bg-emerald-400 transition-colors flex-shrink-0"
          >
            Accept
          </button>
        )}
      </div>
    </div>
  ))

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 pb-20">
      <div className="bg-slate-950/95 border-b border-slate-800 shadow-2xl shadow-black/20">
        <div className="px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <p className="text-[10px] uppercase tracking-[0.24em] text-blue-300 font-semibold">
                Driver Marketplace Core
              </p>
              <h1 className="text-xl font-bold text-slate-100">Welcome, {user?.name?.split(' ')[0] || 'Driver'}</h1>
              <p className="text-sm text-slate-400">Backend-owned rides, lifecycle, and earnings evidence</p>
            </div>
            <button
              onClick={logout}
              className="p-2 text-slate-400 hover:text-slate-200 flex items-center"
              aria-label="Logout"
              data-testid="logout-btn"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
              <span className="ml-2">Logout</span>
            </button>
          </div>
        </div>
      </div>

      <div className="px-6 py-6">
        {loadError && (
          <div
            data-testid="dashboard-load-error"
            className="mb-6 bg-rose-950/40 border border-rose-800 rounded-2xl p-4 space-y-3"
          >
            <p className="text-rose-200 text-sm font-medium">Could not load backend rides</p>
            <p className="text-rose-300 text-sm">{loadError}</p>
            <button
              type="button"
              onClick={fetchDashboardData}
              className="text-sm font-semibold text-rose-100 underline"
            >
              Retry
            </button>
          </div>
        )}

        {acceptError && (
          <div
            data-testid="accept-ride-error"
            className="mb-6 bg-rose-950/40 border border-rose-800 rounded-2xl p-4 space-y-2"
          >
            <p className="text-rose-200 text-sm font-medium">Accept ride failed</p>
            <p className="text-rose-300 text-sm">{acceptError}</p>
            <button type="button" onClick={() => setAcceptError(null)} className="text-sm text-rose-100 underline">
              Dismiss
            </button>
          </div>
        )}

        {!ALLOW_OFFLINE_MOCK && loading && (
          <p className="text-xs text-slate-500 mb-4" data-testid="dashboard-loading">
            Loading dashboard…
          </p>
        )}

        <div
          className="rounded-2xl p-6 mb-6 shadow-2xl shadow-black/30 border border-blue-400/20"
          style={{ background: 'linear-gradient(135deg, #0f172a 0%, #0b3b77 100%)' }}
        >
          <div className="flex items-center justify-between mb-4">
            <p className="text-blue-100 text-sm font-medium">Today&apos;s earnings (from your trips)</p>
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" />
                <path
                  fillRule="evenodd"
                  d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </div>
          <div className="mb-2">
            <p className="text-4xl font-bold text-white mb-1">${memoizedStats.todaysEarnings}</p>
          </div>
          <p className="text-blue-100 text-xs">Based on completed backend rides with a recorded fare and timestamp for today.</p>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <StatCard title="Completed rides" value={memoizedStats.completedRides} icon="OK" bgColor="bg-emerald-500/10 text-emerald-300" />
          <StatCard title="Stored distance" value={memoizedStats.totalDistance} icon="KM" bgColor="bg-blue-500/10 text-blue-300" />
        </div>

        <div className="mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-slate-100">Backend marketplace pool</h2>
            <button type="button" onClick={fetchDashboardData} className="text-blue-300 text-sm font-medium">
              Refresh
            </button>
          </div>

          {availableRides.length === 0 ? (
            <div className="bg-slate-900 rounded-2xl p-8 text-center border border-slate-800">
              <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-slate-500" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-slate-100 mb-2">No rides in the backend pool</h3>
              <p className="text-slate-400 text-sm">
                There are no open requests right now, or the API could not be reached.
              </p>
            </div>
          ) : (
            <div>
              {availableRides.map((ride) => (
                <RideCard
                  key={ride.id}
                  ride={ride}
                  display={normalizeRideForDisplay(ride)}
                  onAccept={handleAcceptRide}
                  showAcceptButton
                />
              ))}
            </div>
          )}
        </div>

        <div className="mb-6">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">My backend rides</h2>

          {myRides.length === 0 ? (
            <div className="bg-slate-900 rounded-2xl p-8 text-center border border-slate-800">
              <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-slate-500" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-slate-100 mb-2">No assigned backend rides</h3>
              <p className="text-slate-400 text-sm">Accept a request from the backend pool to see it here.</p>
            </div>
          ) : (
            <div>
              {myRides.map((ride) => (
                <RideCard key={ride.id} ride={ride} display={normalizeRideForDisplay(ride)} />
              ))}
            </div>
          )}
        </div>
      </div>

      <BottomNavigation />
    </div>
  )
}

export default memo(Dashboard)
