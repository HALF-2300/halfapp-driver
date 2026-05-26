import React, { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { DRIVER_STATES } from '../../utils/driverState.js'
import { formatCurrency } from '../../theme/halfAppTheme.js'
import DriverAvailabilityCard from './DriverAvailabilityCard.jsx'
import ClaimConflictNotice from './ClaimConflictNotice.jsx'
import ExternalNavigationButtons from './ExternalNavigationButtons.jsx'
import RideRequestCard from './RideRequestCard.jsx'
import PrimaryRideActionButton from './PrimaryRideActionButton.jsx'
import TestRideLabel from '../TestRideLabel.jsx'
import { BETA_COMPLETED_TRIP_NOTE } from '../../utils/betaTruthCopy.js'
import TripTruthDetails from './TripTruthDetails.jsx'
import EarningsVisibilityPanel from '../EarningsVisibilityPanel.jsx'
import RideChatPanel from './RideChatPanel.jsx'
import RideNavigationPanel from './RideNavigationPanel.jsx'
import RideAiDispatchPanel from './RideAiDispatchPanel.jsx'

function cockpitBackendState(state) {
  if (state === DRIVER_STATES.ACCEPTED_TO_PICKUP) return 'accepted'
  if (state === DRIVER_STATES.ARRIVED_PICKUP) return 'driver_arrived'
  if (state === DRIVER_STATES.IN_PROGRESS) return 'in_progress'
  return null
}

function DriverActionSheet({ statusLabel, statusTone, headline, body, action, synced }) {
  return (
    <div data-testid="driver-action-sheet" className="driver-action-sheet">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p
            className={`text-[10px] font-semibold uppercase tracking-[0.14em] ${statusTone}`}
            data-testid={
              statusLabel === 'Available'
                ? 'availability-title'
                : statusLabel === 'Offline'
                  ? 'offline-sheet-label'
                  : undefined
            }
          >
            {statusLabel}
          </p>
          <p className="mt-1 text-[17px] font-semibold leading-snug text-[#F8FAFC]">{headline}</p>
          {body && <p className="mt-0.5 text-[13px] text-[#94A3B8]">{body}</p>}
        </div>
        {synced && (
          <span
            data-testid="presence-synced-label"
            className="shrink-0 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-300"
          >
            Synced
          </span>
        )}
      </div>
      <div className="mt-3">{action}</div>
    </div>
  )
}

export default function MarketplaceBottomSheet(props) {
  const {
    state,
    ride,
    summary,
    nextAction,
    loadingBackend,
    backendError,
    backendHideNotice,
    claimConflict,
    lastConflictRideId,
    conflictTransparency,
    conflictTransparencyLoading,
    conflictTransparencyUnavailable,
    goOnline,
    goOffline,
    acceptRide,
    declineRide,
    advanceState,
    refreshBackendTruth,
    onConnectivityRestore,
    sseFailed,
    lastCompletedRide,
    onDismissCompletedSummary,
    rideAi,
  } = props

  const [expanded, setExpanded] = useState(false)
  const sheetExpanded =
    expanded ||
    state === DRIVER_STATES.REQUEST_INCOMING ||
    state === DRIVER_STATES.ACCEPTED_TO_PICKUP ||
    state === DRIVER_STATES.ARRIVED_PICKUP ||
    state === DRIVER_STATES.IN_PROGRESS

  const sheetClass = `marketplace-bottom-sheet pointer-events-auto ${
    sheetExpanded ? 'marketplace-bottom-sheet--expanded' : ''
  }`
  const stateKey = `${state}-${ride?.rideId ?? 'none'}-${lastConflictRideId ?? 'no-conflict'}`

  let content = null
  const presenceSynced = !loadingBackend && !backendError

  if (state === DRIVER_STATES.OFFLINE) {
    content = (
      <div data-testid="sheet-offline">
        <DriverActionSheet
          statusLabel="Offline"
          statusTone="text-slate-400"
          headline="Go online to start receiving requests."
          action={
            <PrimaryRideActionButton onClick={goOnline} tone="success" testId="go-online-btn">
              Go online
            </PrimaryRideActionButton>
          }
        />
        {backendError && (
          <p className="mt-2 text-[11px] text-amber-300 text-center" data-testid="accept-ride-error">
            {backendError}
          </p>
        )}
      </div>
    )
  } else if (state === DRIVER_STATES.ONLINE_IDLE) {
    content = (
      <div data-testid="ride-pool" className="space-y-3">
        <motion.div data-testid="sheet-online-idle" className="space-y-3">
        {sseFailed && (
          <p className="text-[11px] text-orange-300" data-testid="ride-pool-live-updates-degraded">
            Live updates degraded — fallback sync every 5 seconds.
          </p>
        )}
        {lastCompletedRide?.pricing && (
          <div data-testid="ride-flow-completed-summary" className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 px-1">
              <TestRideLabel lifecycleReason={lastCompletedRide?.raw?.lifecycle_reason} />
            </div>
            <p className="text-[10px] text-[var(--ha-muted)]/80 px-1" data-testid="completed-trip-beta-note">
              {BETA_COMPLETED_TRIP_NOTE}
            </p>
            <TripTruthDetails
              ride={lastCompletedRide}
              pricing={lastCompletedRide.pricing}
              pricingLocked={Boolean(lastCompletedRide.pricing.financial_locked)}
              pricingVariant="final"
              showRouteProvider
              defaultOpen
              title="Completed trip"
            />
            <button
              type="button"
              className="w-full min-h-[44px] text-center text-[12px] text-[var(--ha-muted)] hover:text-[var(--ha-text)]"
              data-testid="dismiss-completed-summary"
              onClick={onDismissCompletedSummary}
            >
              Dismiss summary
            </button>
          </div>
        )}
        {lastConflictRideId != null && (
          <>
            <ClaimConflictNotice />
            <TripTruthDetails
              title="Transparency"
              conflictRideId={lastConflictRideId}
              conflictProof={conflictTransparency}
              conflictLoading={conflictTransparencyLoading}
              conflictUnavailable={conflictTransparencyUnavailable}
            />
          </>
        )}
        <DriverActionSheet
          statusLabel="Available"
          statusTone="text-emerald-300/90"
          headline="Waiting for requests nearby."
          synced={presenceSynced}
          action={
            <PrimaryRideActionButton onClick={goOffline} tone="neutral" testId="go-offline-btn">
              Go offline
            </PrimaryRideActionButton>
          }
        />
        {backendHideNotice && (
          <div className="space-y-2">
            <p className="text-[11px] text-amber-300 text-center" data-testid="backend-hide-notice">
              {backendHideNotice}
            </p>
            <button
              type="button"
              onClick={() => refreshBackendTruth(true)}
              disabled={loadingBackend}
              data-testid="sync-marketplace-btn"
              className="cockpit-pressable w-full min-h-[44px] rounded-full border border-white/10 bg-white/[0.06] text-[13px] font-medium text-[var(--ha-text)] disabled:opacity-50"
            >
              Sync marketplace
            </button>
          </div>
        )}
        {backendError && (
          <p className="text-[11px] text-amber-300 text-center" data-testid="accept-ride-error">
            {backendError}
          </p>
        )}
        {expanded && (
          <>
            <DriverAvailabilityCard
              title="Available"
              subtitle="Waiting for requests nearby."
              todayTrips={summary.todayTrips}
              totalTrips={summary.totalTrips}
              todayEarnings={summary.todayEarnings}
              onSync={() => refreshBackendTruth(true)}
              loadingBackend={loadingBackend}
              backendError={backendError}
              backendHideNotice={backendHideNotice}
              expanded={expanded}
              onToggleExpand={() => setExpanded((v) => !v)}
              presenceSynced={presenceSynced}
            />
            <EarningsVisibilityPanel compact className="mt-3" />
          </>
        )}
        {!expanded && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="w-full min-h-[44px] text-center text-[12px] text-[var(--ha-muted)] hover:text-[var(--ha-text)]"
            data-testid="expand-availability-stats"
          >
            Trips & earnings
          </button>
        )}
        </motion.div>
      </div>
    )
  } else if (state === DRIVER_STATES.REQUEST_INCOMING && ride) {
    content = (
      <div data-testid="sheet-request-incoming" data-ride-id={String(ride.rideId)}>
        <RideRequestCard
          ride={ride}
          loadingBackend={loadingBackend}
          claimConflict={claimConflict}
          backendError={backendError}
          onAccept={acceptRide}
          onDecline={declineRide}
        />
        <TripTruthDetails
          ride={ride}
          pricing={ride.pricing}
          pricingVariant="quote"
          showTransparency
          showRouteProvider
          title="Trip details"
        />
        {claimConflict && <ClaimConflictNotice />}
        {rideAi ? (
          <RideAiDispatchPanel
            panelText={rideAi.panelText}
            panelMeta={rideAi.panelMeta}
            manualMode={rideAi.manualMode}
            dispatchAiState={rideAi.dispatchAiState}
            streaming={rideAi.streaming}
            onReset={rideAi.onReset}
          />
        ) : null}
      </div>
    )
  } else if (
    (state === DRIVER_STATES.ACCEPTED_TO_PICKUP ||
      state === DRIVER_STATES.ARRIVED_PICKUP ||
      state === DRIVER_STATES.IN_PROGRESS) &&
    ride
  ) {
    const headline =
      state === DRIVER_STATES.ACCEPTED_TO_PICKUP
        ? 'Heading to pickup'
        : state === DRIVER_STATES.ARRIVED_PICKUP
          ? 'At pickup'
          : 'In progress'
    const subhead = state === DRIVER_STATES.IN_PROGRESS ? ride.dropoff.label : ride.pickup.label
    const buttonTone = state === DRIVER_STATES.IN_PROGRESS ? 'success' : 'primary'
    const backendCockpitState = cockpitBackendState(state)
    content = (
      <div
        className="space-y-3"
        data-testid={`sheet-${state.toLowerCase()}`}
        data-cockpit-state={backendCockpitState}
        data-ride-id={String(ride.rideId)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-wide text-cyan-300">{headline}</p>
            <p className="truncate text-[18px] font-semibold">{ride.riderName}</p>
            <p className="truncate text-[13px] text-[var(--ha-muted)]">→ {subhead}</p>
          </div>
          <div className="text-right shrink-0">
            <p className="text-[10px] uppercase tracking-wide text-[var(--ha-muted)]">Est. payout</p>
            <p className="text-[20px] font-bold" data-testid="ride-active-payout">
              {ride.fareAmount == null ? 'Pending' : formatCurrency(ride.fareAmount)}
            </p>
          </div>
        </div>
        <ExternalNavigationButtons pickup={ride.pickup} dropoff={ride.dropoff} />
        <RideNavigationPanel
          rideId={ride.rideId}
          lifecycleStage={backendCockpitState || ride.backendStatus}
          onConnectivityRestore={onConnectivityRestore}
        />
        <RideChatPanel rideId={ride.rideId} />
        {state !== DRIVER_STATES.REQUEST_INCOMING ? (
          <PrimaryRideActionButton
            onClick={() => declineRide?.({ reason: 'driver_released_active_ride' })}
            tone="neutral"
            disabled={loadingBackend}
            testId="release-ride-btn"
          >
            Release job to pool
          </PrimaryRideActionButton>
        ) : null}
        {nextAction && (
          <PrimaryRideActionButton
            onClick={advanceState}
            tone={buttonTone}
            disabled={loadingBackend}
            testId={`advance-${state.toLowerCase()}`}
          >
            {nextAction.label}
          </PrimaryRideActionButton>
        )}
        <TripTruthDetails
          ride={ride.raw ?? ride}
          pricing={ride.pricing}
          pricingLocked={Boolean(ride.pricing?.financial_locked)}
          showRouteProvider
          title="Trip details"
        />
        {backendError && <p className="text-[11px] text-amber-300 text-center">{backendError}</p>}
        {rideAi ? (
          <RideAiDispatchPanel
            panelText={rideAi.panelText}
            panelMeta={rideAi.panelMeta}
            manualMode={rideAi.manualMode}
            dispatchAiState={rideAi.dispatchAiState}
            streaming={rideAi.streaming}
            onReset={rideAi.onReset}
          />
        ) : null}
      </div>
    )
  } else {
    content = (
      <div className="space-y-3" data-testid="sheet-fallback">
        <p className="text-[13px] text-[var(--ha-muted)]">Ready when you are.</p>
        <PrimaryRideActionButton onClick={goOnline} tone="success" testId="go-online-btn">
          Go online
        </PrimaryRideActionButton>
      </div>
    )
  }

  return (
    <div
      className="marketplace-bottom-sheet-host"
      data-testid="marketplace-bottom-sheet-host"
    >
      <motion.div layout transition={{ duration: 0.22 }} className={sheetClass} data-testid="marketplace-bottom-sheet">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={stateKey}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
          >
            {content}
          </motion.div>
        </AnimatePresence>
      </motion.div>
    </div>
  )
}
