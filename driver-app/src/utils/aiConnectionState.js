/** AI assistant connection states — no provider calls unless BACKEND_CONNECTED. */

export const AI_CONNECTION_STATES = Object.freeze({
  OFF: 'OFF',
  LOCAL_CONTEXT_ONLY: 'LOCAL_CONTEXT_ONLY',
  BACKEND_CONNECTED: 'BACKEND_CONNECTED',
  ERROR: 'ERROR',
})

export const DEFAULT_AI_CONNECTION_STATE = AI_CONNECTION_STATES.OFF

export function canSendToModel(connectionState) {
  return connectionState === AI_CONNECTION_STATES.BACKEND_CONNECTED
}

export function connectionStateLabel(connectionState) {
  switch (connectionState) {
    case AI_CONNECTION_STATES.LOCAL_CONTEXT_ONLY:
      return 'Local context only — no model'
    case AI_CONNECTION_STATES.BACKEND_CONNECTED:
      return 'Backend connected'
    case AI_CONNECTION_STATES.ERROR:
      return 'Connection error'
    case AI_CONNECTION_STATES.OFF:
    default:
      return 'AI off'
  }
}
