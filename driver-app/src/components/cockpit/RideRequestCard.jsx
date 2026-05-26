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
  const expired = remaining === 0
  const urgent = remaining <= 8

  const countdownClass = urgent
    ? 'ride-request-card__countdown ride-request-card__countdown--urgent'
    : 'ride-request-card__countdown'

  const countdownPct = Math.max(0, Math.round((remaining / timeoutSeconds) * 100))

  return (
    <div className="ride-request-card" data-testid="ride-request-card">

      {/* Row 1: eyebrow + countdown */}
      <div className="ride-request-card__header">
        <p className="ride-request-card__eyebrow">{BETA_INCOMING_RIDE_EYEBROW}</p>
        <div
          className={countdownClass}
          data-testid="ride-request-countdown"
          aria-live="polite"
        >
          {expired ? 'Expired' : `${remaining}s`}
        </div>
      </div>

      {/* Row 2: fare + trip meta */}
      <div className="flex items-end justify-between gap-3 mb-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.1em]" style={{ color: 'var(--ha-muted)' }}>
            {BETA_INCOMING_ESTIMATE_LABEL}
          </p>
          <p
            className="text-[30px] font-bold leading-none mt-0.5 tabular-nums"
            style={{ color: 'var(--ha-text)' }}
            data-testid="ride-estimated-payout"
          >
            {ride?.fareAmount == null ? '—' : formatCurrency(ride.fareAmount)}
          </p>
          <p className="text-[10px] mt-1" style={{ color: '#64748B' }}>
            {BETA_INCOMING_ESTIMATE_HINT}
          </p>
          <p className="text-[10px] mt-0.5" style={{ color: '#64748B' }}>
            Manual operations required · recorded only
          </p>
        </div>
        <div className="text-right shrink-0">
          <div
            className="rounded-[14px] border px-3 py-2"
            style={{ borderColor: 'var(--ha-border)', background: 'rgba(255,255,255,0.04)' }}
          >
            <p className="text-[18px] font-bold leading-none tabular-nums" style={{ color: 'var(--ha-text)' }}>
              {formatDistanceKm(Number(ride?.distance ?? 0), units)}
            </p>
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--ha-muted)' }}>
              {ride?.duration ?? 0} min
            </p>
          </div>
        </div>
      </div>

      {/* Timer progress bar */}
      {!expired && (
        <div
          className="mb-3 h-[3px] w-full rounded-full overflow-hidden"
          style={{ background: 'rgba(255,255,255,0.08)' }}
        >
          <div
            className="h-full rounded-full transition-all duration-1000"
            style={{
              width: `${countdownPct}%`,
              background: urgent
                ? 'linear-gradient(90deg, #fb7185, #f43f5e)'
                : 'linear-gradient(90deg, #3b82f6, #22d3ee)',
            }}
          />
        </div>
      )}

      {/* Route visual */}
      <div className="ride-request-route mb-3">
        <div className="ride-request-route__stop">
          <div className="ride-request-route__dot ride-request-route__dot--pickup" />
          <div className="min-w-0 flex-1">
            <p className="text-[10px] uppercase tracking-wide font-semibold" style={{ color: 'var(--ha-muted)' }}>Pickup</p>
            <p
              className="text-[15px] font-semibold leading-snug"
              style={{ color: 'var(--ha-text)' }}
              data-testid="ride-request-pickup"
            >
              {pickupLabel}
            </p>
          </div>
        </div>
        <div className="ride-request-route__line" />
        <div className="ride-request-route__stop">
          <div className="ride-request-route__dot ride-request-route__dot--dropoff" />
          <div className="min-w-0 flex-1">
            <p className="text-[10px] uppercase tracking-wide font-semibold" style={{ color: 'var(--ha-muted)' }}>Dropoff</p>
            <p
              className="text-[15px] font-medium leading-snug"
              style={{ color: 'var(--ha-text)' }}
              data-testid="ride-request-dropoff"
            >
              {dropoffLabel}
            </p>
          </div>
        </div>
      </div>

      {/* Test label + open board note */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <TestRideLabel lifecycleReason={ride?.raw?.lifecycle_reason} testId="ride-request-test-label" />
      </div>
      <p
        className="text-[10px] mb-2"
        style={{ color: '#64748B' }}
        data-testid="ride-request-open-board-note"
      >
        {BETA_OPEN_BOARD_DISPATCH}
      </p>
      <p className="text-[10px] mb-3" style={{ color: '#64748B' }}>
        Payment status: Manual operations required
      </p>

      {/* Accept / Decline */}
      <div className="grid grid-cols-2 gap-3">
        <PrimaryRideActionButton
          onClick={() => onDecline?.({ reason: 'driver_declined' })}
          disabled={loadingBackend || claimConflict || expired}
          tone="neutral"
          testId="decline-ride-btn"
        >
          {expired ? 'Expired' : 'Decline'}
        </PrimaryRideActionButton>
        <PrimaryRideActionButton
          onClick={onAccept}
          disabled={loadingBackend || claimConflict || expired}
          tone="success"
          testId="accept-ride-btn"
        >
          {expired ? 'Offer expired' : 'Accept'}
        </PrimaryRideActionButton>
      </div>

      <p className="mt-2 text-center text-[11px]" style={{ color: '#94a3b8' }}>
        Accept claims the job if it is still available. Decline keeps you online.
      </p>

      {/* Navigation stays available, but the claim decision remains first. */}
      <div className="mt-3">
        <ExternalNavigationButtons pickup={ride?.pickup} dropoff={ride?.dropoff} compact />
      </div>

      {expired && (
        <p className="mt-2 text-center text-[12px] text-amber-300" data-testid="ride-offer-expired">
          Offer expired. Syncing the open board.
        </p>
      )}
      {claimConflict && (
        <p className="mt-2 text-center text-[12px] text-amber-300" data-testid="ride-offer-conflict">
          Another driver already took this job.
        </p>
      )}
      {backendError && (
        <p className="mt-2 text-center text-[12px] text-amber-300" data-testid="accept-ride-error">
          {backendError}
        </p>
      )}
    </div>
  )
}
