/**
 * v0.1 ride pricing ledger display — mirrors backend integer-cent fields for UI only.
 * Does not recalculate fare for billing; uses ride.pricing when present.
 */

export const DEFAULT_PLATFORM_SERVICE_FEE_CENTS = 150
const KM_PER_MILE = 0.621371
const US_LAUNCH_BASE_CENTS = 500
const US_LAUNCH_PER_MILE_CENTS = 150
const US_LAUNCH_PER_MINUTE_CENTS = 25
const US_LAUNCH_MIN_SHAREABLE_CENTS = 800
const COMMISSION_RATE_BPS = 2000

/** @param {unknown} cents */
export function formatCents(cents) {
  const n = Number(cents)
  if (!Number.isFinite(n)) return '—'
  return `$${(n / 100).toFixed(2)}`
}

/**
 * @param {Record<string, unknown>} ride
 * @returns {Record<string, unknown> | null}
 */
export function resolveRidePricing(ride) {
  const pricing = ride?.pricing
  if (!pricing || typeof pricing !== 'object') return null
  return pricing
}

/**
 * @param {Record<string, unknown>} ride
 * @returns {number | null} driver total payout in dollars
 */
/** @param {Record<string, unknown>} ride */
export function driverPayoutDollars(ride) {
  return getDriverTotalPayoutDollars(ride)
}

export function getDriverTotalPayoutDollars(ride) {
  const pricing = resolveRidePricing(ride)
  if (pricing) {
    const cents = Number(
      pricing.driver_total_payout_cents ?? pricing.driver_earnings_cents ?? NaN
    )
    if (Number.isFinite(cents)) return cents / 100
  }
  const legacy = Number(ride?.fare_amount)
  return Number.isFinite(legacy) ? legacy : null
}

/**
 * @param {number} driverShareable
 * @param {{ serviceFee?: number, tip?: number, city?: number, airport?: number, toll?: number, accessibility?: number }} [fees]
 */
export function computeFinancialsFromShareable(driverShareable, fees = {}) {
  const shareable = Math.max(0, Math.round(Number(driverShareable) || 0))
  const serviceFee = fees.serviceFee ?? DEFAULT_PLATFORM_SERVICE_FEE_CENTS
  const tip = Math.max(0, Math.round(fees.tip ?? 0))
  const city = Math.max(0, Math.round(fees.city ?? 0))
  const airport = Math.max(0, Math.round(fees.airport ?? 0))
  const toll = Math.max(0, Math.round(fees.toll ?? 0))
  const accessibility = Math.max(0, Math.round(fees.accessibility ?? 0))

  const platformCommission = Math.round((shareable * COMMISSION_RATE_BPS) / 10000)
  const driverRidePayout = shareable - platformCommission
  const platformRevenue = platformCommission + serviceFee
  const passThroughTotal = city + airport + toll + accessibility
  const customerTotal = shareable + serviceFee + passThroughTotal + tip
  const driverTotal = driverRidePayout + tip

  return {
    driver_shareable_fare_cents: shareable,
    platform_service_fee_cents: serviceFee,
    tip_cents: tip,
    city_fee_cents: city,
    airport_fee_cents: airport,
    toll_cents: toll,
    accessibility_fee_cents: accessibility,
    platform_commission_cents: platformCommission,
    driver_ride_payout_cents: driverRidePayout,
    driver_total_payout_cents: driverTotal,
    platform_revenue_cents: platformRevenue,
    pass_through_total_cents: passThroughTotal,
    customer_total_cents: customerTotal,
  }
}

/**
 * Estimate pricing for mock/offline rides (same launch defaults as backend v0.1).
 *
 * @param {Record<string, unknown>} ride
 * @param {{ tipCents?: number, cityFeeCents?: number, airportFeeCents?: number, tollCents?: number, accessibilityFeeCents?: number }} [opts]
 */
export function buildMockPricingViewForRide(ride, opts = { lock: true }) {
  const distanceKm = Number(ride.distance_km ?? ride.distance ?? 0)
  const durationMinutes = Number(ride.duration_minutes ?? ride.duration ?? 0)
  const miles = Math.max(0, distanceKm) * KM_PER_MILE
  const distanceFare = Math.round(miles * US_LAUNCH_PER_MILE_CENTS)
  const timeFare = Math.max(0, durationMinutes) * US_LAUNCH_PER_MINUTE_CENTS
  const shareable = Math.max(
    US_LAUNCH_BASE_CENTS + distanceFare + timeFare,
    US_LAUNCH_MIN_SHAREABLE_CENTS
  )
  const breakdown = computeFinancialsFromShareable(shareable, {
    tip: opts.tipCents ?? 0,
    city: opts.cityFeeCents ?? 0,
    airport: opts.airportFeeCents ?? 0,
    toll: opts.tollCents ?? 0,
    accessibility: opts.accessibilityFeeCents ?? 0,
  })
  const lockedAt = new Date().toISOString()
  return {
    pricing_policy_id: 'us-launch-v0-1',
    pricing_version: 'v0.1',
    market_id: 'US-DEFAULT',
    base_fare_cents: US_LAUNCH_BASE_CENTS,
    distance_fare_cents: distanceFare,
    time_fare_cents: timeFare,
    wait_fee_cents: 0,
    ...breakdown,
    tax_cents: 0,
    driver_commission_cents: breakdown.driver_ride_payout_cents,
    driver_earnings_cents: breakdown.driver_total_payout_cents,
    platform_earnings_cents: breakdown.platform_revenue_cents,
    total_rider_charge_cents: breakdown.customer_total_cents,
    financial_locked: opts.lock !== false,
    locked_at: opts.lock !== false ? lockedAt : null,
    fare_locked_at: opts.lock !== false ? lockedAt : null,
  }
}

