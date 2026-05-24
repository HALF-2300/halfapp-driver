import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  MONEY_TRUTH_COPY,
  hasMisleadingMoneyPhrase,
} from '../../src/constants/truthCopy.js'
import {
  DISPATCH_TRUTH_COPY,
  hasForbiddenDispatchClaim,
} from '../../src/constants/dispatchCopy.js'

describe('truthCopy (HALFAPP_DRIVER_EARNINGS_AND_DISPATCH_COPY_FOUNDATION_01)', () => {
  it('money truth copy avoids misleading payment-execution phrases', () => {
    for (const [key, value] of Object.entries(MONEY_TRUTH_COPY)) {
      if (key === 'clarifier') continue
      if (typeof value === 'string') {
        assert.equal(hasMisleadingMoneyPhrase(value), false)
      }
    }
  })

  it('dispatch truth copy avoids false nearest-driver claims', () => {
    for (const [key, value] of Object.entries(DISPATCH_TRUTH_COPY)) {
      if (key === 'line4') continue
      if (typeof value === 'string') {
        assert.equal(hasForbiddenDispatchClaim(value), false)
      }
    }
  })

  it('allows negative no-payout sentence without flagging payout wording', () => {
    assert.equal(hasMisleadingMoneyPhrase(MONEY_TRUTH_COPY.noMoneyMovedSentence), false)
    assert.equal(hasMisleadingMoneyPhrase(MONEY_TRUTH_COPY.noPayoutSentLabel), false)
  })
})
