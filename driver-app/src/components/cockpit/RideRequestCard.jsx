import React, { useEffect, useRef, useState } from 'react'
import TestRideLabel from '../TestRideLabel.jsx'
import {
  BETA_INCOMING_ESTIMATE_HINT,
  BETA_INCOMING_ESTIMATE_LABEL,
  BETA_INCOMING_RIDE_EYEBROW,
  BETA_OPEN_BOARD_DISPATCH,
} from '../../utils/betaTruthCopy.js'
import { formatCurrency } from '../../theme/halfAppTheme.js'
import { formatDistanceKm } from '../../utils/formatDistance.js'
import { useDriverPreferences } from '../../context/DriverPreferencesContext.jsx'
import ExternalNavigationButtons from './ExternalNavigationButtons.jsx'
import PrimaryRideActionButton from './PrimaryRideActionButton.jsx'

function MetaRow({ label, value }) {
  return (
    <div className="flex justify-between gap-3 text-[13px]">
      <span className="text-[var(--ha-muted)]">{label}</span>
      <span className="text-right font-medium text-[var(--ha-text)]">{value}</span>
    </div>
  )
}

function secondsRemaining(expiresAtIso, timeoutSeconds) {
  if (!expiresAtIso) return timeoutSeconds ?? 30
  const end = new Date(expiresAtIso).getTime()
  const now = Date.now()
  return Math.max(0, Math.ceil((end - now) / 1000))
}

export default function RideRequestCard({
  ride,
  loadingBackend,
  claimConflict,
  backendError,
  onAccept,
  onDecline,
}) {
  const { units } = useDriverPreferences()
  const timeoutSeconds = ride?.dispatchTimeoutSeconds ?? 30
  const [remaining, setRemaining] = useState(() =>
    secondsRemaining(ride?.dispatchExpiresAt, timeoutSeconds)
  )

  useEffect(() => {
    setRemaining(secondsRemaining(ride?.dispatchExpiresAt, timeoutSeconds))
    const timer = window.setInterval(() => {
      setRemaining(secondsRemaining(ride?.dispatchExpiresAt, timeoutSeconds))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [ride?.dispatchExpiresAt, ride?.rideId, timeoutSeconds])

  const timeoutHandled = useRef(false)
  useEffect(() => {
    timeoutHandled.current = false
  }, [ride?.rideId])
  useEffect(() => {
    if (remaining === 0 && onDecline && !timeoutHandled.current) {
      timeoutHandled.current = true
      onDecline({ reason: 'dispatch_timeout' })
    }
  }, [remaining, onDecline])

  const pickupLabel = ride?.pickup?.label || ride?.pickupLocation || 'Pickup'
  const dropoffLabel = ride?.dropoff?.label || ride?.dropoffLocation || 'Dropoff'
  const countdownClass =
    remaining <= 8 ? 'ride-request-card__countdown ride-request-card__countdown--urgent' : 'ride-request-card__countdown'

  return (
    <div className="ride-request-card" data-testid="ride-request-card">
      <div className="ride-request-card__header">
        <p className="ride-request-card__eyebrow">{BETA_INCOMING_RIDE_EYEBROW}</p>
        <div
          className={countdownClass}
          data-testid="ride-request-countdown"
          aria-live="polite"
        >
          {remaining}s
        </div>
      </div>

      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] uppercase tracking-wide text-[#AAB6C8]">Pickup</p>
          <p className="text-[18px] font-semibold leading-snug text-[#F8FAFC]" data-testid="ride-request-pickup">
            {pickupLabel}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-[10px] uppercase tracking-wide text-[#AAB6C8]">
            {BETA_INCOMING_ESTIMATE_LABEL}
          </p>
          <p className="text-[22px] font-bold leading-none" data-testid="ride-estimated-payout">
            {ride?.fareAmount == null ? 'Pending' : formatCurrency(ride.fareAmount)}
          </p>
          <p className="text-[10px] text-[#64748B]">{BETA_INCOMING_ESTIMATE_HINT}</p>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <TestRideLabel lifecycleReason={ride?.raw?.lifecycle_reason} testId="ride-request-test-label" />
      </div>

      <p className="mt-2 text-[10px] text-[#64748B]" data-testid="ride-request-open-board-note">
        {BETA_OPEN_BOARD_DISPATCH}
      </p>

      <p className="mt-2 text-[11px] uppercase tracking-wide text-[#AAB6C8]">Dropoff</p>
      <p className="text-[15px] font-medium text-[#F8FAFC]" data-testid="ride-request-dropoff">
        {dropoffLabel}
      </p>

      <div className="mt-3 rounded-[18px] border border-white/10 bg-white/[0.04] p-3 space-y-2">
        <MetaRow
          label="Distance"
          value={formatDistanceKm(Number(ride?.distance ?? 0), units)}
        />
        <MetaRow label="Duration" value={`${ride?.duration ?? 0} min`} />
      </div>

      <div className="mt-3">
        <ExternalNavigationButtons pickup={ride?.pickup} dropoff={ride?.dropoff} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <PrimaryRideActionButton
          onClick={() => onDecline?.({ reason: 'driver_declined' })}
          disabled={loadingBackend || claimConflict}
          tone="neutral"
          testId="decline-ride-btn"
        >
          Decline
        </PrimaryRideActionButton>
        <PrimaryRideActionButton
          onClick={onAccept}
          disabled={loadingBackend || claimConflict}
          tone="success"
          testId="accept-ride-btn"
        >
          Accept
        </PrimaryRideActionButton>
      </div>

      {backendError && (
        <p className="mt-2 text-center text-[12px] text-amber-300" data-testid="accept-ride-error">
          {backendError}
        </p>
      )}
    </div>
  )
}
