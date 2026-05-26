import test from 'node:test'
import assert from 'node:assert/strict'
import { riderStatusLabel, riderStatusStep } from '../../src/utils/riderStatus.js'

test('riderStatusLabel maps lifecycle states', () => {
  assert.equal(riderStatusLabel({ status: 'requested' }), 'Looking for a driver')
  assert.equal(riderStatusLabel({ status: 'accepted' }), 'Driver assigned')
  assert.equal(riderStatusLabel({ status: 'in_progress' }), 'On the way')
  assert.equal(riderStatusLabel({ status: 'completed' }), 'Trip complete')
  assert.equal(riderStatusLabel({ status: 'cancelled' }), 'Cancelled')
})

test('riderStatusStep tracks progress', () => {
  assert.equal(riderStatusStep({ status: 'requested' }), 1)
  assert.equal(riderStatusStep({ status: 'accepted' }), 2)
  assert.equal(riderStatusStep({ status: 'in_progress' }), 3)
  assert.equal(riderStatusStep({ status: 'completed' }), 4)
  assert.equal(riderStatusStep({ status: 'cancelled' }), 0)
})
