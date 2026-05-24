import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { trafficSignalsToMapMarkers } from '../../src/utils/trafficSignalMarkers.js'

describe('traffic signal map markers', () => {
  it('converts official signals to optional map markers', () => {
    const markers = trafficSignalsToMapMarkers([
      { id: 'a1', title: 'Crash on I-5', latitude: 45.52, longitude: -122.68 },
    ])
    assert.equal(markers.length, 1)
    assert.equal(markers[0].kind, 'traffic_incident')
    assert.equal(markers[0].source, 'traffic_signal')
  })

  it('returns empty on invalid coords', () => {
    assert.equal(trafficSignalsToMapMarkers([{ title: 'x' }]).length, 0)
  })
})
