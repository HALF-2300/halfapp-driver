import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  AI_LIFECYCLE_EVENTS,
  DISPATCH_AI_STATES,
  ROUTE_ADVISORY_LABEL,
  FARE_SOURCE_DEMO,
  FARE_SOURCE_LEDGER,
  buildMatchAnalysisPrompt,
  buildRouteIntelligencePrompt,
  buildDeclineRedispatchPrompt,
  buildOpsMonitoringPrompt,
  buildTripCompletePrompt,
  resolveTripRecord,
  routeContextFromRide,
  formatRouteNoteForDisplay,
  createDeclineRedispatchManager,
} from '../../src/services/rideAiDispatch/index.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC_ROOT = path.resolve(__dirname, '../../src')

describe('production proof — cockpit wiring (source contract)', () => {
  it('MapHome wires all ride AI lifecycle hooks', () => {
    const mapHome = fs.readFileSync(path.join(SRC_ROOT, 'components/MapHome.jsx'), 'utf8')
    assert.ok(mapHome.includes('useRideAiDispatch'))
    assert.ok(mapHome.includes('rideAi.onIncomingMatch'))
    assert.ok(mapHome.includes('rideAi.onDriverAccept'))
    assert.ok(mapHome.includes('rideAi.onDriverDecline'))
    assert.ok(mapHome.includes('rideAi.onTripStart'))
    assert.ok(mapHome.includes('rideAi.onTripComplete'))
    assert.ok(mapHome.includes('getRidePayment'))
  })

  it('MarketplaceBottomSheet renders RideAiDispatchPanel', () => {
    const sheet = fs.readFileSync(
      path.join(SRC_ROOT, 'components/cockpit/MarketplaceBottomSheet.jsx'),
      'utf8',
    )
    assert.ok(sheet.includes('RideAiDispatchPanel'))
    assert.ok(sheet.includes('data-testid="ride-ai-dispatch-panel"') === false)
    assert.ok(sheet.includes('ride-ai-dispatch-panel') || sheet.includes('RideAiDispatchPanel'))
  })
})

describe('production proof — lifecycle prompt payloads', () => {
  const sensitive = ['WA-7823', 'Jane Rider', '47.606213', '-122.332091', 'Pioneer Courthouse']

  it('match analysis prompt is sanitized', () => {
    const prompt = buildMatchAnalysisPrompt({
      ride_id: 99,
      license_plate: 'WA-7823',
      rider_name: 'Jane Rider',
      pickup_latitude: 47.606213,
      pickup_longitude: -122.332091,
    })
    for (const token of sensitive) {
      assert.ok(!prompt.includes(token), `leaked ${token}`)
    }
    assert.ok(prompt.includes('match_analysis') || prompt.includes('proximity'))
  })

  it('route intelligence prompt carries advisory when not live', () => {
    const ctx = routeContextFromRide({ status: 'accepted' })
    const prompt = buildRouteIntelligencePrompt(ctx)
    assert.ok(prompt.includes('No live traffic source'))
    const display = formatRouteNoteForDisplay(ctx, 'Note body')
    assert.equal(display.slice(0, ROUTE_ADVISORY_LABEL.length), ROUTE_ADVISORY_LABEL)
  })

  it('route intelligence prompt is grounded when OSRM fields present on ride view', () => {
    const ctx = routeContextFromRide({
      route_provider: 'osrm_self_hosted',
      route_source: 'osrm_v5',
      route_calculated_at: '2026-05-25T18:43:11Z',
      route_used_fallback: false,
      route_provider_confidence: 0.91,
      distance_km: 9.5,
      duration_minutes: 14,
    })
    assert.equal(ctx.live, true)
    const prompt = buildRouteIntelligencePrompt(ctx)
    assert.ok(prompt.includes('"route_source": "osrm_v5"'))
    assert.ok(prompt.includes('"live_traffic": true'))
    assert.ok(!prompt.includes(ROUTE_ADVISORY_LABEL))
  })

  it('decline and ops monitoring prompts omit PII', () => {
    const decline = buildDeclineRedispatchPrompt({
      ride_id: 1,
      license_plate: 'WA-7823',
      rider_name: 'Secret',
    })
    const ops = buildOpsMonitoringPrompt({ ride_id: 2, customer_name: 'Secret' })
    assert.ok(!decline.includes('WA-7823'))
    assert.ok(!ops.includes('Secret'))
  })

  it('trip complete uses LEDGER TripRecord when payment present', () => {
    const record = resolveTripRecord(
      5,
      {
        id: 10,
        amount_cents: 1500,
        driver_payout_cents: 1080,
        status: 'captured',
        currency: 'USD',
      },
      925,
    )
    assert.equal(record.source, FARE_SOURCE_LEDGER)
    const prompt = buildTripCompletePrompt(record)
    assert.ok(prompt.includes('"source": "LEDGER"'))
    assert.ok(prompt.includes('ride_payments'))
  })

  it('trip complete uses DEMO_SIMULATION when payment missing', () => {
    const record = resolveTripRecord(5, null, null)
    assert.equal(record.source, FARE_SOURCE_DEMO)
    const prompt = buildTripCompletePrompt(record)
    assert.ok(prompt.includes('DEMO_SIMULATION'))
    assert.ok(prompt.includes('not production'))
  })
})

