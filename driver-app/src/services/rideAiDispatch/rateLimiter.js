import { MIN_AI_CALL_INTERVAL_MS, SESSION_AI_CALL_BUDGET } from './constants.js'

/**
 * Client-side AI call throttle — advisory panel only.
 */
export function createAiRateLimiter({
  minIntervalMs = MIN_AI_CALL_INTERVAL_MS,
  sessionBudget = SESSION_AI_CALL_BUDGET,
} = {}) {
  let lastCallAt = -minIntervalMs
  let callsUsed = 0

  return {
    canCall(now = Date.now()) {
      if (callsUsed >= sessionBudget) {
        return { ok: false, reason: 'session_budget_exceeded' }
      }
      if (now - lastCallAt < minIntervalMs) {
        return { ok: false, reason: 'min_interval' }
      }
      return { ok: true, reason: null }
    },
    recordCall(now = Date.now()) {
      lastCallAt = now
      callsUsed += 1
    },
    reset() {
      lastCallAt = -minIntervalMs
      callsUsed = 0
    },
    get callsUsed() {
      return callsUsed
    },
    get sessionBudget() {
      return sessionBudget
    },
    get paused() {
      return callsUsed >= sessionBudget
    },
  }
}
