import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  GOOGLE_MAPS_FALLBACK_ENABLED,
  MAPBOX_TRAFFIC_ENABLED,
  TRAFFIC_PROVIDER,
  getMapDisplayConfig,
  route,
  resetProviderCallCountForTests,
} from '../../src/services/mapProvider.js'

describe('mapProvider v0.1', () => {
  it('defaults to OSM display without Google or Mapbox traffic', () => {
    assert.equal(GOOGLE_MAPS_FALLBACK_ENABLED, false)
    assert.equal(MAPBOX_TRAFFIC_ENABLED, false)
    assert.equal(TRAFFIC_PROVIDER, 'none')
    const cfg = getMapDisplayConfig()
    assert.ok(cfg.tileUrl.includes('openstreetmap'))
  })

  it('route placeholder does not enable paid providers', async () => {
    resetProviderCallCountForTests()
    const r = await route([45.52, -122.68], [45.53, -122.67])
    assert.ok(r.distanceKm > 0)
    assert.equal(r.trafficAware, false)
    assert.equal(r.trafficProvider, 'none')
  })
})
