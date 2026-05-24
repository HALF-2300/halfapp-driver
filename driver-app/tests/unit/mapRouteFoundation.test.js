import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  V01_ROUTE_PROVIDER,
  V01_TRAFFIC_PROVIDER,
  externalRoutingEnabled,
  resolveMapRouteFoundation,
} from '../../src/utils/mapRouteFoundation.js'

describe('v0.1 map route foundation', () => {
  it('defaults to leaflet OSM with traffic disabled', () => {
    const f = resolveMapRouteFoundation(null)
    assert.equal(f.routeProvider, V01_ROUTE_PROVIDER)
    assert.equal(f.trafficProvider, V01_TRAFFIC_PROVIDER)
    assert.equal(f.trafficAware, false)
    assert.equal(f.trafficSignalAware, false)
    assert.equal(f.googleMapsFallbackEnabled, false)
    assert.equal(f.mapboxTrafficEnabled, false)
    assert.equal(externalRoutingEnabled(f), false)
  })

  it('merges backend ride map fields when present', () => {
    const f = resolveMapRouteFoundation({
      route_provider: 'leaflet_osm',
      traffic_provider: 'odot_tripcheck',
      traffic_signal_aware: true,
      route_confidence: 'visual_only',
      route_calculated_at: '2026-05-22T12:00:00Z',
    })
    assert.equal(f.routeCalculatedAt, '2026-05-22T12:00:00Z')
    assert.equal(f.trafficProvider, 'odot_tripcheck')
    assert.equal(f.trafficSignalAware, true)
  })
})
