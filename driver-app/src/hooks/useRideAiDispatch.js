import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { sendAssistantChat } from '../services/engineeringAssistantApi.js'
import {
  AI_LIFECYCLE_EVENTS,
  DISPATCH_AI_STATES,
  ROUTE_ADVISORY_LABEL,
  createAiRateLimiter,
  createDeclineRedispatchManager,
  resolveTripRecord,
  routeContextFromRide,
  formatRouteNoteForDisplay,
  streamAI,
  abortActiveStream,
  shouldApplyStreamUpdate,
  buildMatchAnalysisPrompt,
  buildRouteIntelligencePrompt,
  buildDeclineRedispatchPrompt,
  buildOpsMonitoringPrompt,
  buildTripCompletePrompt,
} from '../services/rideAiDispatch/index.js'

function nextStreamId() {
  return `ai-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

/**
 * Advisory ride AI dispatch loop — never mutates backend dispatch.
 */
export function useRideAiDispatch({
  authToken,
  canSendToModel = false,
  fetchRidePayment,
}) {
  const [panelText, setPanelText] = useState('')
  const [panelMeta, setPanelMeta] = useState('')
  const [manualMode, setManualMode] = useState(false)
  const [dispatchAiState, setDispatchAiState] = useState(DISPATCH_AI_STATES.IDLE)
  const [streaming, setStreaming] = useState(false)
  const rateLimiterRef = useRef(createAiRateLimiter())
  const declineManagerRef = useRef(createDeclineRedispatchManager())
  const lastEventRef = useRef(null)
  const lastIncomingRideIdRef = useRef(null)

  const resetPanel = useCallback(() => {
    abortActiveStream()
    setPanelText('')
    setPanelMeta('')
    setStreaming(false)
  }, [])

  const runAdvisoryStream = useCallback(
    async (eventType, prompt, metaLabel = '') => {
      if (!canSendToModel || !authToken) {
        setManualMode(true)
        setPanelMeta('AI unavailable — manual mode')
        return
      }
      const gate = rateLimiterRef.current.canCall()
      if (!gate.ok) {
        setManualMode(true)
        setPanelMeta(
          gate.reason === 'session_budget_exceeded'
            ? 'AI paused — session budget exceeded'
            : 'AI paused — rate limit',
        )
        return
      }
      rateLimiterRef.current.recordCall()
      setManualMode(false)
      const streamId = nextStreamId()
      setStreaming(true)
      setPanelMeta(metaLabel)
      setPanelText('')
      lastEventRef.current = eventType

      await streamAI({
        streamId,
        prompt,
        fetchChat: ({ prompt: p, signal }) =>
          sendAssistantChat(authToken, { messages: [], prompt: p, signal }),
        onChunk: (char, sid) => {
          if (!shouldApplyStreamUpdate(sid, streamId)) return
          setPanelText((prev) => prev + char)
        },
        onDone: (reply, sid) => {
          if (!shouldApplyStreamUpdate(sid, streamId)) return
          setPanelText(reply)
          setStreaming(false)
        },
        onError: (err, sid) => {
          if (!shouldApplyStreamUpdate(sid, streamId)) return
          setManualMode(true)
          setPanelMeta(err?.message || 'AI error — manual mode')
          setStreaming(false)
        },
      })
    },
    [authToken, canSendToModel],
  )

  const onIncomingMatch = useCallback(
    (ride) => {
      if (!ride) return
      const rideId = ride.rideId ?? ride.id
      if (lastIncomingRideIdRef.current === rideId) return
      lastIncomingRideIdRef.current = rideId
      declineManagerRef.current.setMatched()
      setDispatchAiState(DISPATCH_AI_STATES.MATCHED)
      runAdvisoryStream(
        AI_LIFECYCLE_EVENTS.MATCH_ANALYSIS,
        buildMatchAnalysisPrompt({
          ride_id: rideId,
          proximity_score: ride.proximity_score,
          rating_score: ride.rating_score,
          eta_minutes: ride.duration ?? ride.eta_minutes,
          license_plate: ride.license_plate || 'WA-7823',
          rider_name: ride.riderName ?? ride.customer_name,
        }),
        'Match analysis (advisory)',
      )
    },
    [runAdvisoryStream],
  )

  const onDriverAccept = useCallback(
    (ride) => {
      if (!ride) return
      declineManagerRef.current.setAccepted()
      setDispatchAiState(DISPATCH_AI_STATES.ACCEPTED)
      const routeCtx = routeContextFromRide(ride.raw ?? ride)
      const label = routeCtx.live ? 'Route intelligence (grounded)' : ROUTE_ADVISORY_LABEL
      runAdvisoryStream(
        AI_LIFECYCLE_EVENTS.ROUTE_INTELLIGENCE,
        buildRouteIntelligencePrompt(routeCtx),
        label,
      ).then(() => {
        if (!routeCtx.live) {
          setPanelText((prev) => formatRouteNoteForDisplay(routeCtx, prev))
        }
      })
    },
    [runAdvisoryStream],
  )

  const onDriverDecline = useCallback(
    (ride) => {
      const rideId = ride?.rideId ?? ride?.id
      const outcome = declineManagerRef.current.decline({
        onRedispatchReady: () => {
          setDispatchAiState(DISPATCH_AI_STATES.REDISPATCHING)
          runAdvisoryStream(
            AI_LIFECYCLE_EVENTS.DECLINE_REDISPATCH,
            buildDeclineRedispatchPrompt({ ride_id: rideId, phase: 'redispatching' }),
            'Redispatch assessment (advisory)',
          )
        },
      })
      if (outcome === 'declined') {
        setDispatchAiState(DISPATCH_AI_STATES.DECLINED)
        runAdvisoryStream(
          AI_LIFECYCLE_EVENTS.DECLINE_REDISPATCH,
          buildDeclineRedispatchPrompt({ ride_id: rideId, phase: 'declined' }),
          'Decline impact (advisory)',
        )
      }
    },
    [runAdvisoryStream],
  )

  const onTripStart = useCallback(
    (ride) => {
      declineManagerRef.current.setInTrip()
      setDispatchAiState(DISPATCH_AI_STATES.IN_TRIP)
      runAdvisoryStream(
        AI_LIFECYCLE_EVENTS.OPS_MONITORING,
        buildOpsMonitoringPrompt({
          ride_id: ride?.rideId ?? ride?.id,
          status: 'in_progress',
        }),
        'Ops monitoring (advisory)',
      )
    },
    [runAdvisoryStream],
  )

  const onTripComplete = useCallback(
    async (ride) => {
      declineManagerRef.current.setComplete()
      setDispatchAiState(DISPATCH_AI_STATES.COMPLETE)
      const rideId = ride?.rideId ?? ride?.id
      let payment = null
      if (fetchRidePayment && rideId) {
        try {
          payment = await fetchRidePayment(rideId)
        } catch {
          payment = null
        }
      }
      const pricing = ride?.pricing ?? ride?.raw?.pricing
      const fallbackGross =
        pricing?.customer_total_cents ?? pricing?.total_rider_charge_cents ?? null
      const tripRecord = resolveTripRecord(
        rideId,
        payment?.payment ?? payment,
        fallbackGross,
      )
      const meta =
        tripRecord.source === 'DEMO_SIMULATION'
          ? 'Trip complete — DEMO_SIMULATION financials'
          : 'Trip complete — ledger-backed financials'
      runAdvisoryStream(
        AI_LIFECYCLE_EVENTS.TRIP_COMPLETE,
        buildTripCompletePrompt(tripRecord),
        meta,
      )
    },
    [fetchRidePayment, runAdvisoryStream],
  )

  const onReset = useCallback(() => {
    abortActiveStream()
    rateLimiterRef.current.reset()
    declineManagerRef.current.dispose()
    lastIncomingRideIdRef.current = null
    setDispatchAiState(DISPATCH_AI_STATES.IDLE)
    setManualMode(false)
    resetPanel()
  }, [resetPanel])

  return useMemo(
    () => ({
      panelText,
      panelMeta,
      manualMode,
      dispatchAiState,
      streaming,
      rateLimiter: rateLimiterRef.current,
      onIncomingMatch,
      onDriverAccept,
      onDriverDecline,
      onTripStart,
      onTripComplete,
      onReset,
      resetPanel,
      lastEvent: lastEventRef.current,
      getDeclineManagerState: () => declineManagerRef.current.getState(),
    }),
    [
      panelText,
      panelMeta,
      manualMode,
      dispatchAiState,
      streaming,
      onIncomingMatch,
      onDriverAccept,
      onDriverDecline,
      onTripStart,
      onTripComplete,
      onReset,
      resetPanel,
    ],
  )
}
