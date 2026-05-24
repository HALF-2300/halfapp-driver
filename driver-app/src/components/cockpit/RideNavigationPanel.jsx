import React, { useCallback, useEffect, useState } from 'react'
import driverAPI from '../../utils/api.js'
import { openExternalNavigation } from '../../utils/externalNavigation.js'

export default function RideNavigationPanel({ rideId, lifecycleStage, onConnectivityRestore }) {
  const [nav, setNav] = useState(null)
  const [error, setError] = useState(null)

  const loadNavigation = useCallback(() => {
    if (!rideId) return undefined
    let cancelled = false
    driverAPI
      .getRideNavigation(rideId)
      .then((data) => {
        if (!cancelled) {
          setNav(data)
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'Navigation unavailable')
      })
    return () => {
      cancelled = true
    }
  }, [rideId])

  useEffect(() => loadNavigation(), [loadNavigation, lifecycleStage])

  useEffect(() => {
    const onOnline = () => {
      if (typeof onConnectivityRestore === 'function') {
        onConnectivityRestore()
      }
      loadNavigation()
    }
    window.addEventListener('online', onOnline)
    return () => window.removeEventListener('online', onOnline)
  }, [loadNavigation, onConnectivityRestore])

  return (
    <div className="ha-card p-3" data-testid="ride-navigation-panel">
      <div className="text-sm font-semibold">Navigation</div>
      {error ? <p className="text-xs mt-2 text-amber-300">{error}</p> : null}
      {nav ? (
        <>
          <p className="text-xs ha-truth-note mt-1">{nav.note}</p>
          <p className="text-sm mt-2">
            {nav.leg === 'dropoff' ? 'Heading to' : 'Navigate to'}:{' '}
            <span className="font-medium">{nav.destination_label}</span>
          </p>
          {nav.distance_meters != null ? (
            <p className="text-xs ha-truth-note mt-1">
              Route snapshot: {Math.round(nav.distance_meters)} m
              {nav.route_provider ? ` · ${nav.route_provider}` : ''}
              {nav.used_fallback ? ' · estimate/fallback' : ''}
            </p>
          ) : null}
          {nav.external_url ? (
            <button
              type="button"
              className="ha-btn ha-btn--primary mt-3 w-full"
              data-testid="ride-navigation-open-maps"
              onClick={() => openExternalNavigation(nav.external_url)}
            >
              Open in Maps
            </button>
          ) : null}
          {nav.steps?.length > 0 ? (
            <ol className="mt-3 space-y-1 text-xs list-decimal list-inside">
              {nav.steps.slice(0, 5).map((step, i) => (
                <li key={i}>{step.instruction || step}</li>
              ))}
            </ol>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
