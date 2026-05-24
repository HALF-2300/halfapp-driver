/**
 * Trusted no-money driver beta — canonical copy, route wording, and forbidden payment phrases.
 * Orders: HALFAPP_BETA_TRUTH_SHEET_AND_MICROCOPY_01, HALFAPP_TRUSTED_NO_MONEY_BETA_BOUNDARY_PACK_01
 * Docs: docs/HALFAPP_TRUSTED_NO_MONEY_BETA_BOUNDARY_PACK_01.md
 */

export const BETA_NO_MONEY_TRUTH_ENABLED =
  import.meta.env?.VITE_BETA_NO_MONEY_TRUTH === 'true'

export const BETA_FIRST_RUN_ACK_STORAGE_KEY = 'halfapp_beta_truth_ack_v1'

/** Required framing — use verbatim where space allows. */
export const BETA_NO_MONEY_HEADLINE =
  'No rider charges. No driver payouts.'

export const BETA_NO_MONEY_SUBHEAD =
  'No money will be collected or paid through HalfApp during this beta.'

export const BETA_CALCULATED_VALUE_LABEL =
  'Calculated test value — no money collected or paid.'

export const BETA_VALUES_ARE_TEST_VALUES =
  'Values shown are calculated test values for system validation — not money received or sent.'

export const BETA_OBLIGATION_NOT_PAYOUT = 'Recorded obligation does not mean payout.'

export const BETA_OBLIGATION_DETAIL =
  'This is a calculation record. No payout has been sent.'

export const BETA_SETTLEMENT_SECTION_NOTE = 'Obligation recorded — not payout execution.'

export const BETA_OPEN_BOARD_DISPATCH =
  'Open board: rides appear to multiple drivers; first claim wins.'

export const BETA_CLAIM_CONFLICT_HEADLINE = 'Ride already claimed'

export const BETA_CLAIM_CONFLICT_BODY =
  'Another driver accepted this ride first. Open board dispatch — first claim wins.'

export const BETA_ROUTE_ESTIMATE_DISCLAIMER =
  'Route may be an estimate/fallback unless OSRM runtime proof is GO.'

export const BETA_STRAIGHT_LINE_ESTIMATE = 'Straight-line estimate'

export const BETA_STRAIGHT_LINE_NOTE =
  'Straight-line estimate — not a live road-network route.'

export const BETA_ROAD_NETWORK_ROUTE = 'Road-network route'

export const BETA_OSRM_NOT_PROVED = 'OSRM runtime not proved'

export const BETA_SIMULATION_RIDE_LABEL =
  'Beta ride / simulation ride — for product testing only.'

export const BETA_OPS_TEST_RIDE_LABEL = 'Ops-created test ride — for product testing only.'

export const BETA_COCKPIT_BANNER_TITLE = 'Trusted driver beta — comprehension only'

export const BETA_COCKPIT_BANNER_BODY =
  'Operational truth beta: lifecycle, pricing ledger, and audit — not a marketplace launch or paid pilot.'

export const BETA_INCOMING_RIDE_EYEBROW = 'Incoming ride · open board'

export const BETA_INCOMING_ESTIMATE_LABEL = 'Est. test earnings'

export const BETA_INCOMING_ESTIMATE_HINT = '(not paid)'

export const BETA_COMPLETED_TRIP_NOTE = BETA_OBLIGATION_DETAIL

export const BETA_EARNINGS_SUBTITLE =
  'Test earnings from completed backend rides — calculation records only, not payouts.'

/** Payment execution visibility (Phase 4) — never imply paid/deposited. */
export const BETA_PAYMENT_VISIBILITY_TITLE = 'Payment execution visibility'

export const BETA_PAYMENT_VISIBILITY_NOTE =
  'Processed and pending amounts from the payment provider. Not a bank deposit or payout guarantee.'

export const BETA_PAYMENT_AVAILABLE_LABEL = 'Net processed (after refunds & disputes)'

/** Provider Connect payout status (Phase 5) — status from Stripe, not bank confirmation. */
export const BETA_PAYOUT_VISIBILITY_TITLE = 'Provider payout status'

export const BETA_PAYOUT_PAID_LABEL = 'Provider payout (paid status)'

export const BETA_PAYOUT_PENDING_LABEL = 'Provider payout (pending / in transit)'

export const BETA_PAYOUT_VISIBILITY_NOTE =
  'Payout rows reflect the payment provider’s payout object status. Not confirmation that funds reached your bank.'

export const BETA_PAYOUT_FAILED_LABEL = 'Failed payouts (provider status)'

export const BETA_PAYOUT_LAST_STATUS_LABEL = 'Last payout status (provider)'

export const BETA_PAYOUT_LAST_TIME_LABEL = 'Last payout time (provider)'

export const BETA_PAYOUT_LAST_STATUS_NONE = 'No payouts yet'

export const BETA_PAYOUT_LAST_TIME_NONE = '—'

export const BETA_PAYOUT_ESTIMATED_ARRIVAL = 'Provider estimated arrival'

export const BETA_AUDIT_DISCLAIMER =
  'Obligation rows record backend-computed amounts — not bank or PSP movement.'

