import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

const DRIVER_SHARE_BPS = 8000
const DEFAULT_SERVICE_FEE_CENTS = 150
const BASE_FARE_CENTS = 500
const PER_KM_CENTS = 150

function shareableFromKm(distanceKm) {
  return BASE_FARE_CENTS + Math.round(Math.max(0, distanceKm) * PER_KM_CENTS)
}

function calculatePricing({
  distanceKm,
  tipCents = 0,
  serviceFeeCents = DEFAULT_SERVICE_FEE_CENTS,
  passThroughCents = 0,
}) {
  const shareable = shareableFromKm(distanceKm)
  const driverCommission = Math.floor((shareable * DRIVER_SHARE_BPS) / 10_000)
  const platformCommission = shareable - driverCommission
  const driverEarnings = driverCommission + tipCents
  const platformEarnings = platformCommission + serviceFeeCents
  return { shareable, driverCommission, platformCommission, driverEarnings, platformEarnings, passThroughCents }
}

describe('v0.1 ride pricing ledger rules', () => {
  it('normal ride: 80/20 on driver-shareable fare', () => {
    const p = calculatePricing({ distanceKm: 4 })
    assert.equal(p.shareable, 1100)
    assert.equal(p.driverCommission, 880)
    assert.equal(p.platformCommission, 220)
  })

  it('short ride includes $1.50 service fee in platform earnings', () => {
    const p = calculatePricing({ distanceKm: 0.5 })
    assert.equal(p.shareable, 575)
    assert.equal(p.platformEarnings, p.platformCommission + 150)
  })

  it('tip is not commissioned', () => {
    const p = calculatePricing({ distanceKm: 2, tipCents: 500 })
    assert.equal(p.driverEarnings, p.driverCommission + 500)
    assert.equal(p.platformEarnings, p.platformCommission + 150)
  })

  it('pass-through fees are excluded from commission split', () => {
    const p = calculatePricing({ distanceKm: 3, passThroughCents: 800 })
    assert.equal(p.driverCommission + p.platformCommission, p.shareable)
    assert.equal(p.passThroughCents, 800)
  })
})
