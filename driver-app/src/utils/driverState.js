/**
 * Canonical driver UI state names for the cockpit.
 *
 * The active product spine uses the backend for ride lifecycle and completed
 * earnings. This module contains UI state names and pure transition helpers
 * only; browser storage must not own marketplace or presence truth.
 *
 * Do not present browser storage as real backend truth.
 */

export const DRIVER_STATES = Object.freeze({
  OFFLINE: 'OFFLINE',
  ONLINE_IDLE: 'ONLINE_IDLE',
  REQUEST_INCOMING: 'REQUEST_INCOMING',
  ACCEPTED_TO_PICKUP: 'ACCEPTED_TO_PICKUP',
  ARRIVED_PICKUP: 'ARRIVED_PICKUP',
  IN_PROGRESS: 'IN_PROGRESS',
  COMPLETED: 'COMPLETED',
})

/**
 * @typedef {Object} ActiveRide
 * @property {string} rideId
 * @property {{ lat:number, lng:number, label:string }} pickup
 * @property {{ lat:number, lng:number, label:string }} dropoff
 * @property {string} riderName
 * @property {number} estimatedFare
 * @property {number} distance
 * @property {number} duration
 * @property {string} status
 * @property {string} createdAt
 * @property {string|null} completedAt
 */

function buildDemoCoordinates() {
  const baseLat = -45 + Math.random() * 90
  const baseLng = -120 + Math.random() * 240
  return {
    pickup: {
      lat: Number(baseLat.toFixed(6)),
      lng: Number(baseLng.toFixed(6)),
    },
    dropoff: {
      lat: Number((baseLat + 0.025 + Math.random() * 0.04).toFixed(6)),
      lng: Number((baseLng + 0.025 + Math.random() * 0.04).toFixed(6)),
    },
  }
}

const DEMO_POOL = [
  {
    riderName: 'Demo Rider · Ava',
    pickupLabel: 'Simulation pickup A',
    dropoffLabel: 'Simulation dropoff A',
    estimatedFare: 28.5,
    distance: 14.2,
    duration: 22,
  },
  {
    riderName: 'Demo Rider · Marcus',
    pickupLabel: 'Simulation pickup B',
    dropoffLabel: 'Simulation dropoff B',
    estimatedFare: 12.75,
    distance: 4.6,
    duration: 11,
  },
  {
    riderName: 'Demo Rider · Priya',
    pickupLabel: 'Simulation pickup C',
    dropoffLabel: 'Simulation dropoff C',
    estimatedFare: 9.5,
    distance: 3.1,
    duration: 9,
  },
  {
    riderName: 'Demo Rider · Jordan',
    pickupLabel: 'Simulation pickup D',
    dropoffLabel: 'Simulation dropoff D',
    estimatedFare: 21.0,
    distance: 11.4,
    duration: 19,
  },
]

/**
 * Build a demo ride payload that mirrors the activeRide contract used in the
 * cockpit. Marked obviously as a demo via `source: 'demo'` and the rider name
 * prefix so it cannot be mistaken for a real backend ride.
 *
 * @returns {ActiveRide}
 */
export function buildDemoRide() {
  const template = DEMO_POOL[Math.floor(Math.random() * DEMO_POOL.length)]
  const coords = buildDemoCoordinates()
  const rideId = `demo-${Date.now().toString(36)}`
  return {
    rideId,
    pickup: { ...coords.pickup, label: template.pickupLabel },
    dropoff: { ...coords.dropoff, label: template.dropoffLabel },
    riderName: template.riderName,
    estimatedFare: template.estimatedFare,
    distance: template.distance,
    duration: template.duration,
    status: DRIVER_STATES.REQUEST_INCOMING,
    createdAt: new Date().toISOString(),
    completedAt: null,
    source: 'demo',
  }
}

const ALLOWED_TRANSITIONS = {
  [DRIVER_STATES.OFFLINE]: [DRIVER_STATES.ONLINE_IDLE],
  [DRIVER_STATES.ONLINE_IDLE]: [DRIVER_STATES.OFFLINE, DRIVER_STATES.REQUEST_INCOMING],
  [DRIVER_STATES.REQUEST_INCOMING]: [DRIVER_STATES.ONLINE_IDLE, DRIVER_STATES.ACCEPTED_TO_PICKUP],
  [DRIVER_STATES.ACCEPTED_TO_PICKUP]: [DRIVER_STATES.ARRIVED_PICKUP, DRIVER_STATES.ONLINE_IDLE],
  [DRIVER_STATES.ARRIVED_PICKUP]: [DRIVER_STATES.IN_PROGRESS, DRIVER_STATES.ONLINE_IDLE],
  [DRIVER_STATES.IN_PROGRESS]: [DRIVER_STATES.COMPLETED],
  [DRIVER_STATES.COMPLETED]: [DRIVER_STATES.ONLINE_IDLE, DRIVER_STATES.OFFLINE],
}

export function canTransition(from, to) {
  const allowed = ALLOWED_TRANSITIONS[from] || []
  return allowed.includes(to)
}

export function getNextDriverAction(state) {
  switch (state) {
    case DRIVER_STATES.ACCEPTED_TO_PICKUP:
      return { label: 'Arrived at pickup', next: DRIVER_STATES.ARRIVED_PICKUP }
    case DRIVER_STATES.ARRIVED_PICKUP:
      return { label: 'Start trip', next: DRIVER_STATES.IN_PROGRESS }
    case DRIVER_STATES.IN_PROGRESS:
      return { label: 'Complete trip', next: DRIVER_STATES.COMPLETED }
    default:
      return null
  }
}

export function summarizeTrips(trips) {
  const list = Array.isArray(trips) ? trips : []
  const todayStr = new Date().toDateString()
  let total = 0
  let today = 0
  let totalDistance = 0
  let todayTrips = 0
  for (const trip of list) {
    const fare = Number(trip?.estimatedFare)
    if (Number.isFinite(fare)) total += fare
    const dist = Number(trip?.distance)
    if (Number.isFinite(dist)) totalDistance += dist
    if (trip?.completedAt) {
      const d = new Date(trip.completedAt)
      if (!Number.isNaN(d.getTime()) && d.toDateString() === todayStr) {
        if (Number.isFinite(fare)) today += fare
        todayTrips += 1
      }
    }
  }
  return {
    totalEarnings: total,
    todayEarnings: today,
    totalTrips: list.length,
    todayTrips,
    totalDistanceKm: totalDistance,
  }
}