export const BETA_AUDIT_OBLIGATION_LABEL =
  'Recorded obligation (testing only) — backend accounting only, not payment execution.'

export const BETA_SUPPORT_PLACEHOLDER = 'Beta support: [support channel — ops to configure]'

export const BETA_CONFUSED_PROMPT =
  'If anything looks like a payment or payout, stop and contact support — amounts are test calculations only.'

/** Driver onboarding / first-run acknowledgment (checkbox; stored ack is ops-owned). */
export const BETA_DRIVER_ACKNOWLEDGMENT_BLOCKS = [
  BETA_NO_MONEY_HEADLINE,
  BETA_NO_MONEY_SUBHEAD,
  BETA_VALUES_ARE_TEST_VALUES,
  BETA_OBLIGATION_NOT_PAYOUT,
  BETA_OBLIGATION_DETAIL,
  'This is an operational truth and usability beta — not a marketplace launch, paid pilot, or payment test.',
  BETA_OPEN_BOARD_DISPATCH,
  BETA_ROUTE_ESTIMATE_DISCLAIMER,
  'I will not describe dollar amounts in the app as money received, deposited, or paid out.',
]

/**
 * Substrings that must not appear in driver-visible product copy during the no-money beta
 * unless covered by {@link BETA_FORBIDDEN_PAYMENT_ALLOWLIST}.
 */
export const BETA_FORBIDDEN_PAYMENT_PHRASES = [
  'paid out',
  'payment processed',
  'payout sent',
  'payout executed',
  'deposited',
  'cash out',
  'wallet',
  'available balance',
  'instant pay',
  'bank settled',
  'stripe',
]

/** Preferred phrases that may contain forbidden substrings (e.g. "not paid"). */
export const BETA_FORBIDDEN_PAYMENT_ALLOWLIST = [
  'not paid',
  'not paid out',
  'not payout',
  'no payout',
  'no driver payouts',
  'no rider charges',
  'testing only',
  'not payout execution',
  'does not mean payout',
  'not stripe',
  'no payout has been sent',
  'no payout sent',
  'not paid.',
  'do not interpret them as paid out',
  'provider payout',
  'paid status',
  'pending / in transit',
  'not confirmation that funds reached your bank',
  'failed payouts (provider status)',
  'last payout status (provider)',
  'last payout time (provider)',
  'no payouts yet',
  'provider estimated arrival',
]

const FORBIDDEN_ROUTING_PHRASES = [
  'production osrm',
  'road-accurate',
  'road accurate',
  'live road network proof',
]

/** @param {string} text */
function stripAllowlistedPhrases(text) {
  let out = text.toLowerCase()
  for (const allowed of BETA_FORBIDDEN_PAYMENT_ALLOWLIST) {
    out = out.split(allowed.toLowerCase()).join(' ')
  }
  return out
}

/** @param {string} text */
export function containsBetaForbiddenPaymentLanguage(text) {
  if (!text) return false
  const scrubbed = stripAllowlistedPhrases(text)
  return BETA_FORBIDDEN_PAYMENT_PHRASES.some((phrase) => scrubbed.includes(phrase.toLowerCase()))
}

/** @param {string} text */
export function containsBetaForbiddenRoutingClaim(text) {
  if (!text) return false
  const lower = text.toLowerCase()
  return FORBIDDEN_ROUTING_PHRASES.some((phrase) => lower.includes(phrase))
}

/**
 * @param {string | null | undefined} lifecycleReason
 * @returns {string | null}
 */
export function testRideLabelForLifecycleReason(lifecycleReason) {
  const reason = String(lifecycleReason || '').trim().toLowerCase()
  if (!reason) return null
  if (reason === 'simulation' || reason.includes('simulation')) {
    return BETA_SIMULATION_RIDE_LABEL
  }
  if (
    reason === 'investor_showcase_seed' ||
    reason.startsWith('ops_') ||
    reason.startsWith('beta_') ||
    reason.startsWith('test_')
  ) {
    return BETA_OPS_TEST_RIDE_LABEL
  }
  return null
}

/**
 * Driver-facing routing label from route truth payload.
 * @param {Record<string, unknown> | null | undefined} payload
 */
export function betaRoutingLabelFromPayload(payload) {
  if (!payload) return '—'
  if (payload.copy?.routing_label) return String(payload.copy.routing_label)
  const truth = payload.route_truth
  if (truth?.used_fallback) return BETA_STRAIGHT_LINE_ESTIMATE
  if (truth?.osrm_runtime_claim === 'proved_portland_v0_1') {
    return BETA_ROAD_NETWORK_ROUTE
  }
  return truth?.current_provider || '—'
}

/**
 * Fallback estimate note for route truth UI.
 * @param {Record<string, unknown> | null | undefined} payload
 */
export function betaRouteEstimateNote(payload) {
  if (payload?.copy?.estimate_note) return String(payload.copy.estimate_note)
  const truth = payload?.route_truth
  if (truth?.used_fallback) return BETA_STRAIGHT_LINE_NOTE
  return null
}
