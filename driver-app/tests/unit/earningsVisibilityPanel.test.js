import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { BETA_FORBIDDEN_PAYMENT_PHRASES } from '../../src/utils/betaTruthCopy.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const panelSrc = readFileSync(
  path.resolve(__dirname, '../../src/components/EarningsVisibilityPanel.jsx'),
  'utf8'
)

describe('EarningsVisibilityPanel (Phase 4 + 5)', () => {
  it('loads reconciliation from driver API', () => {
    assert.match(panelSrc, /getPaymentReconciliation/)
    assert.match(panelSrc, /getPaymentExecutions/)
    assert.match(panelSrc, /getPayouts/)
  })

  it('avoids forbidden paid/deposited marketing phrases', () => {
    for (const phrase of BETA_FORBIDDEN_PAYMENT_PHRASES) {
      assert.equal(
        panelSrc.toLowerCase().includes(phrase.toLowerCase()),
        false,
        `forbidden phrase: ${phrase}`
      )
    }
  })

  it('renders failed and last-payout rows inside payout section', () => {
    assert.match(panelSrc, /BETA_PAYOUT_FAILED_LABEL/)
    assert.match(panelSrc, /BETA_PAYOUT_LAST_STATUS_LABEL/)
    assert.match(panelSrc, /testId="earnings-visibility-payout-failed"/)
    assert.match(panelSrc, /testId="earnings-visibility-payout-last-status"/)
  })

  it('shows payout section from provider_payout_visible, not payout list length', () => {
    assert.match(panelSrc, /data\.provider_payout_visible\s*&&/)
    assert.match(panelSrc, /data-testid="earnings-visibility-payout-section"/)
    assert.match(panelSrc, /payouts\.length\s*>\s*0/)
    const sectionIdx = panelSrc.indexOf('provider_payout_visible')
    const listIdx = panelSrc.indexOf('payouts.length > 0')
    assert.ok(sectionIdx > 0 && listIdx > 0)
    assert.ok(
      sectionIdx < listIdx,
      'payout section must not depend on payouts list being non-empty'
    )
  })

  it('exposes test ids for E2E', () => {
    assert.match(panelSrc, /data-testid="earnings-visibility-panel"/)
    assert.match(panelSrc, /testId="earnings-visibility-available"/)
    assert.match(panelSrc, /testId="earnings-visibility-collected"/)
    assert.match(panelSrc, /data-testid="earnings-visibility-payout-section"/)
    assert.match(panelSrc, /testId="earnings-visibility-payout-paid"/)
  })

  it('shows provider estimated arrival on payout list rows', () => {
    assert.match(panelSrc, /BETA_PAYOUT_ESTIMATED_ARRIVAL/)
    assert.match(panelSrc, /row\.arrival_date/)
  })
})
