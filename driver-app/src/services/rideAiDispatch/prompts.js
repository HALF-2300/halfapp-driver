import { buildSanitizedPromptPayload } from './piiSanitizer.js'
import { formatRouteContextForPrompt } from './routeContext.js'
import { formatTripRecordForPrompt } from './fareBreakdown.js'

export function buildMatchAnalysisPrompt(operationalContext) {
  return [
    'You are an advisory dispatch analyst for HalfApp. Do NOT change dispatch decisions.',
    'Analyze match quality using only the sanitized operational JSON below.',
    'Comment on proximity score, rating optimality, and ETA alignment if present.',
    'Never invent rider names, plates, or exact addresses.',
    '',
    buildSanitizedPromptPayload(operationalContext),
  ].join('\n')
}

/**
 * @param {import('./routeContext.js').RouteContext} routeContext
 */
export function buildRouteIntelligencePrompt(routeContext) {
  return [
    'You are an advisory route assistant. Do NOT claim live traffic unless live_traffic is true.',
    'If advisory_label is set, echo that the note is not live traffic guidance.',
    '',
    formatRouteContextForPrompt(routeContext),
  ].join('\n')
}

export function buildDeclineRedispatchPrompt(operationalContext) {
  return [
    'Driver declined the offer. Advisory only — do not mutate dispatch.',
    'Summarize redispatch impact and backup driver assessment queue.',
    '',
    buildSanitizedPromptPayload(operationalContext),
  ].join('\n')
}

export function buildOpsMonitoringPrompt(operationalContext) {
  return [
    'Trip is in progress. Advisory ops monitoring — no dispatch changes.',
    '',
    buildSanitizedPromptPayload(operationalContext),
  ].join('\n')
}

/**
 * @param {import('./fareBreakdown.js').TripRecord} tripRecord
 */
export function buildTripCompletePrompt(tripRecord) {
  return [
    'Trip complete. Summarize financial breakdown using ONLY the structured trip record JSON.',
    'If source is DEMO_SIMULATION, state clearly that figures are demo simulation, not production payouts.',
    'Do not calculate or invent dollar amounts — use only provided cent fields.',
    '',
    formatTripRecordForPrompt(tripRecord),
  ].join('\n')
}
