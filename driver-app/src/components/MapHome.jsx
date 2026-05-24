import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.jsx'
import driverAPI, { ALLOW_RIDE_SIMULATION } from '../utils/api.js'
import MapView from './MapView.jsx'
import BottomNavigation from './BottomNavigation.jsx'
import { buildExperimentalMapMarkers } from '../utils/experimentalMapMarkers.js'
import { useDriverGeolocation } from '../hooks/useDriverGeolocation.js'
import { useTelemetryPing } from '../hooks/useTelemetryPing.js'
import SilMapLayer from './SilMapLayer.jsx'
import StreetIntelligencePanel from './cockpit/StreetIntelligencePanel.jsx'
import CityRealityPanel from './cockpit/CityRealityPanel.jsx'
import { GEOLOCATION_STATES, geolocationDriverMessage } from '../utils/locationTruth.js'
import { resolveMapCenterPresentation } from '../utils/mapCenterPresentation.js'
import { resolveMapSurfaceState } from '../utils/mapLocationSurface.js'
import { writeCachedMapViewport } from '../utils/mapViewportCache.js'
import { resolveMapRouteFoundation } from '../utils/mapRouteFoundation.js'
import {
  fetchTrafficSignals,
  TRAFFIC_SIGNALS_ENABLED,
} from '../services/trafficSignalsService.js'
import { trafficSignalsToMapMarkers } from '../utils/trafficSignalMarkers.js'
import {
  DRIVER_STATES,
  canTransition,
  getNextDriverAction,
} from '../utils/driverState.js'
import BetaFirstRunAck from './BetaFirstRunAck.jsx'
import BetaTruthNotice from './BetaTruthNotice.jsx'
import DriverCockpitShell from './cockpit/DriverCockpitShell.jsx'
import { friendlyAcceptError } from '../utils/rideRequestMessages.js'
import DriverStatusBar from './cockpit/DriverStatusBar.jsx'
import TripTruthDetails from './cockpit/TripTruthDetails.jsx'
import DriverLocationChip from './cockpit/DriverLocationChip.jsx'
import MarketplaceBottomSheet from './cockpit/MarketplaceBottomSheet.jsx'
import DiagnosticsDrawer from './cockpit/DiagnosticsDrawer.jsx'
import DevActionDock from './cockpit/DevActionDock.jsx'
import CockpitNetworkBanner from './CockpitNetworkBanner.jsx'
import CockpitSkeleton from './cockpit/CockpitSkeleton.jsx'
import { useActiveRide } from '../hooks/useActiveRide.js'
import { formatCurrency } from '../theme/halfAppTheme.js'
import { driverPayoutDollars } from '../utils/ridePricingDisplay.js'
import { isBackendClaimConflict } from '../utils/rideTransparency.js'
import { useDriverPreferences } from '../context/DriverPreferencesContext.jsx'
import { playOfferSound } from '../utils/sounds.js'

const STATE_LABELS = {
  [DRIVER_STATES.OFFLINE]: { label: 'Offline', tone: 'bg-slate-700 text-slate-200' },
  [DRIVER_STATES.ONLINE_IDLE]: { label: 'Online', tone: 'bg-emerald-500/20 text-emerald-300' },
  [DRIVER_STATES.REQUEST_INCOMING]: { label: 'Incoming', tone: 'bg-amber-500/20 text-amber-200' },
  [DRIVER_STATES.ACCEPTED_TO_PICKUP]: { label: 'To pickup', tone: 'bg-sky-500/20 text-sky-200' },
  [DRIVER_STATES.ARRIVED_PICKUP]: { label: 'At pickup', tone: 'bg-blue-500/20 text-blue-200' },
  [DRIVER_STATES.IN_PROGRESS]: { label: 'In progress', tone: 'bg-indigo-500/20 text-indigo-200' },
  [DRIVER_STATES.COMPLETED]: { label: 'Completed', tone: 'bg-emerald-500/20 text-emerald-200' },
}

const ACTIVE_BACKEND_STATUSES = new Set([
  'accepted',
  'driver_arrived',
  'in_progress',
])

const NETWORK_DEGRADED_MS = 15_000

function isTransientNetworkError(err) {
  if (!err) return false
  if (err.retryableWrite) return true
  if (err.status === 502 || err.status === 503 || err.status === 504) return true
  if (err.name === 'AbortError') return true
  const message = String(err.message || '').toLowerCase()
  return message.includes('fetch') || message.includes('network') || message.includes('aborted')
}

function hasCoordinatePair(lat, lng) {
  return Number.isFinite(Number(lat)) && Number.isFinite(Number(lng))
}

function mapBackendStatusToDriverState(status) {
  if (status === 'requested') return DRIVER_STATES.REQUEST_INCOMING
  if (status === 'accepted') return DRIVER_STATES.ACCEPTED_TO_PICKUP
  if (status === 'driver_arrived') return DRIVER_STATES.ARRIVED_PICKUP
  if (status === 'in_progress') return DRIVER_STATES.IN_PROGRESS
  if (status === 'completed') return DRIVER_STATES.COMPLETED
  return DRIVER_STATES.ONLINE_IDLE
}

