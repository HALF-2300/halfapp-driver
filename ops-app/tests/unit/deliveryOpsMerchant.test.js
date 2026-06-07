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

describe('ops and merchant delivery surfaces', () => {
  it('adds protected ops delivery monitor and public merchant portal routes', () => {
    const app = readSrc('App.jsx')
    const layout = readSrc('components/OpsLayout.jsx')
    assert.match(app, /DeliveryOpsPage/)
    assert.match(app, /DeliveryOpsDetailPage/)
    assert.match(app, /MerchantDeliveryPortal/)
    assert.match(app, /path="\/merchant"/)
    assert.match(layout, /ops-nav-deliveries/)
  })

  it('wires merchant accept, reject, preparing, and ready actions', () => {
    const merchant = readSrc('components/MerchantDeliveryPortal.jsx')
    const api = readSrc('utils/api.js')
    assert.match(merchant, /Accept/)
    assert.match(merchant, /Reject/)
    assert.match(merchant, /Start preparing/)
    assert.match(merchant, /Ready for pickup/)
    assert.match(api, /merchantAcceptDeliveryOrder/)
    assert.match(api, /merchantRejectDeliveryOrder/)
    assert.match(api, /merchantMarkDeliveryPreparing/)
    assert.match(api, /merchantMarkDeliveryReady/)
  })

  it('ops sees delivery settlement and refund eligibility', () => {
    const detail = readSrc('components/DeliveryOpsDetailPage.jsx')
    const api = readSrc('utils/api.js')
    assert.match(detail, /Financial summary/)
    assert.match(detail, /Refund eligibility/)
    assert.match(detail, /Settlement entries/)
    assert.match(api, /fetchDeliveryOrderForOps/)
    assert.match(api, /refundDeliveryOrder/)
  })
})
