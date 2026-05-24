import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  containsForbiddenRoutingClaim,
  formatDistanceMeters,
  formatDurationSeconds,
  isFallbackProvider,
  osrmStatusLabel,
  routingLabelFromPayload,
} from '../../src/utils/routeTruthFormat.js'

describe('routeTruthDetails', () => {
  it('formats distance and duration from snapshot fields', () => {
    assert.equal(formatDistanceMeters(1500), '1.5 km')
    assert.equal(formatDurationSeconds(900), '~15 min')
  })

  it('labels fallback honestly as estimated route', () => {
    assert.equal(isFallbackProvider('haversine_fallback'), true)
    const label = routingLabelFromPayload({
      route_truth: { used_fallback: true, current_provider: 'haversine_fallback' },
      copy: { routing_label: 'Estimated route' },
    })
    assert.equal(label, 'Estimated route')
  })

  it('keeps OSRM runtime as not proved', () => {
    const status = osrmStatusLabel({
      route_truth: { osrm_runtime_claim: 'not_proved' },
      copy: { osrm_status: 'OSRM runtime not proved' },
    })
    assert.match(status, /not proved/i)
    assert.equal(containsForbiddenRoutingClaim(status), false)
  })

  it('labels proved Portland evidence without production OSRM wording', () => {
    const status = osrmStatusLabel({
      route_truth: { osrm_runtime_claim: 'proved_portland_v0_1' },
    })
    assert.match(status, /proved/i)
    assert.equal(containsForbiddenRoutingClaim(status), false)
  })

  it('rejects forbidden production routing claims in copy', () => {
    assert.equal(containsForbiddenRoutingClaim('production OSRM is live'), true)
    assert.equal(containsForbiddenRoutingClaim('road-accurate routing'), true)
    assert.equal(containsForbiddenRoutingClaim('Haversine estimate'), false)
  })

  it('RouteTruthDetails exposes E2E test ids for snapshot technical proof', () => {
    const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '../../src/components/cockpit')
    const src = readFileSync(path.join(dir, 'RouteTruthDetails.jsx'), 'utf8')
    assert.ok(src.includes('route-truth-snapshot-id'))
    assert.ok(src.includes('route-truth-geometry-hash'))
    assert.ok(src.includes('route-truth-production-claim'))
  })
})