function backendRideToCockpitRide(ride) {
  if (!ride) return null
  if (
    !hasCoordinatePair(ride.pickup_latitude, ride.pickup_longitude) ||
    !hasCoordinatePair(ride.dropoff_latitude, ride.dropoff_longitude)
  ) {
    throw new Error('Backend ride is missing pickup/dropoff coordinates')
  }
  const distance = Number(ride.distance_km ?? 0)
  const payout = driverPayoutDollars(ride)
  return {
    rideId: ride.id,
    pickup: {
      lat: Number(ride.pickup_latitude),
      lng: Number(ride.pickup_longitude),
      label: ride.pickup_location || 'Pickup not provided',
    },
    dropoff: {
      lat: Number(ride.dropoff_latitude),
      lng: Number(ride.dropoff_longitude),
      label: ride.destination || 'Destination not provided',
    },
    riderName: ride.customer_name || 'Rider',
    fareAmount: payout != null && payout > 0 ? payout : null,
    pricing: ride.pricing ?? null,
    distance: Number.isFinite(distance) ? distance : 0,
    duration: Number(ride.duration_minutes ?? 0) || 0,
    orderingRank: ride.ordering_rank ?? null,
    orderingScore: ride.ordering_score ?? null,
    whyThisRank: ride.why_this_rank ?? null,
    dispatchPolicyName: ride.dispatch_policy_name ?? null,
    policyVersion: ride.policy_version ?? null,
    generatedAt: ride.generated_at ?? null,
    status: mapBackendStatusToDriverState(ride.status),
    backendStatus: ride.status,
    source: ride.lifecycle_reason === 'simulation' ? 'simulation' : 'backend',
    dispatchExpiresAt: ride.dispatch_expires_at ?? null,
    dispatchTimeoutSeconds: ride.dispatch_timeout_seconds ?? 30,
    raw: ride,
  }
}

function statusFromPresence(presence) {
  const state = presence?.state || presence?.effective_state || presence?.availability
  return state === 'available'
    ? { state: DRIVER_STATES.ONLINE_IDLE, online: true }
    : { state: DRIVER_STATES.OFFLINE, online: false }
}

function statusFromDriverMe(meStatus) {
  if (meStatus && typeof meStatus.online === 'boolean') {
    return meStatus.online
      ? { state: DRIVER_STATES.ONLINE_IDLE, online: true }
      : { state: DRIVER_STATES.OFFLINE, online: false }
  }
  return statusFromPresence(meStatus)
}

function hydrateFromActiveRidePayload(payload) {
  if (!payload?.ride) return null
  const ride = backendRideToCockpitRide(payload.ride)
  const lifecycleStatus =
    payload.lifecycle?.current || payload.lifecycle_stage || ride.backendStatus
  return {
    ride,
    state: { state: mapBackendStatusToDriverState(lifecycleStatus), online: true },
    resume: {
      rideId: ride.rideId,
      status: lifecycleStatus,
    },
  }
}

