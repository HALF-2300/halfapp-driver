import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC = path.resolve(__dirname, '../../src')

function readSrc(rel) {
  return readFileSync(path.join(SRC, rel), 'utf8')
}

describe('courier delivery jobs surface', () => {
  it('keeps delivery jobs distinct from ride trips', () => {
    const app = readSrc('App.jsx')
    const nav = readSrc('components/BottomNavigation.jsx')
    assert.match(app, /\/driver\/deliveries/)
    assert.match(app, /DeliveryJobs/)
    assert.match(nav, /id: 'deliveries'/)
    assert.match(nav, /path: '\/driver\/deliveries'/)
    assert.match(app, /\/driver\/trips/)
  })

  it('calls delivery offer and lifecycle APIs', () => {
    const api = readSrc('utils/api.js')
    assert.match(api, /getDeliveryOffers/)
    assert.match(api, /acceptDeliveryOrder/)
    assert.match(api, /pickupDeliveryOrder/)
    assert.match(api, /startDeliveryOrder/)
    assert.match(api, /deliverDeliveryOrder/)
    assert.match(api, /\/delivery\/courier\/orders/)
  })

  it('shows GPS health without blocking delivery actions', () => {
    const page = readSrc('components/DeliveryJobs.jsx')
    const contracts = readSrc('utils/deliveryContracts.js')
    assert.match(page, /Location health/)
    assert.match(page, /GPS denied, stale, or unavailable/)
    assert.match(contracts, /Location permission denied/)
    assert.match(contracts, /Stale location/)
  })
})
