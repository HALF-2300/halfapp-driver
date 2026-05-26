import {
  DEMO_DRIVER_SHARE_BPS,
  DEMO_FLOOR_CENTS,
  FARE_SOURCE_DEMO,
  FARE_SOURCE_LEDGER,
} from './constants.js'

/**
 * @typedef {Object} FareBreakdown
 * @property {number} grossFareCents
 * @property {number} platformCutCents
 * @property {number} driverPayoutCents
 * @property {string} status
 * @property {string} currency
 * @property {'LEDGER' | 'DEMO_SIMULATION'} source
 * @property {string} [receiptId]
 * @property {string} [capturedAt]
 * @property {string} label
 */

/**
 * @typedef {Object} TripRecord
 * @property {number} rideId
 * @property {'LEDGER' | 'DEMO_SIMULATION'} source
 * @property {FareBreakdown} fare
 * @property {Record<string, unknown>} [receipt]
 */

/**
 * Build ledger-backed trip record from GET /drivers/rides/{id}/payment.
 * @param {number} rideId
 * @param {Record<string, unknown> | null | undefined} payment
 * @returns {TripRecord | null}
 */
export function tripRecordFromLedgerPayment(rideId, payment) {
  if (!payment || payment.amount_cents == null) return null
  const gross = Number(payment.amount_cents) || 0
  const driverPayout = Number(payment.driver_payout_cents) || 0
  const platformCut = Math.max(0, gross - driverPayout)
  return {
    rideId,
    source: FARE_SOURCE_LEDGER,
    fare: {
      grossFareCents: gross,
      platformCutCents: platformCut,
      driverPayoutCents: driverPayout,
      status: String(payment.status || 'unknown'),
      currency: String(payment.currency || 'USD'),
      source: FARE_SOURCE_LEDGER,
      receiptId: payment.id != null ? `payment-${payment.id}` : undefined,
      capturedAt: payment.captured_at || undefined,
      label: 'Ledger-backed (ride_payments)',
    },
    receipt: {
      ride_id: rideId,
      payment_id: payment.id,
      status: payment.status,
      amount_cents: gross,
      driver_payout_cents: driverPayout,
      authorized_at: payment.authorized_at,
      captured_at: payment.captured_at,
    },
  }
}

/**
 * Static demo fare — explicitly labeled; no ticker / invented production money.
 * @param {number} rideId
 * @param {number} [grossFareCents]
 * @returns {TripRecord}
 */
export function tripRecordDemoSimulation(rideId, grossFareCents = DEMO_FLOOR_CENTS) {
  const gross = Math.max(DEMO_FLOOR_CENTS, Number(grossFareCents) || DEMO_FLOOR_CENTS)
  const driverPayout = Math.round((gross * DEMO_DRIVER_SHARE_BPS) / 10000)
  const platformCut = gross - driverPayout
  return {
    rideId,
    source: FARE_SOURCE_DEMO,
    fare: {
      grossFareCents: gross,
      platformCutCents: platformCut,
      driverPayoutCents: driverPayout,
      status: 'demo',
      currency: 'USD',
      source: FARE_SOURCE_DEMO,
      label: 'DEMO_SIMULATION — not production financials',
    },
    receipt: {
      ride_id: rideId,
      demo: true,
      disclaimer: 'DEMO_SIMULATION',
    },
  }
}

/**
 * Prefer ledger; fall back to labeled demo.
 * @param {number} rideId
 * @param {Record<string, unknown> | null | undefined} payment
 * @param {number} [fallbackGrossCents]
 * @returns {TripRecord}
 */
export function resolveTripRecord(rideId, payment, fallbackGrossCents) {
  const ledger = tripRecordFromLedgerPayment(rideId, payment)
  if (ledger) return ledger
  return tripRecordDemoSimulation(rideId, fallbackGrossCents)
}

/**
 * @param {TripRecord} record
 * @returns {string}
 */
export function formatTripRecordForPrompt(record) {
  return JSON.stringify(
    {
      ride_id: record.rideId,
      source: record.source,
      fare: {
        gross_fare_cents: record.fare.grossFareCents,
        platform_cut_cents: record.fare.platformCutCents,
        driver_payout_cents: record.fare.driverPayoutCents,
        status: record.fare.status,
        currency: record.fare.currency,
        label: record.fare.label,
      },
      receipt: record.receipt || null,
      instruction:
        record.source === FARE_SOURCE_DEMO
          ? 'Values are DEMO_SIMULATION only. Do not describe as bank-settled production money.'
          : 'Values are from ride_payments ledger. Summarize only these numbers.',
    },
    null,
    2,
  )
}
