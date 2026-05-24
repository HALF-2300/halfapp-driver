import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { getIdempotencyKey, clearIdempotencyKey } from '../../src/utils/idempotencyKeys.js'
import { resilientFetch } from '../../src/utils/resilientFetch.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const apiSrc = readFileSync(path.resolve(__dirname, '../../src/utils/api.js'), 'utf8')
const mapSrc = readFileSync(path.resolve(__dirname, '../../src/components/MapHome.jsx'), 'utf8')
const bannerSrc = readFileSync(
  path.resolve(__dirname, '../../src/components/CockpitNetworkBanner.jsx'),
  'utf8'
)

describe('Slice 03 idempotency keys', () => {
  it('returns a stable key per ride and action until cleared', () => {
    const k1 = getIdempotencyKey(42, 'accept')
    const k2 = getIdempotencyKey(42, 'accept')
    assert.equal(k1, k2)
    clearIdempotencyKey(42, 'accept')
    const k3 = getIdempotencyKey(42, 'accept')
    assert.notEqual(k1, k3)
  })
})

describe('Slice 03 resilientFetch', () => {
  it('does not retry GET by default', async () => {
    let calls = 0
    const original = globalThis.fetch
    globalThis.fetch = async () => {
      calls += 1
      return new Response('bad', { status: 503 })
    }
    try {
      const res = await resilientFetch('http://example.test/x', { method: 'GET' })
      assert.equal(res.status, 503)
      assert.equal(calls, 1)
    } finally {
      globalThis.fetch = original
    }
  })
})

describe('Slice 03 driver API wiring', () => {
  it('ride writes use callRideWrite with Idempotency-Key path', () => {
    assert.match(apiSrc, /callRideWrite/)
    assert.match(apiSrc, /Idempotency-Key/)
    assert.match(apiSrc, /resilientFetch/)
    assert.match(apiSrc, /action: 'accept'/)
    assert.match(apiSrc, /action: 'complete'/)
  })
})

describe('Slice 03 cockpit network banner', () => {
  it('MapHome renders offline/degraded banner component', () => {
    assert.match(mapSrc, /CockpitNetworkBanner/)
    assert.match(mapSrc, /networkDegraded/)
    assert.match(bannerSrc, /data-testid="cockpit-offline-banner"/)
    assert.match(bannerSrc, /data-testid="cockpit-degraded-banner"/)
  })
})