describe('production proof — PII final prompt capture', () => {
  it('writes sanitized prompt snapshot for audit', () => {
    const prompts = {
      match: buildMatchAnalysisPrompt({
        ride_id: 1,
        license_plate: 'OR-4412',
        rider_name: 'Audit Rider',
        pickup_location: '123 Main St',
        pickup_latitude: 45.52,
        pickup_longitude: -122.67,
      }),
      route: buildRouteIntelligencePrompt(routeContextFromRide({})),
      complete_demo: buildTripCompletePrompt(resolveTripRecord(2, null)),
      complete_ledger: buildTripCompletePrompt(
        resolveTripRecord(3, {
          amount_cents: 800,
          driver_payout_cents: 576,
          status: 'captured',
        }),
      ),
    }
    const forbidden = ['OR-4412', 'Audit Rider', '123 Main St', '47.606213', '-122.332091']
    for (const [name, text] of Object.entries(prompts)) {
      for (const token of forbidden) {
        assert.ok(!text.includes(token), `${name} leaked ${token}`)
      }
    }
    const outDir = path.resolve(__dirname, '../../test-results/ride-ai-dispatch-proof')
    fs.mkdirSync(outDir, { recursive: true })
    fs.writeFileSync(
      path.join(outDir, 'sanitized-prompt-snapshot.json'),
      JSON.stringify(prompts, null, 2),
      'utf8',
    )
    assert.ok(fs.existsSync(path.join(outDir, 'sanitized-prompt-snapshot.json')))
  })
})

describe('production proof — decline state machine', () => {
  it('DECLINED then REDISPATCHING without duplicate timers', async () => {
    const m = createDeclineRedispatchManager()
    m.setMatched()
    assert.equal(m.decline({ delayMs: 40 }), 'declined')
    assert.equal(m.getState(), DISPATCH_AI_STATES.DECLINED)
    assert.equal(m.decline({ delayMs: 40 }), 'ignored')
    await new Promise((r) => setTimeout(r, 60))
    assert.equal(m.getState(), DISPATCH_AI_STATES.REDISPATCHING)
  })
})

describe('production proof — lifecycle event constants', () => {
  it('maps UI stages to distinct AI events', () => {
    const events = [
      AI_LIFECYCLE_EVENTS.MATCH_ANALYSIS,
      AI_LIFECYCLE_EVENTS.ROUTE_INTELLIGENCE,
      AI_LIFECYCLE_EVENTS.DECLINE_REDISPATCH,
      AI_LIFECYCLE_EVENTS.OPS_MONITORING,
      AI_LIFECYCLE_EVENTS.TRIP_COMPLETE,
    ]
    assert.equal(new Set(events).size, events.length)
  })
})
