import React from 'react'
import {
  buildGoogleMapsNavigationUrl,
  hasNavigationTarget,
  openExternalNavigation,
} from '../../utils/externalNavigation.js'

function ExternalNavButton({ children, onClick, testId, disabled }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className="cockpit-pressable w-full rounded-[18px] border border-white/10 bg-white/[0.06] py-2.5 text-[13px] font-semibold text-[#E2E8F0] transition-colors hover:bg-white/[0.1] disabled:cursor-not-allowed disabled:opacity-50"
    >
      {children}
    </button>
  )
}

/**
 * Launches Google Maps externally for pickup/dropoff — does not embed Google or change pricing.
 *
 * @param {{ lat?: number, lng?: number, label?: string } | null | undefined} props.pickup
 * @param {{ lat?: number, lng?: number, label?: string } | null | undefined} props.dropoff
 * @param {boolean} [props.showDestination=true]
 */
export default function ExternalNavigationButtons({ pickup, dropoff, showDestination = true }) {
  const pickupReady = hasNavigationTarget(pickup)
  const destinationReady = showDestination && hasNavigationTarget(dropoff)

  if (!pickupReady && !destinationReady) return null

  const pickupUrl = buildGoogleMapsNavigationUrl(pickup)
  const destinationUrl = buildGoogleMapsNavigationUrl(dropoff)

  return (
    <div className="space-y-2" data-testid="external-navigation-actions">
      {pickupReady && (
        <ExternalNavButton
          testId="open-pickup-google-maps"
          disabled={!pickupUrl}
          onClick={() => openExternalNavigation(pickupUrl)}
        >
          Open pickup in Google Maps
        </ExternalNavButton>
      )}
      {destinationReady && (
        <ExternalNavButton
          testId="open-destination-google-maps"
          disabled={!destinationUrl}
          onClick={() => openExternalNavigation(destinationUrl)}
        >
          Open destination in Google Maps
        </ExternalNavButton>
      )}
    </div>
  )
}
