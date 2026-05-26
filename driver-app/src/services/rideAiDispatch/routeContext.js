import { ROUTE_ADVISORY_LABEL } from './constants.js'

/** @typedef {'none' | 'osrm' | 'mapbox' | 'google' | 'here'} RouteProviderId */

/**
 * @typedef {Object} RouteContext
 * @property {RouteProviderId} provider
 * @property {boolean} live
 * @property {string} advisoryLabel
 * @property {number | null} distanceKm
 * @property {number | null} durationMinutes
 * @property {number | null} distanceMeters
 * @property {number | null} durationSeconds
 * @property {string | null} evidenceSummary
 * @property {string | null} validatedAt
 * @property {string | null} routeSource
 * @property {number | null} routeProviderConfidence
 * @property {boolean} usedFallback
 */

/**
 * @param {Record<string, unknown> | null | undefined} ride
 * @returns {Record<string, unknown>}
 */
export function normalizeRideRouteFields(ride) {
  const r = ride || {}
  const distanceKm =
    r.distance_km != null
      ? Number(r.distance_km)
      : r.distance != null
        ? Number(r.distance)
        : null
  const durationMinutes =
    r.duration_minutes != null
      ? Number(r.duration_minutes)
      : r.duration != null
        ? Number(r.duration)
        : null
  return {
    ...r,
    distance_km: distanceKm,
    duration_minutes: durationMinutes,
    route_provider: r.route_provider ?? null,
    route_calculated_at: r.route_calculated_at ?? null,
    route_source: r.route_source ?? null,
    route_used_fallback: r.route_used_fallback ?? null,
    route_provider_confidence: r.route_provider_confidence ?? null,
    route_confidence: r.route_confidence ?? null,
  }
}

/**
 * @param {string | null | undefined} routeProvider
 * @param {boolean} usedFallback
 * @returns {RouteProviderId}
 */
function mapRouteProvider(routeProvider, usedFallback) {
  if (usedFallback) return 'none'
  const provider = String(routeProvider || '').toLowerCase()
  if (provider.includes('osrm')) return 'osrm'
  if (provider.includes('mapbox')) return 'mapbox'
  if (provider.includes('google')) return 'google'
  if (provider.includes('here')) return 'here'
  return 'none'
}

/**
 * @param {Record<string, unknown>} normalized
 * @returns {boolean}
 */
function isOsrmGrounded(normalized) {
  const provider = String(normalized.route_provider || '').toLowerCase()
  const usedFallback = normalized.route_used_fallback === true || provider.includes('haversine')
  return provider.includes('osrm') && !usedFallback
}

/**
 * @param {Object} [input]
 * @param {RouteProviderId} [input.provider]
 * @param {boolean} [input.live]
 * @param {number | null} [input.distanceKm]
 * @param {number | null} [input.durationMinutes]
 * @param {number | null} [input.distanceMeters]
 * @param {number | null} [input.durationSeconds]
 * @param {string | null} [input.evidenceSummary]
 * @param {string | null} [input.validatedAt]
 * @param {string | null} [input.routeSource]
 * @param {number | null} [input.routeProviderConfidence]
 * @param {boolean} [input.usedFallback]
 * @returns {RouteContext}
 */
export function createRouteContext(input = {}) {
  const provider = input.provider || 'none'
  const live = Boolean(input.live && provider !== 'none' && !input.usedFallback)
  return {
    provider,
    live,
    advisoryLabel: live ? '' : ROUTE_ADVISORY_LABEL,
    distanceKm: input.distanceKm ?? null,
    durationMinutes: input.durationMinutes ?? null,
    distanceMeters: input.distanceMeters ?? null,
    durationSeconds: input.durationSeconds ?? null,
    evidenceSummary: input.evidenceSummary ?? null,
    validatedAt: input.validatedAt ?? null,
    routeSource: input.routeSource ?? null,
    routeProviderConfidence: input.routeProviderConfidence ?? null,
    usedFallback: Boolean(input.usedFallback),
  }
}

/**
 * @param {Record<string, unknown> | null | undefined} ride
 * @returns {RouteContext}
 */
export function routeContextFromRide(ride) {
  if (!ride) return createRouteContext()
  const normalized = normalizeRideRouteFields(ride)
  const providerRaw = String(normalized.route_provider || '')
  const usedFallback =
    normalized.route_used_fallback === true || providerRaw.toLowerCase().includes('haversine')
  const mapped = mapRouteProvider(providerRaw, usedFallback)
  const distanceKm = normalized.distance_km
  const durationMinutes = normalized.duration_minutes
  const hasEvidence =
    normalized.route_calculated_at != null &&
    (distanceKm != null || durationMinutes != null)
  const osrmGrounded = isOsrmGrounded(normalized)
  const live = osrmGrounded && hasEvidence
  const routeSource =
    normalized.route_source != null
      ? String(normalized.route_source)
      : osrmGrounded
        ? 'osrm_v5'
        : mapped !== 'none'
          ? mapped
          : null
  const confidence =
    normalized.route_provider_confidence != null
      ? Number(normalized.route_provider_confidence)
      : live
        ? 0.91
        : null
  const distanceMeters =
    distanceKm != null && Number.isFinite(distanceKm) ? Math.round(distanceKm * 1000) : null
  const durationSeconds =
    durationMinutes != null && Number.isFinite(durationMinutes)
      ? Math.round(durationMinutes * 60)
      : null

  return createRouteContext({
    provider: mapped,
    live,
    usedFallback,
    distanceKm: distanceKm != null && Number.isFinite(distanceKm) ? distanceKm : null,
    durationMinutes:
      durationMinutes != null && Number.isFinite(durationMinutes) ? durationMinutes : null,
    distanceMeters,
    durationSeconds,
    evidenceSummary: live
      ? `OSRM road-network route (${providerRaw})`
      : hasEvidence
        ? `Route metadata (${providerRaw || 'unknown'}; not OSRM-grounded)`
        : null,
    validatedAt: normalized.route_calculated_at ? String(normalized.route_calculated_at) : null,
    routeSource,
    routeProviderConfidence: confidence,
  })
}

/**
 * @param {RouteContext} ctx
 * @returns {string}
 */
export function formatRouteContextForPrompt(ctx) {
  return JSON.stringify(
    {
      provider: ctx.provider,
      route_source: ctx.routeSource,
      route_calculated_at: ctx.validatedAt,
      route_provider_confidence: ctx.routeProviderConfidence,
      live_traffic: ctx.live,
      advisory_label: ctx.advisoryLabel || null,
      distance_km: ctx.distanceKm,
      distance_meters: ctx.distanceMeters,
      duration_minutes: ctx.durationMinutes,
      duration_seconds: ctx.durationSeconds,
      route_used_fallback: ctx.usedFallback,
      evidence: ctx.evidenceSummary,
      validated_at: ctx.validatedAt,
      instruction: ctx.live
        ? 'Summarize only the grounded route context above. Do not invent traffic incidents.'
        : 'No live traffic source. Provide general advisory only; never claim live traffic conditions.',
    },
    null,
    2,
  )
}

/**
 * @param {RouteContext} ctx
 * @param {string} [aiText]
 * @returns {string}
 */
export function formatRouteNoteForDisplay(ctx, aiText = '') {
  const prefix = ctx.live ? '' : `${ROUTE_ADVISORY_LABEL}\n`
  return `${prefix}${aiText}`.trim()
}
