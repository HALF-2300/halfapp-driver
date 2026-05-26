import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import {
  READINESS_BLOCKERS,
  buildDriverReadiness,
} from '../../src/utils/driverReadiness.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SRC = path.resolve(__dirname, '../../src')

function readSrc(rel) {
  return readFileSync(path.join(SRC, rel), 'utf8')
}

const readyProfile = {
  email: 'ready@example.com',
  name: 'Ready Driver',
  approval_status: 'approved',
  license_no: 'DLREADY1',
  vehicle: {
    make: 'Toyota',
    model: 'Prius',
    plate: 'READY1',
  },
  insurance_policy: 'POLICY-1',
  insurance_expires_at: '2027-05-25T00:00:00Z',
  vehicle_ready: true,
}

describe('DriverReadinessV1', () => {
  it('blocks going online when profile, vehicle, docs, insurance, backend, or approval are missing', () => {
    const readiness = buildDriverReadiness({
      accountProfile: {
        approval_status: 'pending',
        vehicle: { make: 'Not registered', model: '', plate: null },
      },
      backendUnavailable: true,
    })

    assert.equal(readiness.canGoOnline, false)
    const codes = readiness.blockers.map((item) => item.code)
    assert.ok(codes.includes(READINESS_BLOCKERS.BACKEND_UNAVAILABLE))
    assert.ok(codes.includes(READINESS_BLOCKERS.PROFILE_INCOMPLETE))
    assert.ok(codes.includes(READINESS_BLOCKERS.VEHICLE_MISSING))
    assert.ok(codes.includes(READINESS_BLOCKERS.LICENSE_DOCS_MISSING))
    assert.ok(codes.includes(READINESS_BLOCKERS.INSURANCE_MISSING))
    assert.ok(codes.includes(READINESS_BLOCKERS.APPROVAL_REQUIRED))
  })

  it('blocks when vehicle or insurance expiry has not been reviewed by operations', () => {
    const readiness = buildDriverReadiness({
      accountProfile: {
        ...readyProfile,
        vehicle_ready: false,
        insurance_expires_at: null,
      },
    })

    assert.equal(readiness.canGoOnline, false)
    const codes = readiness.blockers.map((item) => item.code)
    assert.ok(codes.includes(READINESS_BLOCKERS.VEHICLE_NOT_READY))
    assert.ok(codes.includes(READINESS_BLOCKERS.INSURANCE_EXPIRY_MISSING))
  })

  it('allows going online when beta readiness requirements are satisfied', () => {
    const readiness = buildDriverReadiness({ accountProfile: readyProfile })

    assert.equal(readiness.canGoOnline, true)
    assert.equal(readiness.blockers.length, 0)
    assert.equal(readiness.statusLabel, 'Ready to go online')
  })

  it('detects expired insurance as a practical beta blocker', () => {
    const readiness = buildDriverReadiness({
      accountProfile: {
        ...readyProfile,
        insurance_expires_at: '2024-01-01T00:00:00Z',
      },
      now: new Date('2026-05-25T00:00:00Z'),
    })

    assert.equal(readiness.canGoOnline, false)
    assert.equal(readiness.primaryBlocker.code, READINESS_BLOCKERS.INSURANCE_EXPIRED)
  })
})

describe('Driver app real-app shaping source guards', () => {
  it('MapHome gates online using DriverReadinessV1 before patching status', () => {
    const mapHome = readSrc('components/MapHome.jsx')
    assert.match(mapHome, /buildDriverReadiness/)
    assert.match(mapHome, /driverReadiness\.canGoOnline/)
    assert.ok(mapHome.indexOf('driverReadiness.canGoOnline') < mapHome.indexOf('patchDriverMeStatus'))
  })

  it('readiness reason and action are visible in the cockpit UI', () => {
    const card = readSrc('components/cockpit/DriverReadinessCard.jsx')
    assert.match(card, /driver-readiness-card/)
    assert.match(card, /You are not ready to go online yet|readiness\?\.headline/)
    assert.match(card, /Reason:/)
    assert.match(card, /readiness-action-btn/)
    assert.match(card, /Manual operations readiness is recorded/)
  })

  it('ride request card exposes accept, decline, expired, conflict, and obligation states', () => {
    const card = readSrc('components/cockpit/RideRequestCard.jsx')
    assert.match(card, /accept-ride-btn/)
    assert.match(card, /decline-ride-btn/)
    assert.match(card, /onClick=\{onAccept\}/)
    assert.match(card, /onDecline\?\.\(\{ reason: 'driver_declined' \}\)/)
    assert.match(card, /disabled=\{loadingBackend \|\| claimConflict \|\| expired\}/)
    assert.match(card, /ride-offer-expired/)
    assert.match(card, /ride-offer-conflict/)
    assert.match(card, /BETA_INCOMING_ESTIMATE_LABEL/)
    assert.match(card, /Manual operations required/)
  })

  it('completion receipt tells the beta truth', () => {
    const receipt = readSrc('components/cockpit/CompletionReceiptCard.jsx')
    assert.match(receipt, /Trip completed/)
    assert.match(receipt, /Fare obligation recorded/)
    assert.match(receipt, /Payout not executed/)
    assert.match(receipt, /Manual review required/)
  })

  it('driver-facing flow copy avoids real payout claims', () => {
    const surfaces = [
      readSrc('components/MapHome.jsx'),
      readSrc('components/cockpit/RideRequestCard.jsx'),
      readSrc('components/cockpit/MarketplaceBottomSheet.jsx'),
      readSrc('components/cockpit/RidePayoutSummary.jsx'),
      readSrc('components/cockpit/CompletionReceiptCard.jsx'),
    ].join('\n')

    assert.equal(/Driver total payout/i.test(surfaces), false)
    assert.equal(/added to earnings/i.test(surfaces), false)
    assert.equal(/deposited|cash out|instant payout|bank transfer complete/i.test(surfaces), false)
  })
})