/**
 * @param {Record<string, unknown> | null | undefined} pricing
 */
export function buildDriverEarningsRows(pricing) {
  if (!pricing) return null
  return {
    statusLabel: 'Completed',
    rows: [
      { label: 'Driver ride payout', value: formatCents(pricing.driver_ride_payout_cents), testId: 'driver-ride-payout' },
      { label: 'Tips', value: formatCents(pricing.tip_cents ?? 0), testId: 'driver-tips', hint: 'Tips are not commissioned' },
      {
        label: 'Driver total payout',
        value: formatCents(pricing.driver_total_payout_cents ?? pricing.driver_earnings_cents),
        testId: 'driver-total-payout',
        emphasize: true,
      },
      {
        label: 'Financial lock',
        value: pricing.financial_locked ? 'Locked' : 'Unlocked',
        testId: 'financial-lock-status',
      },
      ...(pricing.locked_at
        ? [{ label: 'Locked at', value: String(pricing.locked_at), testId: 'financial-locked-at' }]
        : []),
    ],
  }
}

/**
 * @param {Record<string, unknown> | null | undefined} pricing
 */
export function buildRiderReceiptRows(pricing) {
  if (!pricing) return null
  const passThroughRows = []
  if (Number(pricing.city_fee_cents) > 0) {
    passThroughRows.push({ label: 'City fee (pass-through)', value: formatCents(pricing.city_fee_cents) })
  }
  if (Number(pricing.airport_fee_cents) > 0) {
    passThroughRows.push({ label: 'Airport fee (pass-through)', value: formatCents(pricing.airport_fee_cents) })
  }
  if (Number(pricing.toll_cents) > 0) {
    passThroughRows.push({ label: 'Toll (pass-through)', value: formatCents(pricing.toll_cents) })
  }
  if (Number(pricing.accessibility_fee_cents) > 0) {
    passThroughRows.push({
      label: 'Accessibility fee (pass-through)',
      value: formatCents(pricing.accessibility_fee_cents),
    })
  }

  return {
    title: 'Customer receipt (ledger)',
    rows: [
      {
        label: 'Ride fare',
        value: formatCents(pricing.driver_shareable_fare_cents),
        testId: 'rider-ride-fare',
        hint: 'Driver-shareable fare before commission split',
      },
      {
        label: 'Platform service fee',
        value: formatCents(pricing.platform_service_fee_cents ?? DEFAULT_PLATFORM_SERVICE_FEE_CENTS),
        testId: 'rider-platform-service-fee',
      },
      ...passThroughRows.map((row, i) => ({ ...row, testId: `rider-pass-through-${i}` })),
      {
        label: 'Tips',
        value: formatCents(pricing.tip_cents ?? 0),
        testId: 'rider-tips',
        hint: 'Paid to driver; not included in platform commission',
      },
      {
        label: 'Customer total',
        value: formatCents(pricing.customer_total_cents ?? pricing.total_rider_charge_cents),
        testId: 'rider-customer-total',
        emphasize: true,
      },
      {
        label: 'Platform commission',
        value: formatCents(pricing.platform_commission_cents),
        testId: 'rider-platform-commission',
        hint: 'Commission applies to ride fare only, not pass-through fees or tips',
      },
    ],
  }
}

/**
 * @param {Record<string, unknown> | null | undefined} pricing
 */
export function buildPricingLedgerDebugRows(pricing) {
  if (!pricing) return null
  return [
    { label: 'driver_shareable_fare_cents', value: String(pricing.driver_shareable_fare_cents ?? '—') },
    { label: 'platform_commission_cents', value: String(pricing.platform_commission_cents ?? '—') },
    { label: 'platform_service_fee_cents', value: String(pricing.platform_service_fee_cents ?? '—') },
    { label: 'platform_revenue_cents', value: String(pricing.platform_revenue_cents ?? pricing.platform_earnings_cents ?? '—') },
    { label: 'driver_total_payout_cents', value: String(pricing.driver_total_payout_cents ?? pricing.driver_earnings_cents ?? '—') },
    { label: 'customer_total_cents', value: String(pricing.customer_total_cents ?? pricing.total_rider_charge_cents ?? '—') },
    { label: 'financial_locked', value: String(Boolean(pricing.financial_locked)) },
    { label: 'locked_at', value: String(pricing.locked_at ?? '—') },
  ]
}

/**
 * Documents ambiguous legacy API fields for diagnostics copy.
 *
 * @param {Record<string, unknown>} ride
 */
export function describeLegacyFareFields(ride) {
  const notes = []
  if (ride.fare_amount != null) {
    notes.push(
      'fare_amount on RideDriverView is driver total payout (dollars), not customer fare — label as driver earnings in UI.'
    )
  }
  notes.push('fare_earned on CompleteRideResponse is driver earnings (dollars), not customer fare.')
  return notes
}
