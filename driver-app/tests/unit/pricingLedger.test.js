import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

/**
 * Mirror of backend v0.1 commission rules for quick frontend unit checks.
 */
function compute(driverShareable, serviceFee = 150, tip = 0, passThrough = 0) {
  const platformCommission = Math.round((driverShareable * 2000) / 10000)
  const driverRidePayout = driverShareable - platformCommission
  const platformRevenue = platformCommission + serviceFee
  const customerTotal = driverShareable + serviceFee + passThrough + tip
  const driverTotal = driverRidePayout + tip
  return { platformCommission, driverRidePayout, platformRevenue, customerTotal, driverTotal }
}

describe('pricing ledger v0.1 (frontend mirror)', () => {
  it('normal ride', () => {
    const r = compute(2500, 150, 0, 0)
    assert.equal(r.platformCommission, 500)
    assert.equal(r.driverRidePayout, 2000)
    assert.equal(r.platformRevenue, 650)
    assert.equal(r.customerTotal, 2650)
  })

  it('short ride protection', () => {
    const r = compute(1000, 150)
    assert.equal(r.platformCommission, 200)
    assert.equal(r.driverRidePayout, 800)
    assert.equal(r.platformRevenue, 350)
    assert.equal(r.customerTotal, 1150)
  })

  it('tip not commissioned', () => {
    const r = compute(2500, 150, 500)
    assert.equal(r.platformCommission, 500)
    assert.equal(r.driverTotal, 2500)
  })
})
