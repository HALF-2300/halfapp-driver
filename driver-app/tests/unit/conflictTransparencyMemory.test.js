import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  formatConflictIdleProof,
  hasClaimConflictProofLabel,
} from '../../src/utils/rideTransparency.js'

describe('conflictTransparencyMemory', () => {
  it('formats unavailable fallback without inventing ETA or fare', () => {
    const rows = formatConflictIdleProof(null, 42)
    const labels = rows.map((r) => r.label)
    assert.ok(labels.includes('Status'))
    assert.equal(rows.find((r) => r.label === 'Status')?.value, 'Conflict recorded by backend')
    assert.equal(
      rows.find((r) => r.label === 'Transparency')?.value,
      'Details unavailable'
    )
    assert.equal(labels.some((l) => /eta|fare|route/i.test(l)), false)
  })

  it('formats lost claim proof from backend transparency', () => {
    const rows = formatConflictIdleProof(
      {
        ride_id: '12',
        driver_id: '3',
        visibility: { source: 'open_board', policy_name: 'Ranked Open Board v1' },
        claim: {
          last_claim_result: 'lost',
          truth_status: 'backend_conflict',
          claimable: false,
        },
        audit: { ledger_event_ids: ['101', '102'] },
        truth_labels: ['CLAIM_CONFLICT_PROOF'],
      },
      12
    )
    assert.equal(
      rows.find((r) => r.label === 'last_claim_result')?.value,
      'lost'
    )
    assert.equal(
      rows.find((r) => r.label === 'truth_status')?.value,
      'backend_conflict'
    )
    assert.equal(rows.find((r) => r.label === 'Claimable')?.value, 'No')
    assert.ok(hasClaimConflictProofLabel({ truth_labels: ['CLAIM_CONFLICT_PROOF'] }))
  })
})
