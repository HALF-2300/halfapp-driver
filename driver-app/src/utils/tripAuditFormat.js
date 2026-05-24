/** Format helpers for read-only trip audit / receipt UI (no payment-execution copy). */

import { BETA_FORBIDDEN_PAYMENT_PHRASES } from './betaTruthCopy.js'

const FORBIDDEN_PAYMENT_PHRASES = BETA_FORBIDDEN_PAYMENT_PHRASES

/** @param {string} eventType */
export function formatAuditEventType(eventType) {
  if (!eventType) return '—'
  return eventType.replace(/\./g, ' · ').replace(/_/g, ' ')
}

/** @param {Record<string, unknown>} entry */
export function formatSettlementEntryLabel(entry) {
  const type = String(entry?.entry_type || 'obligation')
  const party = entry?.party ? ` (${entry.party})` : ''
  return `${type.replace(/_/g, ' ')}${party}`
}

/** @param {Record<string, unknown> | null | undefined} audit */
export function auditUsesObligationLanguage(audit) {
  const label = audit?.copy?.driver_payment_label
  return typeof label === 'string' && /obligation/i.test(label)
}

/** @param {string} text */
export function containsForbiddenPaymentLanguage(text) {
  if (!text) return false
  const lower = text.toLowerCase()
  return FORBIDDEN_PAYMENT_PHRASES.some((phrase) => lower.includes(phrase))
}

/** @param {Record<string, unknown> | null | undefined} audit */
export function buildAuditPricingForSummary(audit) {
  const pricing = audit?.pricing
  if (!pricing || typeof pricing !== 'object') return null
  return {
    ...pricing,
    financial_locked: audit.financial_locked ?? pricing.financial_locked,
  }
}
