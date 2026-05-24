import React, { useState } from 'react'
import RidePayoutSummary from './RidePayoutSummary.jsx'
import RideTransparencyPanel from './RideTransparencyPanel.jsx'
import ConflictTransparencyMemory from './ConflictTransparencyMemory.jsx'
import RouteTruthDetails from './RouteTruthDetails.jsx'

/**
 * Collapsible ledger, transparency, and route-truth — keeps primary cockpit uncluttered.
 */
export default function TripTruthDetails({
  ride,
  pricing,
  pricingLocked = false,
  pricingVariant = 'ledger',
  showTransparency = false,
  showRouteProvider = false,
  conflictRideId = null,
  conflictProof = null,
  conflictLoading = false,
  conflictUnavailable = false,
  defaultOpen = false,
  title = 'Trip details',
}) {
  const [open, setOpen] = useState(defaultOpen)
  const hasConflict = conflictRideId != null
  const hasPricing = Boolean(pricing)
  const hasBody = hasPricing || showTransparency || showRouteProvider || hasConflict

  if (!hasBody) return null

  return (
    <div className="trip-truth-details" data-testid="trip-truth-details">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        data-testid="trip-truth-details-toggle"
        className="trip-truth-details__toggle cockpit-pressable"
      >
        <span>{title}</span>
        <span className="text-[#94A3B8]" aria-hidden>
          {open ? '−' : '+'}
        </span>
      </button>
      {open && (
        <div className="trip-truth-details__body space-y-2" data-testid="trip-truth-details-body">
          {showRouteProvider && (ride?.rideId ?? ride?.id) ? (
            <RouteTruthDetails rideId={ride.rideId ?? ride.id} ride={ride} embedded />
          ) : null}
          {hasPricing && (
            <RidePayoutSummary pricing={pricing} locked={pricingLocked} variant={pricingVariant} />
          )}
          {showTransparency && ride?.rideId && <RideTransparencyPanel rideId={ride.rideId} />}
          {hasConflict && (
            <ConflictTransparencyMemory
              rideId={conflictRideId}
              proof={conflictProof}
              loading={conflictLoading}
              unavailable={conflictUnavailable}
            />
          )}
        </div>
      )}
    </div>
  )
}
