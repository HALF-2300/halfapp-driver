import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { BETA_FORBIDDEN_PAYMENT_PHRASES } from '../../src/utils/betaTruthCopy.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC = path.resolve(__dirname, '../../src')

function readSrc(rel) {
  return readFileSync(path.join(SRC, rel), 'utf8')
}

function walkJs(dir, acc = []) {
  for (const name of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, name.name)
    if (name.isDirectory() && name.name !== 'node_modules') walkJs(full, acc)
    else if (/\.(jsx?|tsx?)$/.test(name.name)) acc.push(full)
  }
  return acc
}

describe('cockpit layout truth guards (HALFAPP_DRIVER_COCKPIT_LIGHTWEIGHT_UBER_POLISH_01)', () => {
  it('MapHome uses map-first DriverCockpitShell and DriverStatusBar', () => {
    const mapHome = readSrc('components/MapHome.jsx')
    assert.ok(mapHome.includes('DriverCockpitShell'))
    assert.ok(mapHome.includes('DriverStatusBar'))
    assert.ok(mapHome.includes('DriverCockpitShell'))
    assert.equal(mapHome.includes('HalfAppEngineeringIntelligence'), false)
  })

  it('App lazy-loads Engineering Intelligence (not on /driver path)', () => {
    const app = readSrc('App.jsx')
    assert.ok(app.includes('lazy') && app.includes('HalfAppEngineeringIntelligence'))
    assert.ok(app.includes('/engineering-intelligence'))
    assert.ok(app.includes('path={COCKPIT_PATH}'))
    assert.equal(app.match(/import HalfAppEngineeringIntelligence from/), null)
  })

  it('driver src has no dossier or AI provider endpoint strings', () => {
    const files = walkJs(SRC)
    const forbidden = [
      'supply/heartbeat',
      'demand/request',
      'trip/complete',
      'api.anthropic.com',
      'api.openai.com',
      ...BETA_FORBIDDEN_PAYMENT_PHRASES,
    ]
    for (const file of files) {
      const rel = path.relative(SRC, file).replace(/\\/g, '/')
      if (rel.includes('HalfAppEngineeringIntelligence')) continue
      if (rel === 'utils/betaTruthCopy.js') continue
      if (rel === 'constants/truthCopy.js' || rel === 'constants/dispatchCopy.js') continue
      if (rel === 'utils/api.js') continue
      if (rel === 'components/DriverSettings.jsx') continue
      const text = readFileSync(file, 'utf8')
      for (const needle of forbidden) {
        assert.equal(
          text.includes(needle),
          false,
          `${rel} must not contain ${needle}`
        )
      }
    }
  })

  it('PrimaryRideActionButton and TripTruthDetails exist for cockpit polish', () => {
    assert.ok(readSrc('components/cockpit/PrimaryRideActionButton.jsx').includes('primary-ride-cta'))
    const tripTruth = readSrc('components/cockpit/TripTruthDetails.jsx')
    assert.ok(tripTruth.includes('RouteTruthDetails'))
    const routeTruth = readSrc('components/cockpit/RouteTruthDetails.jsx')
    assert.ok(routeTruth.includes('trip-route-provider-value'))
    assert.ok(readSrc('utils/routeTruthFormat.js').includes('haversine_fallback'))
    assert.ok(readSrc('components/cockpit/MarketplaceBottomSheet.jsx').includes('TripTruthDetails'))
  })

  it('MarketplaceBottomSheet exposes primary CTAs per driver state', () => {
    const sheet = readSrc('components/cockpit/MarketplaceBottomSheet.jsx')
    assert.ok(sheet.includes('go-online-btn'))
    assert.ok(
      sheet.includes('accept-ride-btn') ||
        readSrc('components/cockpit/RideRequestCard.jsx').includes('accept-ride-btn')
    )
    assert.ok(sheet.includes('advance-'))
    assert.ok(sheet.includes('PrimaryRideActionButton'))
  })
})
