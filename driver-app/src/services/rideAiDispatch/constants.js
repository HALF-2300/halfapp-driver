/** Ride AI dispatch loop — advisory only; never mutates backend dispatch. */

export const DISPATCH_AI_STATES = {
  IDLE: 'idle',
  MATCHED: 'matched',
  ACCEPTED: 'accepted',
  DECLINED: 'declined',
  REDISPATCHING: 'redispatching',
  IN_TRIP: 'in_trip',
  COMPLETE: 'complete',
}

export const AI_LIFECYCLE_EVENTS = {
  MATCH_ANALYSIS: 'match_analysis',
  ROUTE_INTELLIGENCE: 'route_intelligence',
  DECLINE_REDISPATCH: 'decline_redispatch',
  OPS_MONITORING: 'ops_monitoring',
  TRIP_COMPLETE: 'trip_complete',
}

export const ROUTE_ADVISORY_LABEL = '[ADVISORY · AI ESTIMATE · NOT LIVE TRAFFIC]'

export const FARE_SOURCE_LEDGER = 'LEDGER'
export const FARE_SOURCE_DEMO = 'DEMO_SIMULATION'

export const MIN_AI_CALL_INTERVAL_MS = 3000
export const SESSION_AI_CALL_BUDGET = 24

export const DEMO_FLOOR_CENTS = 925
export const DEMO_DRIVER_SHARE_BPS = 7200
