import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  buildMockPricingViewForRide,
  buildRiderReceiptRows,
  computeFinancialsFromShareable,
  driverPayoutDollars,
  formatCents,
} from '../../src/utils/ridePricingDisplay.js'

describe('ridePricingDisplay', () => {
  it('formats cents as dollars', () => {
    assert.equal(formatCents(150), '$1.50')
    assert.equal(formatCents(2650), '$26.50')
  })

  it('shows $1.50 platform service fee on rider receipt', () => {
    const pricing = buildMockPricingViewForRide({ distance_km: 4, duration_minutes: 12 })
    const receipt = buildRiderReceiptRows(pricing)
    const feeRow = receipt.rows.find((r) => r.testId === 'rider-platform-service-fee')
    assert.equal(feeRow?.value, '$1.50')
  })

  it('keeps tips out of platform commission', () => {
    const breakdown = computeFinancialsFromShareable(2500, { tip: 500 })
    assert.equal(breakdown.platform_commission_cents, 500)
    assert.equal(breakdown.driver_total_payout_cents, 2500)
  })

  it('pass-through fees are not added to platform commission', () => {
    const breakdown = computeFinancialsFromShareable(2500, {
      city: 300,
      toll: 100,
    })
    assert.equal(breakdown.platform_commission_cents, 500)
    assert.equal(breakdown.customer_total_cents, 2500 + 150 + 300 + 100)
  })

  it('locks mock pricing on completion', () => {
    const locked = buildMockPricingViewForRide({ distance_km: 2, duration_minutes: 8 }, { lock: true })
    assert.equal(locked.financial_locked, true)
    assert.ok(locked.locked_at)
  })

  it('driverPayoutDollars prefers ledger over legacy fare_amount', () => {
    const ride = {
      fare_amount: 99,
      pricing: { driver_total_payout_cents: 2000, driver_earnings_cents: 2000 },
    }
    assert.equal(driverPayoutDollars(ride), 20)
  })
})
