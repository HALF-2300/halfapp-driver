import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
import {
  auditUsesObligationLanguage,
  buildAuditPricingForSummary,
  containsForbiddenPaymentLanguage,
  formatAuditEventType,
  formatSettlementEntryLabel,
} from '../../src/utils/tripAuditFormat.js'

describe('tripAuditReceipt', () => {
  it('formats lifecycle and ledger event types for display', () => {
    assert.equal(formatAuditEventType('ride.completed'), 'ride · completed')
    assert.equal(formatAuditEventType('earning.calculated'), 'earning · calculated')
  })

  it('labels settlement rows as obligations without payout language', () => {
    const label = formatSettlementEntryLabel({
      entry_type: 'driver_payout_obligation',
      party: 'driver',
    })
    assert.match(label, /driver payout obligation/i)
    assert.equal(containsForbiddenPaymentLanguage(label), false)
  })

  it('detects forbidden payment-execution phrases', () => {
    assert.equal(containsForbiddenPaymentLanguage('Payment processed'), true)
    assert.equal(containsForbiddenPaymentLanguage('Recorded obligation'), false)
  })

  it('maps audit pricing for RidePayoutSummary with financial_locked', () => {
    const mapped = buildAuditPricingForSummary({
      financial_locked: true,
      pricing: {
        driver_ride_payout_cents: 2000,
        platform_service_fee_cents: 150,
        customer_total_cents: 2500,
      },
    })
    assert.equal(mapped.financial_locked, true)
    assert.equal(mapped.platform_service_fee_cents, 150)
  })

  it('recognizes backend obligation copy', () => {
    assert.equal(
      auditUsesObligationLanguage({
        copy: { driver_payment_label: 'Recorded obligation, not ' + 'paid out' },
      }),
      true
    )
  })

  it('TripAuditReceipt exposes technical proof toggle and TripsList audit link', () => {
    const receipt = readFileSync(
      path.join(__dirname, '../../src/components/TripAuditReceipt.jsx'),
      'utf8'
    )
    const trips = readFileSync(path.join(__dirname, '../../src/components/TripsList.jsx'), 'utf8')
    const app = readFileSync(path.join(__dirname, '../../src/App.jsx'), 'utf8')
    assert.ok(receipt.includes('trip-audit-money-truth-summary'))
    assert.ok(
      receipt.includes(
        'This is a server-calculated record. Pricing is locked by the server. No payout has been sent.'
      )
    )
    assert.ok(receipt.includes('shouldShowPrimaryMoneyTruth'))
    assert.ok(receipt.includes('trip-audit-technical-toggle'))
    assert.ok(receipt.includes('trip-audit-payment-execution'))
    assert.ok(receipt.includes('Technical proof'))
    assert.ok(trips.includes('trip-audit-link'))
    assert.ok(app.includes('/driver/trips/:rideId/audit'))
  })
})
