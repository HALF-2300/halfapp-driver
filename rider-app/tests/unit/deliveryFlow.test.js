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

describe('customer delivery flow surface', () => {
  it('wires delivery routes without replacing ride routes', () => {
    const app = readSrc('App.jsx')
    assert.match(app, /DeliveryOrderPage/)
    assert.match(app, /DeliveryOrderDetailPage/)
    assert.match(app, /path="\/delivery"/)
    assert.match(app, /path="\/ride\/:rideId"/)
  })

  it('creates, quotes, lists, views, and cancels delivery orders through API helpers', () => {
    const api = readSrc('utils/api.js')
    assert.match(api, /quoteDelivery/)
    assert.match(api, /createDeliveryOrder/)
    assert.match(api, /fetchMyDeliveryOrders/)
    assert.match(api, /fetchDeliveryOrder/)
    assert.match(api, /cancelDeliveryOrder/)
    assert.match(api, /\/delivery\/orders\/customer/)
  })

  it('renders transparent price breakdown and receipt states', () => {
    const create = readSrc('components/DeliveryOrderPage.jsx')
    const detail = readSrc('components/DeliveryOrderDetailPage.jsx')
    assert.match(create, /Transparent price breakdown/)
    assert.match(create, /Place delivery order/)
    assert.match(detail, /Status timeline/)
    assert.match(detail, /Receipt/)
    assert.match(detail, /local test hold/)
  })
})
