import { describe, it, mock } from 'node:test'
import assert from 'node:assert/strict'

import {
  DISPATCH_AI_STATES,
  ROUTE_ADVISORY_LABEL,
  FARE_SOURCE_DEMO,
  FARE_SOURCE_LEDGER,
  createAiRateLimiter,
  createDeclineRedispatchManager,
  tripRecordFromLedgerPayment,
  tripRecordDemoSimulation,
  resolveTripRecord,
  formatTripRecordForPrompt,
  routeContextFromRide,
  formatRouteNoteForDisplay,
  buildMatchAnalysisPrompt,
  buildTripCompletePrompt,
  buildRouteIntelligencePrompt,
  sanitizeOperationalContext,
  scrubSensitiveStrings,
  streamAI,
  abortActiveStream,
  getActiveStreamId,
} from '../../src/services/rideAiDispatch/index.js'

describe('rideAiDispatch streamAI AbortController', () => {
  it('aborts previous fetch when a new stream supersedes', async () => {
    let firstSignal
    let secondStarted = false
    let firstAborted = false

    const slowFetch = ({ signal }) =>
      new Promise((resolve, reject) => {
        if (!secondStarted) {
          firstSignal = signal
          signal?.addEventListener?.('abort', () => {
            firstAborted = true
            reject(Object.assign(new Error('aborted'), { name: 'AbortError' }))
          })
        } else {
          resolve({ reply: 'second' })
        }
      })

    const first = streamAI({
      streamId: 'stream-a',
      prompt: 'a',
      fetchChat: slowFetch,
    })
    secondStarted = true
    const second = await streamAI({
      streamId: 'stream-b',
      prompt: 'b',
      fetchChat: slowFetch,
    })

    await first
    assert.equal(second.streamId, 'stream-b')
    assert.equal(second.reply, 'second')
    assert.equal(firstAborted, true)
    assert.equal(firstSignal?.aborted, true)
    abortActiveStream()
  })

  it('ignores stale streamId UI updates via shouldApplyStreamUpdate', async () => {
    const chunks = []
    await streamAI({
      streamId: 'keep',
      prompt: 'x',
      fetchChat: async () => ({ reply: 'ok' }),
      onChunk: (c, id) => chunks.push([c, id]),
    })
    assert.ok(chunks.every(([, id]) => id === 'keep'))
    assert.equal(getActiveStreamId(), null)
  })
})

describe('declineRedispatch manager', () => {
  it('does not stack repeated redispatch timeouts', async () => {
    const manager = createDeclineRedispatchManager()
    manager.setMatched()
    assert.equal(manager.decline({ delayMs: 50 }), 'declined')
    assert.equal(manager.getState(), DISPATCH_AI_STATES.DECLINED)
    assert.equal(manager.decline({ delayMs: 50 }), 'ignored')
    await new Promise((r) => setTimeout(r, 80))
    assert.equal(manager.getState(), DISPATCH_AI_STATES.REDISPATCHING)
    manager.dispose()
  })

  it('leaves MATCHED after decline (not stuck)', () => {
    const manager = createDeclineRedispatchManager()
    manager.setMatched()
    manager.decline({ delayMs: 10_000 })
    assert.notEqual(manager.getState(), DISPATCH_AI_STATES.MATCHED)
    assert.equal(manager.getState(), DISPATCH_AI_STATES.DECLINED)
  })
})

