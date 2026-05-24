import React, { useCallback, useEffect, useState } from 'react'
import driverAPI from '../../utils/api.js'
import { resolveMapRouteFoundation } from '../../utils/mapRouteFoundation.js'
import {
  betaRouteEstimateNote,
  betaRoutingLabelFromPayload,
} from '../../utils/betaTruthCopy.js'
import {
  formatDurationSeconds,
  isFallbackProvider,
  osrmStatusLabel,
} from '../../utils/routeTruthFormat.js'
import { formatDistanceMeters } from '../../utils/formatDistance.js'
import { useDriverPreferences } from '../../context/DriverPreferencesContext.jsx'

function Row({ label, value, testId }) {
  return (
    <div className="flex justify-between gap-2 text-[11px]" data-testid={testId}>
      <span className="text-[var(--ha-muted)]">{label}</span>
      <span className="max-w-[58%] text-right font-medium text-[var(--ha-text)]">{value ?? '—'}</span>
    </div>
  )
}

function formatWhen(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/**
 * Collapsed route truth + snapshot list (read-only). No map, no navigation engine.
 */
export default function RouteTruthDetails({
  rideId,
  ride = null,
  defaultOpen = false,
  embedded = false,
}) {
  const { units } = useDriverPreferences()
  const [open, setOpen] = useState(defaultOpen)
  const [technicalOpen, setTechnicalOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [payload, setPayload] = useState(null)

  const load = useCallback(async () => {
    if (!rideId) return
    setLoading(true)
    setError(null)
    try {
      const data = await driverAPI.getRideRouteSnapshots(rideId)
      setPayload(data || null)
    } catch (err) {
      setPayload(null)
      setError(err?.message || 'Could not load route snapshots')
    } finally {
      setLoading(false)
    }
  }, [rideId])

  useEffect(() => {
    if (open && rideId && !payload && !loading && !error) {
      load()
    }
  }, [open, rideId, payload, loading, error, load])

  const foundation = ride ? resolveMapRouteFoundation(ride) : null
  const routeTruth = payload?.route_truth
  const snapshots = payload?.snapshots || []
  const usedFallback =
    routeTruth?.used_fallback ?? isFallbackProvider(foundation?.routeProvider)
  const provider =
    routeTruth?.current_provider ?? foundation?.routeProvider ?? '—'
  const routingLabel = payload
    ? betaRoutingLabelFromPayload(payload)
    : usedFallback
      ? betaRoutingLabelFromPayload({ route_truth: { used_fallback: true } })
      : provider

  const wrapperClass = embedded ? '' : 'rounded-[18px] border border-white/10 bg-white/[0.03]'

  return (
    <div className={wrapperClass} data-testid="route-truth-details">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        data-testid="route-truth-details-toggle"
        className="cockpit-pressable flex w-full items-center justify-between px-3 py-2.5 text-left text-[12px] font-semibold text-[var(--ha-text)]"
      >
        Route truth
        <span className="text-[var(--ha-muted)]">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-white/10 px-3 py-2.5" data-testid="route-truth-details-body">
          {loading ? <p className="text-[11px] text-[var(--ha-muted)]">Loading route snapshots…</p> : null}
          {error ? <p className="text-[11px] text-amber-200">{error}</p> : null}

          <Row label="Routing label" value={routingLabel} testId="route-truth-routing-label" />
          <Row
            label="Provider"
            value={provider}
            testId={embedded ? 'trip-route-provider-value' : 'route-truth-provider'}
          />
          <Row
            label="Fallback"
            value={usedFallback ? 'Yes' : 'No'}
            testId="route-truth-fallback"
          />
          <Row
            label="OSRM status"
            value={payload ? osrmStatusLabel(payload) : 'OSRM runtime not proved'}
            testId="route-truth-osrm-status"
          />

          {usedFallback ? (
            <p className="text-[10px] text-amber-200/90" data-testid="route-truth-estimate-note">
              {betaRouteEstimateNote(payload) ||
                betaRouteEstimateNote({ route_truth: { used_fallback: true } })}
            </p>
          ) : null}

          {snapshots.length > 0 ? (
            <ul className="space-y-2" data-testid="route-truth-snapshot-list">
              {snapshots.map((snap) => (
                <li
                  key={snap.id ?? `${snap.snapshot_role}-${snap.created_at}`}
                  className="rounded-lg border border-white/10 px-2 py-1.5 text-[11px]"
                  data-testid="route-truth-snapshot-row"
                >
                  <div className="flex justify-between gap-2 font-medium">
                    <span data-testid="route-truth-snapshot-role">{snap.snapshot_role}</span>
                    <span className="text-cyan-200">{snap.route_provider}</span>
                  </div>
                  <div className="mt-1 text-[var(--ha-muted)]">
                    {formatDistanceMeters(snap.distance_meters, units)} ·{' '}
                    {formatDurationSeconds(snap.duration_seconds)}
                    {snap.used_fallback ? ' · fallback' : ''}
                  </div>
                </li>
              ))}
            </ul>
          ) : !loading && !error ? (
            <p className="text-[10px] text-[var(--ha-muted)]/80">No route snapshots stored for this ride yet.</p>
          ) : null}

          {(snapshots.length > 0 || routeTruth) && (
            <div data-testid="route-truth-technical">
              <button
                type="button"
                onClick={() => setTechnicalOpen((v) => !v)}
                aria-expanded={technicalOpen}
                data-testid="route-truth-technical-toggle"
                className="cockpit-pressable flex w-full items-center justify-between text-[11px] text-[var(--ha-muted)]"
              >
                Technical proof
                <span>{technicalOpen ? '−' : '+'}</span>
              </button>
              {technicalOpen ? (
                <div className="mt-2 space-y-2 text-[10px] text-[var(--ha-muted)]/80" data-testid="route-truth-technical-body">
                  {snapshots.map((snap) => (
                    <div key={`tech-${snap.id}`} data-testid="route-truth-snapshot-tech-row">
                      <div data-testid="route-truth-snapshot-id">
                        snapshot #{snap.id} · {snap.snapshot_role} ·{' '}
                        <span data-testid="route-truth-snapshot-timestamp">{formatWhen(snap.created_at)}</span>
                      </div>
                      {snap.geometry_hash ? (
                        <div data-testid="route-truth-geometry-hash">
                          geometry_hash: {snap.geometry_hash.slice(0, 16)}…
                        </div>
                      ) : null}
                      {snap.request_hash ? (
                        <div data-testid="route-truth-request-hash">
                          request_hash: {snap.request_hash.slice(0, 12)}…
                        </div>
                      ) : null}
                    </div>
                  ))}
                  {routeTruth?.production_routing_claim ? (
                    <div data-testid="route-truth-production-claim">
                      production_routing_claim: {routeTruth.production_routing_claim}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
