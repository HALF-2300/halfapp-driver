import test from 'node:test'
import assert from 'node:assert/strict'
import {
  RIDE_STATUS,
  mapBackendStatus,
  paymentForReceipt,
  isTerminalUiStatus,
  driverFromRide,
} from '../../src/utils/rideUiStatus.js'

test('mapBackendStatus maps storage contract to UI states', () => {
  assert.equal(mapBackendStatus('requested'), RIDE_STATUS.REQUESTING)
  assert.equal(mapBackendStatus('accepted'), RIDE_STATUS.MATCHED)
  assert.equal(mapBackendStatus('driver_arrived'), RIDE_STATUS.ARRIVED)
  assert.equal(mapBackendStatus('in_progress'), RIDE_STATUS.IN_PROGRESS)
  assert.equal(mapBackendStatus('completed'), RIDE_STATUS.COMPLETE)
  assert.equal(mapBackendStatus('cancelled'), RIDE_STATUS.CANCELLED)
})

test('paymentForReceipt prefers ledger payment', () => {
  const row = paymentForReceipt(
    { amount_cents: 1200, currency: 'USD', status: 'captured', captured_at: '2026-01-01T12:00:00Z', ride_id: 9 },
    { id: 9, pickup_location: 'A', dropoff_location: 'B' },
  )
  assert.equal(row.fare_cents, 1200)
  assert.equal(row.source, 'LEDGER')
})

test('driverFromRide prefers assigned_driver_name', () => {
  const d = driverFromRide({ driver_id: 7, assigned_driver_name: 'Sam Driver' })
  assert.equal(d.name, 'Sam Driver')
})

test('isTerminalUiStatus', () => {
  assert.equal(isTerminalUiStatus(RIDE_STATUS.COMPLETE), true)
  assert.equal(isTerminalUiStatus(RIDE_STATUS.REQUESTING), false)
})
