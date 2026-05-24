import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { friendlyAcceptError } from '../../src/utils/rideRequestMessages.js'

describe('friendlyAcceptError', () => {
  it('maps ride_already_claimed to friendly copy', () => {
    const message = friendlyAcceptError({
      status: 409,
      detail: { reason: 'ride_already_claimed', detail: 'Ride already claimed' },
    })
    assert.equal(message, 'Ride taken by another driver')
  })

  it('avoids raw JSON in generic errors', () => {
    const message = friendlyAcceptError({ status: 500, message: '{"detail":"broken"}' })
    assert.equal(message, 'Could not accept ride')
  })
})
