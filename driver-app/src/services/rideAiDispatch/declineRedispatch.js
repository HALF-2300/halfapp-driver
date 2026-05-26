import { DISPATCH_AI_STATES } from './constants.js'

/**
 * Local advisory dispatch UI state — does not write backend lifecycle.
 */
export function createDeclineRedispatchManager() {
  let state = DISPATCH_AI_STATES.IDLE
  let redispatchTimer = null
  let redispatchInFlight = false

  const clearTimer = () => {
    if (redispatchTimer != null) {
      clearTimeout(redispatchTimer)
      redispatchTimer = null
    }
  }

  return {
    getState() {
      return state
    },
    setMatched() {
      clearTimer()
      redispatchInFlight = false
      state = DISPATCH_AI_STATES.MATCHED
    },
    setAccepted() {
      clearTimer()
      redispatchInFlight = false
      state = DISPATCH_AI_STATES.ACCEPTED
    },
    setInTrip() {
      clearTimer()
      redispatchInFlight = false
      state = DISPATCH_AI_STATES.IN_TRIP
    },
    setComplete() {
      clearTimer()
      redispatchInFlight = false
      state = DISPATCH_AI_STATES.COMPLETE
    },
    setIdle() {
      clearTimer()
      redispatchInFlight = false
      state = DISPATCH_AI_STATES.IDLE
    },
    /**
     * Decline → DECLINED → REDISPATCHING (single timeout; no stacking).
     * @param {{ onRedispatchReady?: () => void, delayMs?: number }} [options]
     * @returns {'declined' | 'ignored'}
     */
    decline(options = {}) {
      const { onRedispatchReady, delayMs = 1200 } = options
      if (state !== DISPATCH_AI_STATES.MATCHED && state !== DISPATCH_AI_STATES.ACCEPTED) {
        return 'ignored'
      }
      if (redispatchInFlight) {
        return 'ignored'
      }
      clearTimer()
      state = DISPATCH_AI_STATES.DECLINED
      redispatchInFlight = true
      redispatchTimer = setTimeout(() => {
        redispatchTimer = null
        if (state === DISPATCH_AI_STATES.DECLINED) {
          state = DISPATCH_AI_STATES.REDISPATCHING
          onRedispatchReady?.()
        }
        redispatchInFlight = false
      }, delayMs)
      return 'declined'
    },
    dispose() {
      clearTimer()
      redispatchInFlight = false
      state = DISPATCH_AI_STATES.IDLE
    },
  }
}
