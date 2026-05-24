import React from 'react'
import TruthBadge from './TruthBadge.jsx'
import AgentBriefGenerator from './AgentBriefGenerator.jsx'
import HalfAppEngineerPanel from './HalfAppEngineerPanel.jsx'
import {
  GEOLOCATION_STATES,
  geolocationDiagnosticMessage,
} from '../../utils/locationTruth.js'
import {
  mapLocationDiagnosticLabel,
  MAP_CENTER_SOURCES,
} from '../../utils/mapCenterPresentation.js'
import RidePricingBreakdown from './RidePricingBreakdown.jsx'
import { describeLegacyFareFields } from '../../utils/ridePricingDisplay.js'

const SHOWCASE_PROOF_POINTS = [
  'Backend presence: live',
  'Marketplace truth: backend-owned',
  'Ride visibility: audited',
]

export default function DiagnosticsDrawer({
  open,
  onClose,
  geoStatus,
  geoUsingFallback,
  geoAccuracyMeters,
  devicePosition,
  centerSource,
  isDev,
  allowSimulation,
  loadingBackend,
  backendError,
  onRefresh,
  onCreateSimulationRide,
  canSimulate,
  lastCompletedRide,
  authToken,
}) {
  if (!open) return null

  const locationDiagnostic = geolocationDiagnosticMessage(geoStatus, {
    usingFallback: geoUsingFallback,
    isDev,
    accuracyMeters: geoAccuracyMeters ?? undefined,
    capturedAtMs: devicePosition?.capturedAt,
  })
  const mapSourceDiagnostic = mapLocationDiagnosticLabel(centerSource ?? MAP_CENTER_SOURCES.NONE)

  return (
    <div
      className="absolute left-[18px] right-[18px] top-[88px] z-[25] max-h-[min(50vh,360px)] overflow-y-auto diagnostics-drawer-panel p-3 shadow-2xl"
      data-testid="diagnostics-drawer"
    >
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-[13px] font-semibold text-[#F8FAFC]">Advanced / Diagnostics</h2>
        <button
          type="button"
          onClick={onClose}
          className="cockpit-pressable rounded-full px-2 py-1 text-[11px] text-[#AAB6C8]"
        >
          Close
        </button>
      </div>
      <ul className="mb-3 space-y-1 text-[11px] text-[#AAB6C8]">
        {SHOWCASE_PROOF_POINTS.map((line) => (
          <li key={line}>{line}</li>
        ))}
        <li>No ETA guarantee</li>
        <li>No route guarantee</li>
        <li data-testid="diagnostics-fleet-traffic-copy">
          Fleet traffic heat: aggregated HalfApp driver speeds (no TomTom/Mapbox key)
        </li>
        <li data-testid="diagnostics-map-source-copy">{mapSourceDiagnostic}</li>
        <li data-testid="diagnostics-location-copy">{locationDiagnostic}</li>
        {isDev && <li>Dev mode active</li>}
        {geoUsingFallback && <li>Dev fallback location active</li>}
        {Number.isFinite(geoAccuracyMeters) && (
          <li data-testid="diagnostics-accuracy-meters">Accuracy: {Math.round(geoAccuracyMeters)}m</li>
        )}
        {devicePosition?.capturedAt && (
          <li data-testid="diagnostics-captured-at">
            Captured: {new Date(devicePosition.capturedAt).toISOString()}
          </li>
        )}
      </ul>
      <div className="flex flex-wrap gap-1.5" data-testid="cockpit-truth-labels">
        <TruthBadge kind="BACKEND_OWNED" />
        <TruthBadge kind="DISPATCH_BACKEND_OWNED" />
        <TruthBadge kind="EXPERIMENTAL">Experimental map</TruthBadge>
        <TruthBadge kind="NO_ROUTE_SNAPSHOT" />
        <TruthBadge kind="NO_FARE_QUOTE">No ETA guarantee</TruthBadge>
        <TruthBadge kind="DEVICE_LOCATION">Device location on map only</TruthBadge>
        {geoUsingFallback && <TruthBadge kind="DEV_FIXTURE">DEV FALLBACK LOCATION</TruthBadge>}
        {geoStatus === GEOLOCATION_STATES.ALLOWED && (
          <TruthBadge kind="DEVICE_LOCATION">Not backend dispatch truth</TruthBadge>
        )}
      </div>
      {geoUsingFallback && (
        <p
          className="mt-2 rounded-lg border border-amber-500/30 bg-amber-950/50 px-2 py-1 text-[10px] text-amber-200"
          data-testid="diagnostics-dev-fallback-banner"
        >
          DEV FALLBACK LOCATION — not real driver GPS
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onRefresh}
          disabled={loadingBackend}
          data-testid="sync-marketplace-btn"
          className="cockpit-pressable rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-[12px] font-medium text-[#F8FAFC] disabled:opacity-50"
        >
          ↻ Sync
        </button>
        {allowSimulation && (
          <button
            type="button"
            onClick={onCreateSimulationRide}
            disabled={!canSimulate || loadingBackend}
            data-testid="diagnostics-dev-ride-btn"
            className="cockpit-pressable rounded-full border border-amber-400/40 bg-amber-500/20 px-3 py-1.5 text-[12px] font-medium text-amber-100 disabled:opacity-50"
          >
            DEV · Create ride
          </button>
        )}
      </div>
      {lastCompletedRide?.pricing && (
        <div className="mt-3 space-y-2">
          <RidePricingBreakdown variant="debug" ride={lastCompletedRide.raw ?? lastCompletedRide} />
          <ul className="space-y-1 text-[10px] text-[#64748B]" data-testid="legacy-fare-field-notes">
            {describeLegacyFareFields(lastCompletedRide.raw ?? {}).map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      )}
      {import.meta.env.DEV && (
        <>
          <HalfAppEngineerPanel authToken={authToken} />
          <AgentBriefGenerator activeSurface="driver cockpit / MapHome (#/)" />
        </>
      )}
      {backendError && (
        <p className="mt-2 text-[11px] text-amber-300" data-testid="diagnostics-backend-error">
          {backendError}
        </p>
      )}
    </div>
  )
}
