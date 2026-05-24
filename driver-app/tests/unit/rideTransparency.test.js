import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  formatTransparencyLine,
  isBackendClaimConflict,
} from '../../src/utils/rideTransparency.js'

describe('rideTransparency', () => {
  it('detects structured backend conflict detail', () => {
    assert.equal(
      isBackendClaimConflict({
        detail: 'Ride already claimed',
        ride_id: 12,
        claim_result: 'lost',
        truth_status: 'backend_conflict',
      }),
      true
    )
    assert.equal(isBackendClaimConflict('Ride already claimed'), false)
    assert.equal(isBackendClaimConflict({ detail: 'Ride already claimed' }), false)
  })

  it('formats visibility and claim rows without inventing ETA', () => {
    const rows = formatTransparencyLine({
      driver_id: '3',
      visibility: {
        source: 'open_board',
        policy_name: 'Ranked Open Board v1',
        reason_codes: ['requested_unassigned_open_board'],
      },
      claim: {
        claimable: true,
        current_status: 'requested',
        last_claim_result: 'none',
      },
      dismissal: { hidden_for_this_driver: false },
    })
    const labels = rows.map((r) => r.label)
    assert.ok(labels.includes('Visibility source'))
    assert.ok(labels.includes('Claimable'))
    assert.equal(labels.some((l) => /eta/i.test(l)), false)
  })
})