describe('TripRecord / FareBreakdown', () => {
  it('trip complete prompt uses structured ledger record only', () => {
    const record = tripRecordFromLedgerPayment(42, {
      id: 9,
      amount_cents: 1200,
      driver_payout_cents: 864,
      currency: 'USD',
      status: 'captured',
      captured_at: '2026-05-24T12:00:00Z',
    })
    assert.equal(record.source, FARE_SOURCE_LEDGER)
    const prompt = buildTripCompletePrompt(record)
    assert.ok(prompt.includes('"source": "LEDGER"'))
    assert.ok(prompt.includes('1200'))
    assert.ok(!prompt.includes('0.09'))
  })

  it('labels demo simulation in trip record', () => {
    const record = tripRecordDemoSimulation(7)
    assert.equal(record.source, FARE_SOURCE_DEMO)
    const json = formatTripRecordForPrompt(record)
    assert.ok(json.includes('DEMO_SIMULATION'))
  })

  it('resolveTripRecord prefers ledger over demo', () => {
    const record = resolveTripRecord(
      1,
      { amount_cents: 500, driver_payout_cents: 360, status: 'captured' },
      925,
    )
    assert.equal(record.source, FARE_SOURCE_LEDGER)
    assert.equal(record.fare.grossFareCents, 500)
  })
})

describe('route intelligence advisory label', () => {
  it('drops advisory when OSRM-grounded ride has route evidence', () => {
    const ctx = routeContextFromRide({
      route_provider: 'osrm_self_hosted',
      route_source: 'osrm_v5',
      route_calculated_at: '2026-05-25T18:43:11Z',
      route_used_fallback: false,
      route_provider_confidence: 0.91,
      distance_km: 11.2,
      duration_minutes: 16,
    })
    assert.equal(ctx.live, true)
    assert.equal(ctx.advisoryLabel, '')
    assert.equal(ctx.routeSource, 'osrm_v5')
    const display = formatRouteNoteForDisplay(ctx, 'Grounded note')
    assert.ok(!display.includes('NOT LIVE TRAFFIC'))
  })

  it('shows advisory label when no live route provider', () => {
    const ctx = routeContextFromRide({ status: 'accepted' })
    assert.equal(ctx.live, false)
    assert.equal(ctx.advisoryLabel, ROUTE_ADVISORY_LABEL)
    const display = formatRouteNoteForDisplay(ctx, 'Take I-5 south.')
    assert.ok(display.startsWith(ROUTE_ADVISORY_LABEL))
    const prompt = buildRouteIntelligencePrompt(ctx)
    assert.ok(prompt.includes('No live traffic source'))
  })
})

describe('PII prompt hygiene', () => {
  it('does not include raw license plate in sanitized prompt payload', () => {
    const payload = buildMatchAnalysisPrompt({
      ride_id: 1,
      license_plate: 'WA-7823',
      rider_name: 'Jane Rider',
      pickup_latitude: 47.6062,
      pickup_longitude: -122.3321,
    })
    assert.ok(!payload.includes('WA-7823'))
    assert.ok(!payload.includes('Jane Rider'))
    assert.ok(payload.includes('VEHICLE_TOKEN'))
  })

  it('scrubs plates from free text', () => {
    const out = scrubSensitiveStrings('Vehicle WA-7823 near zone')
    assert.ok(!out.includes('WA-7823'))
    assert.ok(out.includes('VEHICLE_TOKEN'))
  })

  it('sanitizeOperationalContext removes exact coordinates', () => {
    const sanitized = sanitizeOperationalContext({
      pickup_latitude: 47.606213,
      pickup_longitude: -122.332091,
    })
    assert.equal(sanitized.pickup_latitude, undefined)
    assert.ok(sanitized.pickup_lat_rounded != null)
  })
})

describe('rate limiting', () => {
  it('blocks rapid calls under min interval', () => {
    const limiter = createAiRateLimiter({ minIntervalMs: 3000, sessionBudget: 10 })
    assert.equal(limiter.canCall(10_000).ok, true)
    limiter.recordCall(10_000)
    assert.equal(limiter.canCall(10_100).ok, false)
    assert.equal(limiter.canCall(10_100).reason, 'min_interval')
    assert.equal(limiter.canCall(13_100).ok, true)
  })

  it('pauses after session budget', () => {
    const limiter = createAiRateLimiter({ minIntervalMs: 0, sessionBudget: 2 })
    limiter.recordCall(0)
    limiter.recordCall(10)
    assert.equal(limiter.canCall(20).ok, false)
    assert.equal(limiter.paused, true)
  })
})
