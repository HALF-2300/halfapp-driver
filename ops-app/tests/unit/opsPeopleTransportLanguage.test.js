import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC = path.resolve(__dirname, '../../src')

function readSrc(relativePath) {
  return readFileSync(path.join(SRC, relativePath), 'utf8')
}

describe('ops people-transport language', () => {
  it('keeps ride and delivery navigation explicitly separated', () => {
    const layout = readSrc('components/OpsLayout.jsx')
    assert.match(layout, /people-transport ride/)
    assert.match(layout, /\bRides\b/)
    assert.match(layout, /\bDrivers\b/)
    assert.match(layout, /to="\/deliveries"/)
    assert.match(layout, /ops-nav-deliveries/)
    assert.match(layout, /\bDeliveries\b/)
    assert.doesNotMatch(layout, /\bCouriers\b/)
  })

  it('uses rides in the ride list visible copy', () => {
    const list = readSrc('components/RideListPage.jsx')
    assert.match(list, /\bRides\b/)
    assert.match(list, /No rides/)
    assert.doesNotMatch(list, /\bDeliveries\b/)
  })
})
