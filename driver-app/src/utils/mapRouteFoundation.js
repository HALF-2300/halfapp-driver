/**
 * v0.1 map route foundation — OSM/Leaflet visual only; paid providers disabled.
 */

export const V01_ROUTE_PROVIDER = 'leaflet_osm'
export const V01_TRAFFIC_PROVIDER = 'none'
export const V01_ROUTE_CONFIDENCE = 'visual_only'

/** @param {Record<string, unknown> | null | undefined} ride */
export function resolveMapRouteFoundation(ride) {
  const r = ride || {}
  return {
    routeProvider: String(r.route_provider || V01_ROUTE_PROVIDER),
    trafficProvider: String(r.traffic_provider || V01_TRAFFIC_PROVIDER),
    trafficAware: Boolean(r.traffic_aware),
    trafficSignalAware: Boolean(r.traffic_signal_aware),
    routeConfidence: r.route_confidence != null ? String(r.route_confidence) : V01_ROUTE_CONFIDENCE,
    routeCalculatedAt: r.route_calculated_at != null ? String(r.route_calculated_at) : null,
    googleMapsFallbackEnabled: Boolean(r.google_maps_fallback_enabled),
    mapboxTrafficEnabled: Boolean(r.mapbox_traffic_enabled),
  }
}

/** @param {ReturnType<typeof resolveMapRouteFoundation>} foundation */
export function externalRoutingEnabled(foundation) {
  return Boolean(foundation.googleMapsFallbackEnabled || foundation.mapboxTrafficEnabled)
}