export default function MapHome() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const { preferences } = useDriverPreferences()
  const {
    activeRide: activeRidePayload,
    loading: activeRideLoading,
    refetch: refetchActiveRide,
  } = useActiveRide({ enabled: Boolean(user) })

  const [status, setStatus] = useState({ state: DRIVER_STATES.OFFLINE, online: false })
  const [activeRide, setActiveRide] = useState(null)
  const [completedFlash, setCompletedFlash] = useState(null)
  const [lastCompletedRide, setLastCompletedRide] = useState(null)
  const [earningsSummary, setEarningsSummary] = useState(null)
  const [loadingBackend, setLoadingBackend] = useState(false)
  const [backendError, setBackendError] = useState(null)
  const [backendHideNotice, setBackendHideNotice] = useState(null)
  const [claimConflict, setClaimConflict] = useState(false)
  const [lastConflictRideId, setLastConflictRideId] = useState(null)
  const [conflictTransparency, setConflictTransparency] = useState(null)
  const [conflictTransparencyLoading, setConflictTransparencyLoading] = useState(false)
  const [conflictTransparencyUnavailable, setConflictTransparencyUnavailable] = useState(false)
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false)
  const [driverApproved, setDriverApproved] = useState(true)
  const [presenceStale, setPresenceStale] = useState(false)
  const [meStatusSnapshot, setMeStatusSnapshot] = useState(null)
  const flashTimer = useRef(null)
  const lastIncomingSoundRideId = useRef(null)
  const refreshSeq = useRef(0)
  const lastConflictRideIdRef = useRef(null)
  const activeRideRef = useRef(null)
  const [trafficOverlayMarkers, setTrafficOverlayMarkers] = useState([])
  const [resumeNotice, setResumeNotice] = useState(null)
  const [networkDegraded, setNetworkDegraded] = useState(false)
  const [sseFailed, setSseFailed] = useState(false)
  const [leafletMap, setLeafletMap] = useState(null)
  const [silPanelOpen, setSilPanelOpen] = useState(false)
  const [crlPanelOpen, setCrlPanelOpen] = useState(false)
  const [silShowBusy, setSilShowBusy] = useState(true)
  const [silShowSlow, setSilShowSlow] = useState(true)
  const initialResumeChecked = useRef(false)
  const degradedTimer = useRef(null)

  const {
    position: devicePosition,
    status: geoStatus,
    usingFallback: geoUsingFallback,
    error: geoError,
    accuracyMeters: geoAccuracyMeters,
    speedMps: geoSpeedMps,
  } = useDriverGeolocation()

  const telemetrySnapshot = useCallback(() => {
    if (!devicePosition) return null
    return {
      lat: devicePosition.lat,
      lng: devicePosition.lng,
      capturedAt: devicePosition.capturedAt,
      speedMps: geoSpeedMps,
    }
  }, [devicePosition, geoSpeedMps])

  useTelemetryPing({
    enabled: status.online && Boolean(devicePosition),
    getSnapshot: telemetrySnapshot,
  })

  const clearConflictMemory = useCallback(() => {
    setLastConflictRideId(null)
    lastConflictRideIdRef.current = null
    setClaimConflict(false)
    setConflictTransparency(null)
    setConflictTransparencyLoading(false)
    setConflictTransparencyUnavailable(false)
  }, [])

  const loadConflictTransparency = useCallback(async (rideId) => {
    if (!rideId) return
    setConflictTransparencyLoading(true)
    setConflictTransparencyUnavailable(false)
    setConflictTransparency(null)
    try {
      const proof = await driverAPI.getRideTransparency(rideId)
      setConflictTransparency(proof)
    } catch {
      setConflictTransparency(null)
      setConflictTransparencyUnavailable(true)
    } finally {
      setConflictTransparencyLoading(false)
    }
  }, [])

  useEffect(() => () => {
    if (flashTimer.current) clearTimeout(flashTimer.current)
    if (degradedTimer.current) clearTimeout(degradedTimer.current)
  }, [])

  const markNetworkDegraded = useCallback(() => {
    setNetworkDegraded(true)
    if (degradedTimer.current) clearTimeout(degradedTimer.current)
    degradedTimer.current = window.setTimeout(() => setNetworkDegraded(false), NETWORK_DEGRADED_MS)
  }, [])

  const clearNetworkDegraded = useCallback(() => {
    setNetworkDegraded(false)
    if (degradedTimer.current) clearTimeout(degradedTimer.current)
  }, [])

  const summary = useMemo(() => {
    const data = earningsSummary || {}
    return {
      todayEarnings: data.today_earnings || 0,
      todayTrips: data.today_rides || 0,
      totalTrips: data.total_rides_completed || 0,
    }
  }, [earningsSummary])

  const refreshBackendTruth = useCallback(async (showRequested = false, options = {}) => {
    const refreshId = ++refreshSeq.current
    const excludeRideId = options.excludeRideId ?? lastConflictRideIdRef.current ?? null
    const quiet = Boolean(options.quiet)
    if (!quiet) setLoadingBackend(true)
    setBackendError(null)
    try {
      const [meStatus, available, mine, earnings] = await Promise.all([
        driverAPI.getDriverMeStatus(),
        driverAPI.getAvailableRides(),
        driverAPI.getMyRides(),
        driverAPI.getEarnings(),
      ])
      const presenceStatus = statusFromDriverMe(meStatus)

      const myRides = Array.isArray(mine) ? mine : []
      const currentRideId = meStatus?.current_ride_id
      const assignedByStatusId =
        currentRideId != null
          ? myRides.find(
              (ride) =>
                Number(ride.id) === Number(currentRideId) &&
                ACTIVE_BACKEND_STATUSES.has(ride.status)
            )
          : null
      const assigned =
        assignedByStatusId || myRides.find((ride) => ACTIVE_BACKEND_STATUSES.has(ride.status))
      const latestCompleted = myRides
        .filter((ride) => ride.status === 'completed' && ride.pricing?.financial_locked)
        .sort((a, b) => String(b.completed_at || '').localeCompare(String(a.completed_at || '')))[0]
      if (latestCompleted && !assigned) {
        try {
          setLastCompletedRide(backendRideToCockpitRide(latestCompleted))
        } catch {
          /* ignore malformed completed row */
        }
      }
      let requested = null
      const preserveConflictIdle = lastConflictRideIdRef.current != null
      if (showRequested && Array.isArray(available) && !preserveConflictIdle) {
        const eligible = available.filter((ride) => ride.id !== excludeRideId)
        requested =
          eligible.sort((a, b) => Number(b.id) - Number(a.id))[0] ?? null
      }
      const selected = assigned || requested || null
      const cockpitRide = backendRideToCockpitRide(selected)
      if (refreshId !== refreshSeq.current) return
      setActiveRide(cockpitRide)
      setEarningsSummary(earnings?.earnings_summary || null)

      if (cockpitRide && options.resumeBanner && !initialResumeChecked.current) {
        initialResumeChecked.current = true
        setResumeNotice({
          rideId: cockpitRide.rideId,
          status: cockpitRide.backendStatus || cockpitRide.status,
        })
      }

      if (cockpitRide) {
        setStatus({ state: cockpitRide.status, online: true })
      } else {
        setResumeNotice(null)
        setStatus(
          presenceStatus.online
            ? { state: DRIVER_STATES.ONLINE_IDLE, online: true }
            : { state: DRIVER_STATES.OFFLINE, online: false }
        )
      }
    } catch (err) {
      if (refreshId !== refreshSeq.current) return
      setActiveRide(null)
      setBackendError(err?.message || 'Backend ride lifecycle is unavailable')
    } finally {
      if (refreshId === refreshSeq.current && !quiet) setLoadingBackend(false)
    }
  }, [])

  useEffect(() => {
    activeRideRef.current = activeRide
  }, [activeRide])

  const pickIncomingRideFromPool = useCallback((rides, excludeRideId = null) => {
    if (!Array.isArray(rides)) return null
    const eligible = rides.filter((ride) => ride.id !== excludeRideId)
    return eligible.sort((a, b) => Number(b.id) - Number(a.id))[0] ?? null
  }, [])

  const applyPoolSnapshot = useCallback(
    (rides) => {
      const current = activeRideRef.current
      if (current && ACTIVE_BACKEND_STATUSES.has(current.backendStatus)) return
      const excludeRideId = lastConflictRideIdRef.current
      const requested = pickIncomingRideFromPool(rides, excludeRideId)
      if (requested) {
        try {
          const cockpitRide = backendRideToCockpitRide(requested)
          setActiveRide(cockpitRide)
          setStatus({ state: DRIVER_STATES.REQUEST_INCOMING, online: true })
          return
        } catch {
          /* malformed snapshot row */
        }
      }
      if (!current || current.status === DRIVER_STATES.REQUEST_INCOMING) {
        setActiveRide(null)
        setStatus((prev) =>
          prev.online
            ? { state: DRIVER_STATES.ONLINE_IDLE, online: true }
            : { state: DRIVER_STATES.OFFLINE, online: false }
        )
      }
    },
    [pickIncomingRideFromPool]
  )

  const applyPoolDelta = useCallback(
    (event) => {
      if (!event?.type) return
      const current = activeRideRef.current
      switch (event.type) {
        case 'ride.created': {
          if (current) return
          if (lastConflictRideIdRef.current === event.ride_id) return
          if (event.ride) {
            try {
              const cockpitRide = backendRideToCockpitRide(event.ride)
              setActiveRide(cockpitRide)
              setStatus({ state: DRIVER_STATES.REQUEST_INCOMING, online: true })
            } catch {
              refreshBackendTruth(true, { quiet: true, excludeRideId: lastConflictRideIdRef.current })
            }
          } else {
            refreshBackendTruth(true, { quiet: true, excludeRideId: lastConflictRideIdRef.current })
          }
          break
        }
        case 'ride.claimed':
        case 'ride.cancelled':
          if (
            current?.rideId === event.ride_id &&
            current?.status === DRIVER_STATES.REQUEST_INCOMING
          ) {
            setActiveRide(null)
            setStatus({ state: DRIVER_STATES.ONLINE_IDLE, online: true })
          }
          break
        default:
          break
      }
    },
    [refreshBackendTruth]
  )

  const recoverActiveRideOnOnline = useCallback(async () => {
    const prevRideId = activeRide?.rideId
    const prevBackendStatus = activeRide?.backendStatus
    try {
      const payload = await refetchActiveRide()
      const hydrated = hydrateFromActiveRidePayload(payload)
      if (!hydrated) {
        if (prevRideId && prevBackendStatus && ACTIVE_BACKEND_STATUSES.has(prevBackendStatus)) {
          setBackendHideNotice(
            'This ride was cancelled by the customer while you were offline.'
          )
          setActiveRide(null)
          setResumeNotice(null)
          setStatus((current) =>
            current.online
              ? { state: DRIVER_STATES.ONLINE_IDLE, online: true }
              : { state: DRIVER_STATES.OFFLINE, online: false }
          )
        }
        await refreshBackendTruth(true, { quiet: true })
        return
      }
      setActiveRide(hydrated.ride)
      setStatus(hydrated.state)
      if (
        prevRideId === hydrated.ride.rideId &&
        prevBackendStatus &&
        prevBackendStatus !== hydrated.resume.status
      ) {
        setResumeNotice({
          rideId: hydrated.ride.rideId,
          status: hydrated.resume.status,
        })
      }
      clearNetworkDegraded()
      await refreshBackendTruth(true, { quiet: true })
    } catch {
      await refreshBackendTruth(true, { quiet: true })
    }
  }, [activeRide, refetchActiveRide, clearNetworkDegraded, refreshBackendTruth])

  const initialBackendLoadDone = useRef(false)

  useEffect(() => {
    if (activeRideLoading || initialBackendLoadDone.current) return
    let cancelled = false
    async function loadInitialBackendTruth() {
      setLoadingBackend(true)
      setBackendError(null)
      try {
        const [meStatus, profile] = await Promise.all([
          driverAPI.getDriverMeStatus(),
          driverAPI.getDriverSettingsProfile().catch(() => null),
        ])
        if (cancelled) return
        setMeStatusSnapshot(meStatus)
        const approved = String(profile?.approval_status || 'approved').toLowerCase() === 'approved'
        setDriverApproved(approved)
        const backendStatus = statusFromDriverMe(meStatus)
        if (meStatus?.last_seen_at) {
          const ageMs = Date.now() - new Date(meStatus.last_seen_at).getTime()
          setPresenceStale(backendStatus.online && Number.isFinite(ageMs) && ageMs > 45_000)
        } else {
          setPresenceStale(false)
        }
        const hydrated = hydrateFromActiveRidePayload(activeRidePayload)
        if (hydrated) {
          setActiveRide(hydrated.ride)
          setStatus(hydrated.state)
          setResumeNotice(hydrated.resume)
          initialResumeChecked.current = true
        } else {
          setStatus(backendStatus)
        }
        await refreshBackendTruth(backendStatus.online, { resumeBanner: !hydrated })
      } catch (err) {
        if (!cancelled) {
          setActiveRide(null)
          setBackendError(err?.message || 'Could not load backend driver availability')
        }
      } finally {
        if (!cancelled) {
          setLoadingBackend(false)
          initialBackendLoadDone.current = true
        }
      }
    }
    loadInitialBackendTruth()
    return () => {
      cancelled = true
    }
  }, [activeRideLoading, activeRidePayload, refreshBackendTruth])

  useEffect(() => {
    const onVisibility = () => {
      if (document.visibilityState !== 'visible') return
      refreshBackendTruth(false, { quiet: true })
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => document.removeEventListener('visibilitychange', onVisibility)
  }, [refreshBackendTruth])

  const goOnline = useCallback(async () => {
    if (!driverApproved) {
      setBackendError('Account not approved — you cannot go online yet')
      return
    }
    if (!canTransition(status.state, DRIVER_STATES.ONLINE_IDLE)) return
    const lat = Number(devicePosition?.lat ?? devicePosition?.latitude)
    const lng = Number(devicePosition?.lng ?? devicePosition?.longitude)
    if (!hasCoordinatePair(lat, lng)) {
      setBackendError('Location is required before going online')
      return
    }
    setLoadingBackend(true)
    setBackendError(null)
    setBackendHideNotice(null)
    clearConflictMemory()
    try {
      await driverAPI.patchDriverMeStatus({ online: true, lat, lng })
      await driverAPI.sendHeartbeat()
      setStatus({ state: DRIVER_STATES.ONLINE_IDLE, online: true })
      await refreshBackendTruth(true)
    } catch (err) {
      setBackendError(err?.message || 'Could not update backend availability')
    } finally {
      setLoadingBackend(false)
    }
  }, [refreshBackendTruth, status.state, clearConflictMemory, devicePosition, driverApproved])

  const goOffline = useCallback(async () => {
    if (activeRide) return
    setLoadingBackend(true)
    setBackendError(null)
    setBackendHideNotice(null)
    clearConflictMemory()
    try {
      await driverAPI.patchDriverMeStatus({ online: false })
      setActiveRide(null)
      setStatus({ state: DRIVER_STATES.OFFLINE, online: false })
    } catch (err) {
      setBackendError(err?.message || 'Could not update backend availability')
    } finally {
      setLoadingBackend(false)
    }
  }, [activeRide, clearConflictMemory])

  const createSimulationRide = useCallback(async () => {
    if (!ALLOW_RIDE_SIMULATION) return
    if (activeRide) return
    if (status.state !== DRIVER_STATES.ONLINE_IDLE) return
    setLoadingBackend(true)
    setBackendError(null)
    setBackendHideNotice(null)
    clearConflictMemory()
    try {
      const response = await driverAPI.createSimulationRide({
        customer_name: 'Simulation Rider',
        pickup_location: 'Simulation Pickup',
        destination: 'Simulation Dropoff',
        distance_km: 14.2,
        duration_minutes: 22,
      })
      const ride = backendRideToCockpitRide(response?.ride)
      setActiveRide(ride)
      setStatus({ state: DRIVER_STATES.REQUEST_INCOMING, online: true })
    } catch (err) {
      setBackendError(err?.message || 'Could not create simulation ride')
    } finally {
      setLoadingBackend(false)
    }
  }, [activeRide, status.state, clearConflictMemory])

  const acceptRide = useCallback(async () => {
    if (!activeRide) return
    const conflictRideId = activeRide.rideId
    setLoadingBackend(true)
    setBackendError(null)
    setBackendHideNotice(null)
    try {
      const response = await driverAPI.acceptRide(conflictRideId)
      clearNetworkDegraded()
      clearConflictMemory()
      const ride = backendRideToCockpitRide(response?.ride)
      setActiveRide(ride)
      setStatus({ state: DRIVER_STATES.ACCEPTED_TO_PICKUP, online: true })
    } catch (err) {
      const structuredConflict =
        err?.status === 409 && isBackendClaimConflict(err?.detail)
      if (structuredConflict) {
        setLastConflictRideId(conflictRideId)
        lastConflictRideIdRef.current = conflictRideId
        setClaimConflict(true)
        setActiveRide(null)
        setStatus({ state: DRIVER_STATES.ONLINE_IDLE, online: true })
        setBackendError(null)
        await loadConflictTransparency(conflictRideId)
        await refreshBackendTruth(true, { excludeRideId: conflictRideId })
        return
      }
      if (err?.status === 409) {
        setBackendError(friendlyAcceptError(err))
        setClaimConflict(false)
        return
      }
      if (isTransientNetworkError(err)) markNetworkDegraded()
      setBackendError(friendlyAcceptError(err))
    } finally {
      setLoadingBackend(false)
    }
  }, [
    activeRide,
    refreshBackendTruth,
    clearConflictMemory,
    loadConflictTransparency,
    markNetworkDegraded,
    clearNetworkDegraded,
  ])

  const declineRide = useCallback(
    async (options = {}) => {
      if (!activeRide) return
      setLoadingBackend(true)
      setBackendError(null)
      setBackendHideNotice(null)
      try {
        if (options.reason === 'dispatch_timeout') {
          await driverAPI.declineDispatchOffer(activeRide.rideId).catch(() => null)
        } else {
          await driverAPI.declineDispatchOffer(activeRide.rideId).catch(async () => {
            await driverAPI.hideRide(activeRide.rideId, { reason: 'driver_declined_offer' })
          })
        }
        setActiveRide(null)
        setStatus({ state: DRIVER_STATES.ONLINE_IDLE, online: true })
        if (options.reason !== 'dispatch_timeout') {
          setBackendHideNotice(
            'Offer declined. The ride may be sent to another eligible driver.'
          )
        }
        await refreshBackendTruth(true)
      } catch (err) {
        setBackendError(err?.message || 'Could not decline ride')
      } finally {
        setLoadingBackend(false)
      }
    },
    [activeRide, refreshBackendTruth]
  )

  useEffect(() => {
    if (!status.online) return undefined
    let cancelled = false
    async function heartbeat() {
      try {
        const presence = await driverAPI.sendHeartbeat()
        if (!cancelled && (presence?.state === 'stale' || presence?.state === 'disconnected')) {
          setStatus(statusFromPresence(presence))
        }
      } catch {
        // Heartbeat must not invent local truth.
      }
    }
    heartbeat()
    const timer = window.setInterval(heartbeat, 30_000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [status.online])

  useEffect(() => {
    if (!status.online || activeRide || status.state !== DRIVER_STATES.ONLINE_IDLE) return undefined
    if (typeof EventSource === 'undefined') {
      setSseFailed(true)
      return undefined
    }

    let closed = false
    const stream = driverAPI.subscribeAvailableRidesStream({
      onOpen: () => {
        if (!closed) setSseFailed(false)
      },
      onSnapshot: (rides) => {
        if (closed) return
        setSseFailed(false)
        applyPoolSnapshot(rides)
      },
      onDelta: (event) => {
        if (closed) return
        applyPoolDelta(event)
      },
      onError: () => {
        if (!closed) setSseFailed(true)
      },
    })

    return () => {
      closed = true
      stream?.close?.()
    }
  }, [activeRide, applyPoolDelta, applyPoolSnapshot, status.online, status.state])

  useEffect(() => {
    if (!sseFailed || !status.online || activeRide || status.state !== DRIVER_STATES.ONLINE_IDLE) return undefined
    const timer = window.setInterval(() => {
      refreshBackendTruth(true, { excludeRideId: lastConflictRideIdRef.current })
    }, 5_000)
    return () => window.clearInterval(timer)
  }, [activeRide, refreshBackendTruth, sseFailed, status.online, status.state])

  const advanceState = useCallback(async () => {
    const next = getNextDriverAction(status.state)
    if (!next) return
    if (!canTransition(status.state, next.next)) return
    if (!activeRide) return

    setLoadingBackend(true)
    setBackendError(null)
    setBackendHideNotice(null)
    try {
      let response
      if (next.next === DRIVER_STATES.ARRIVED_PICKUP) {
        response = await driverAPI.arrivePickup(activeRide.rideId)
      } else if (next.next === DRIVER_STATES.IN_PROGRESS) {
        response = await driverAPI.startRide(activeRide.rideId)
      } else if (next.next === DRIVER_STATES.COMPLETED) {
        response = await driverAPI.completeRide(activeRide.rideId)
      }

      if (next.next === DRIVER_STATES.COMPLETED) {
        const completedRide = response?.ride || activeRide.raw
        const cockpitCompleted = backendRideToCockpitRide(completedRide)
        const fare =
          response?.fare_earned ??
          driverPayoutDollars(completedRide) ??
          activeRide.fareAmount
        clearNetworkDegraded()
        await refreshBackendTruth(true)
        setActiveRide(null)
        setLastCompletedRide(cockpitCompleted)
        setStatus({ state: DRIVER_STATES.ONLINE_IDLE, online: true })
        setCompletedFlash({
          fare,
          riderName: completedRide?.customer_name || activeRide.riderName,
          ride: cockpitCompleted,
        })
        if (flashTimer.current) clearTimeout(flashTimer.current)
        flashTimer.current = setTimeout(() => setCompletedFlash(null), 8000)
        return
      }

      clearNetworkDegraded()
      const ride = backendRideToCockpitRide(response?.ride)
      setActiveRide(ride)
      setStatus({ state: next.next, online: true })
    } catch (err) {
      if (isTransientNetworkError(err)) markNetworkDegraded()
      setBackendError(err?.message || 'Could not advance ride')
    } finally {
      setLoadingBackend(false)
    }
  }, [activeRide, refreshBackendTruth, status.state, markNetworkDegraded, clearNetworkDegraded])

  const handleLogout = useCallback(() => {
    logout()
    navigate('/', { replace: true })
  }, [logout, navigate])

  const stateMeta = STATE_LABELS[status.state] ?? STATE_LABELS[DRIVER_STATES.OFFLINE]
  const isOnline = status.online && status.state !== DRIVER_STATES.OFFLINE
  const onlineToggleDisabled = !driverApproved || (!!activeRide && isOnline)

  useEffect(() => {
    if (!activeRide || activeRide.status !== DRIVER_STATES.REQUEST_INCOMING) return
    if (lastIncomingSoundRideId.current === activeRide.rideId) return
    lastIncomingSoundRideId.current = activeRide.rideId
    playOfferSound(Boolean(preferences?.notif_sound_enabled))
  }, [activeRide, preferences?.notif_sound_enabled])

  const nextAction = getNextDriverAction(status.state)

  useEffect(() => {
    let cancelled = false
    async function loadTrafficOverlay() {
      if (!TRAFFIC_SIGNALS_ENABLED || !activeRide?.pickup || !activeRide?.dropoff) {
        if (!cancelled) setTrafficOverlayMarkers([])
        return
      }
      const token = localStorage.getItem('driver_token')
      const result = await fetchTrafficSignals(token, {
        origin: activeRide.pickup,
        destination: activeRide.dropoff,
      })
      if (!cancelled) {
        setTrafficOverlayMarkers(trafficSignalsToMapMarkers(result.signals))
      }
    }
    loadTrafficOverlay()
    return () => {
      cancelled = true
    }
  }, [
    activeRide?.rideId,
    activeRide?.pickup?.lat,
    activeRide?.pickup?.lng,
    activeRide?.dropoff?.lat,
    activeRide?.dropoff?.lng,
  ])

  const experimentalMarkers = useMemo(
    () =>
      buildExperimentalMapMarkers({
        includeDevDriver: false,
        devicePosition,
        usingDevFallback: geoUsingFallback,
        activeRide,
        extraMarkers: trafficOverlayMarkers,
      }),
    [activeRide, devicePosition, geoUsingFallback, trafficOverlayMarkers]
  )

  useEffect(() => {
    if (geoStatus !== GEOLOCATION_STATES.ALLOWED || !devicePosition) return
    writeCachedMapViewport({
      latitude: devicePosition.lat,
      longitude: devicePosition.lng,
      zoom: 14,
      source: 'ui_viewport_only',
      savedAt: new Date().toISOString(),
    })
  }, [geoStatus, devicePosition])

  const isAwaitingDeviceLocation =
    geoStatus === GEOLOCATION_STATES.REQUESTING || geoStatus === GEOLOCATION_STATES.IDLE

  const mapPresentation = useMemo(
    () =>
      resolveMapCenterPresentation({
        geoStatus,
        devicePosition,
        usingDevFallback: geoUsingFallback,
        markers: experimentalMarkers,
        cachedViewport: null,
      }),
    [geoStatus, devicePosition, geoUsingFallback, experimentalMarkers]
  )

  const mapSurface = useMemo(
    () =>
      resolveMapSurfaceState({
        geoStatus,
        hasMapCenter: Boolean(mapPresentation.mapCenter),
        markerPointCount: experimentalMarkers.length,
      }),
    [geoStatus, mapPresentation.mapCenter, experimentalMarkers.length]
  )

  const showLocatingShell = isAwaitingDeviceLocation || mapPresentation.showLocatingOverlay

  const locationStatusLabel = geolocationDriverMessage(geoStatus, {
    accuracyMeters: geoAccuracyMeters,
  })

  const routeFoundation = useMemo(
    () => resolveMapRouteFoundation(activeRide?.raw),
    [activeRide?.raw]
  )

  const locationChipCompact =
    geoStatus === GEOLOCATION_STATES.ALLOWED && !geoUsingFallback && !geoError

  return (
    <DriverCockpitShell
      map={
        <>
          <MapView
            markers={experimentalMarkers}
            mapCenter={mapPresentation.mapCenter}
            centerSource={mapPresentation.centerSource}
            locating={showLocatingShell || mapSurface.isLocating}
            showMapCanvas={mapPresentation.showMapCanvas && mapSurface.canMountLeaflet}
            surfaceMode={isAwaitingDeviceLocation ? 'locating' : mapSurface.mode}
            routeFoundation={routeFoundation}
            className="cockpit-map"
            onMapReady={setLeafletMap}
          />
          <SilMapLayer
            map={leafletMap}
            enabled={isOnline}
            showBusy={silShowBusy}
            showSlow={silShowSlow}
          />
        </>
      }
    >
      <BetaFirstRunAck />
      <div className="cockpit-top-chrome" data-testid="map-region">
        <div className="cockpit-beta-banner-wrap px-3 pb-2">
          <BetaTruthNotice variant="cockpit" />
        </div>
        <DriverStatusBar
          userName={user?.name}
          stateLabel={stateMeta.label}
          isOnline={isOnline}
          onlineToggleDisabled={onlineToggleDisabled}
          onToggleOnline={isOnline ? goOffline : goOnline}
          onLogout={handleLogout}
          onOpenDiagnostics={() => setDiagnosticsOpen((v) => !v)}
          diagnosticsOpen={diagnosticsOpen}
          showDiagnostics={import.meta.env.DEV}
        />
        <div className="cockpit-location-chip-wrap">
          <DriverLocationChip
            message={locationStatusLabel}
            geoState={geoStatus}
            title={geoError || undefined}
            compact={locationChipCompact}
          />
        </div>
        {onlineToggleDisabled && (
          <p className="cockpit-offline-hint">Finish the current ride to go offline</p>
        )}
        <CockpitNetworkBanner
          degraded={networkDegraded}
          onRetry={recoverActiveRideOnOnline}
        />
        {isOnline ? (
          <div className="px-3 pb-1 flex items-center justify-between gap-2">
            <p className="text-[10px] leading-snug text-[#94a3b8] flex-1" data-testid="fleet-traffic-truth-note">
              Street Intelligence: aggregated HalfApp signals — not official traffic or demand.
            </p>
            <button
              type="button"
              className="cockpit-pressable shrink-0 rounded-lg px-2 py-1 text-[10px] font-semibold"
              onClick={() => {
                setCrlPanelOpen(false)
                setSilPanelOpen((v) => !v)
              }}
              data-testid="street-intelligence-open"
            >
              {silPanelOpen ? 'Hide' : 'Layers'}
            </button>
            <button
              type="button"
              className="cockpit-pressable shrink-0 rounded-lg px-2 py-1 text-[10px] font-semibold"
              onClick={() => {
                setSilPanelOpen(false)
                setCrlPanelOpen((v) => !v)
              }}
              data-testid="city-reality-open"
            >
              {crlPanelOpen ? 'Hide' : 'Why?'}
            </button>
          </div>
        ) : null}
        {!driverApproved ? (
          <div
            className="mx-3 mt-2 rounded-xl border border-amber-500/50 bg-amber-950/80 px-3 py-2 text-xs text-amber-100"
            data-testid="cockpit-approval-gate"
          >
            Account not approved — you cannot go online. Check Profile for status.
          </div>
        ) : null}
        {presenceStale && isOnline ? (
          <div
            className="mx-3 mt-2 rounded-xl border border-orange-500/40 bg-orange-950/70 px-3 py-2 text-xs text-orange-100"
            data-testid="cockpit-presence-stale"
          >
            You may appear offline to dispatch — last heartbeat was over 45s ago.
            {meStatusSnapshot?.last_seen_at
              ? ` Last seen: ${new Date(meStatusSnapshot.last_seen_at).toLocaleTimeString()}.`
              : ''}
          </div>
        ) : null}
        {resumeNotice && activeRide && (
          <div
            className="mx-3 mt-2 rounded-xl border border-sky-500/40 bg-sky-950/80 px-3 py-2 text-xs text-sky-100"
            data-testid="cockpit-resume-notice"
          >
            <div className="flex items-start justify-between gap-2">
              <span>
                Resumed active ride #{resumeNotice.rideId} ({resumeNotice.status})
              </span>
              <button
                type="button"
                className="shrink-0 text-sky-300 underline"
                onClick={() => setResumeNotice(null)}
              >
                Dismiss
              </button>
            </div>
          </div>
        )}
      </div>

      <CityRealityPanel
        open={crlPanelOpen && isOnline}
        onClose={() => setCrlPanelOpen(false)}
      />

      <StreetIntelligencePanel
        open={silPanelOpen && isOnline}
        onClose={() => setSilPanelOpen(false)}
        showBusy={silShowBusy}
        showSlow={silShowSlow}
        onToggleBusy={setSilShowBusy}
        onToggleSlow={setSilShowSlow}
        devicePosition={devicePosition}
        activeRide={activeRide}
      />

      <DiagnosticsDrawer
        open={diagnosticsOpen}
        onClose={() => setDiagnosticsOpen(false)}
        geoStatus={geoStatus}
        geoUsingFallback={geoUsingFallback}
        geoAccuracyMeters={geoAccuracyMeters}
        devicePosition={devicePosition}
        centerSource={mapPresentation.centerSource}
        isDev={import.meta.env.DEV}
        allowSimulation={ALLOW_RIDE_SIMULATION}
        loadingBackend={loadingBackend}
        backendError={backendError}
        onRefresh={() => refreshBackendTruth(true)}
        onCreateSimulationRide={createSimulationRide}
        canSimulate={status.state === DRIVER_STATES.ONLINE_IDLE && !activeRide}
        lastCompletedRide={lastCompletedRide}
        authToken={typeof localStorage !== 'undefined' ? localStorage.getItem('driver_token') : null}
      />

      <DevActionDock
        visible={ALLOW_RIDE_SIMULATION && status.state === DRIVER_STATES.ONLINE_IDLE && !activeRide}
        onCreateRide={createSimulationRide}
        disabled={loadingBackend}
      />

      {completedFlash && (
        <div data-testid="completed-flash" className="completed-flash-banner">
          <p className="font-semibold text-emerald-100">
            Trip with {completedFlash.riderName} completed
          </p>
          <p className="mt-1 text-[13px] text-emerald-200/90" data-testid="completed-flash-headline">
            Driver total payout {formatCurrency(completedFlash.fare)} · added to earnings
          </p>
          {completedFlash.ride?.pricing && (
            <div className="mt-3">
              <TripTruthDetails
                ride={completedFlash.ride.raw ?? completedFlash.ride}
                pricing={completedFlash.ride.pricing}
                pricingLocked={Boolean(completedFlash.ride.pricing.financial_locked)}
                pricingVariant="final"
                showRouteProvider
                title="Completed trip"
              />
            </div>
          )}
        </div>
      )}

      {activeRideLoading ? (
        <CockpitSkeleton />
      ) : (
        <MarketplaceBottomSheet
          state={status.state}
          ride={activeRide}
          summary={summary}
          isOnline={isOnline}
          nextAction={nextAction}
          loadingBackend={loadingBackend}
          backendError={backendError}
          backendHideNotice={backendHideNotice}
          claimConflict={claimConflict}
          lastConflictRideId={lastConflictRideId}
          conflictTransparency={conflictTransparency}
          conflictTransparencyLoading={conflictTransparencyLoading}
          conflictTransparencyUnavailable={conflictTransparencyUnavailable}
          goOnline={goOnline}
          goOffline={goOffline}
          acceptRide={acceptRide}
          declineRide={declineRide}
          advanceState={advanceState}
          refreshBackendTruth={refreshBackendTruth}
          onConnectivityRestore={recoverActiveRideOnOnline}
          sseFailed={sseFailed}
          lastCompletedRide={lastCompletedRide}
          onDismissCompletedSummary={() => setLastCompletedRide(null)}
        />
      )}

      <BottomNavigation embedded />
    </DriverCockpitShell>
  )
}
