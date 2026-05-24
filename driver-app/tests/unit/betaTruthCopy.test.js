import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  BETA_CALCULATED_VALUE_LABEL,
  BETA_DRIVER_ACKNOWLEDGMENT_BLOCKS,
  BETA_FORBIDDEN_PAYMENT_PHRASES,
  BETA_STRAIGHT_LINE_ESTIMATE,
  containsBetaForbiddenPaymentLanguage,
  containsBetaForbiddenRoutingClaim,
  betaRoutingLabelFromPayload,
  testRideLabelForLifecycleReason,
} from '../../src/utils/betaTruthCopy.js'

describe('betaTruthCopy (HALFAPP_TRUSTED_NO_MONEY_BETA_BOUNDARY_PACK_01)', () => {
  it('uses required calculated-test-value label', () => {
    assert.match(BETA_CALCULATED_VALUE_LABEL, /calculated test value/i)
    assert.match(BETA_CALCULATED_VALUE_LABEL, /no money collected or paid/i)
  })
  it('exposes onboarding acknowledgment blocks', () => {
    assert.ok(BETA_DRIVER_ACKNOWLEDGMENT_BLOCKS.length >= 5)
    assert.ok(
      BETA_DRIVER_ACKNOWLEDGMENT_BLOCKS.some((b) => /no rider charges/i.test(b))
    )
  })

  it('allows preferred phrases with not paid / testing only', () => {
    assert.equal(containsBetaForbiddenPaymentLanguage(BETA_CALCULATED_VALUE_LABEL), false)
    assert.equal(
      containsBetaForbiddenPaymentLanguage('Recorded obligation does not mean payout.'),
      false
    )
    assert.equal(
      containsBetaForbiddenPaymentLanguage('No rider charges. No driver payouts.'),
      false
    )
  })

  it('flags forbidden payment execution phrases', () => {
    for (const phrase of BETA_FORBIDDEN_PAYMENT_PHRASES) {
      assert.equal(
        containsBetaForbiddenPaymentLanguage(`Driver message: ${phrase} today`),
        true,
        `expected forbidden: ${phrase}`
      )
    }
  })

  it('labels simulation and ops test rides', () => {
    assert.ok(testRideLabelForLifecycleReason('simulation'))
    assert.ok(testRideLabelForLifecycleReason('ops_seed'))
    assert.equal(testRideLabelForLifecycleReason('open_board'), null)
  })

  it('uses straight-line estimate for fallback routing', () => {
    const label = betaRoutingLabelFromPayload({
      route_truth: { used_fallback: true, osrm_runtime_claim: 'not_proved' },
    })
    assert.equal(label, BETA_STRAIGHT_LINE_ESTIMATE)
  })

  it('rejects forbidden production routing claims', () => {
    assert.equal(containsBetaForbiddenRoutingClaim('production OSRM is live'), true)
    assert.equal(containsBetaForbiddenRoutingClaim(BETA_STRAIGHT_LINE_ESTIMATE), false)
  })
})
