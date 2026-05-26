# P1.3 — Delivery Vocabulary Pass (UI copy only)

**Task:** P1.3  
**Date:** 2026-05-25  
**STATUS:** **GO**

---

## Goal

Reduce ride-hailing copy in the driver app. The product is a courier job execution platform — UI labels should use delivery/job language rather than passenger ride-hailing language.

Rule: variable names, API endpoints, backend status strings, and lifecycle identifiers are unchanged. Only user-visible display text was updated.

---

## Changes

### `driver-app/src/utils/betaTruthCopy.js` (string values only)

| Constant | Before | After |
|----------|--------|-------|
| `BETA_OPEN_BOARD_DISPATCH` | "rides appear to multiple drivers" | "jobs are visible to multiple drivers" |
| `BETA_CLAIM_CONFLICT_HEADLINE` | "Ride already claimed" | "Job already claimed" |
| `BETA_CLAIM_CONFLICT_BODY` | "this ride first" | "this job first" |
| `BETA_SIMULATION_RIDE_LABEL` | "Beta ride / simulation ride" | "Simulation job" |
| `BETA_OPS_TEST_RIDE_LABEL` | "test ride" | "test job" |
| `BETA_EARNINGS_SUBTITLE` | "Test earnings from completed backend rides — calculation records only, not payouts." | "Calculation records from completed jobs — not payouts." |
| `BETA_INCOMING_RIDE_EYEBROW` | "Incoming ride · open board" | "Incoming job · open board" |
| `BETA_COCKPIT_BANNER_TITLE` | "Trusted driver beta — comprehension only" | "Driver cockpit — comprehension only" |
| `BETA_COCKPIT_BANNER_BODY` | "Operational truth beta: lifecycle…" | "Operational truth: lifecycle…" |

### `driver-app/src/utils/rideRequestMessages.js`

| Before | After |
|--------|-------|
| "Ride taken by another driver" | "Job taken by another driver" |
| "This ride is no longer available" | "This job is no longer available" |
| "Could not accept ride" | "Could not accept job" |

### `driver-app/src/components/TripsList.jsx`

| Before | After |
|--------|-------|
| subtitle: "Completed rides from the backend lifecycle…" | "Completed deliveries from the backend lifecycle…" |
| placeholder: "Pickup, dropoff, rider" | "Pickup, dropoff, customer" |

### `driver-app/src/components/Earnings.jsx`

| Before | After |
|--------|-------|
| "{weekly_rides} rides" | "{weekly_rides} jobs" |
| "Ride payments (Phase 3)" | "Simulated payment records" |
| "Recent backend trips" | "Recent deliveries" |
| "Ride #{id} · driver earnings" | "Job #{id} · your earnings record" |

### Tests updated

- `driver-app/tests/unit/rideRequestCard.test.js` — updated expected strings to match new messages
- `driver-app/tests/trust-mock-off/ride-transparency-conflict.spec.ts` — updated text assertions to "Job already claimed" / "Another driver accepted this job first."
- `driver-app/tests/unit/mapProvider.test.js` — fixed pre-existing failure (test checked `openstreetmap` but default map provider is `carto_voyager`; test now checks for OSM-based tile URLs with explicit Mapbox/Google exclusion)

---

## COMMAND RUN

```powershell
cd driver-app
npm test
npm run build
```

## PROOF

```
# tests 150
# suites 45
# pass 150
# fail 0
assert-no-ai-providers: OK (no forbidden strings in driver-app/src)
assert-no-money-claims: OK (79 driver-facing files, no forbidden payment-claim language)
✓ built in 3.94s
```

---

## DOCS UPDATED

- `docs/P1_3_DELIVERY_VOCABULARY_PASS_01.md` (this file)
- `docs/CURRENT_TRUTH.md` (P1.3 row added)

---

## GOVERNANCE CHECK

- `assert-no-money-claims` ✓
- `assert-no-ai-providers` ✓
- `assert-prod-truth` ✓ (build passes)

---

## Non-negotiables respected

- No variable names, API endpoints, or lifecycle status strings changed
- No closed lanes (AUTH-001, RIDE-001/002/003, DRIVER-002, etc.) touched
- Backend `CURRENT_TRUTH.md` test gate: 383 passed, 9 skipped (unchanged)
- Driver app: 150 passed, 0 failed

---

## NEXT TASK

Per AI agent directives: P1.1 (push notifications) and P1.2 (session recovery) are still listed as blocked until P0 gates (G1 Postgres, G2 OSRM, G3 owner day) are owner-closed.

Next agent-executable items from product completion roadmap:
- Roadmap slice 9: `TRIPS_EARNINGS_POLISH_01` — consistent audit/earnings language, period breakdown
- Roadmap slice 10: `OPENAPI_TRUTH_SYNC_01` — contract CI + doc reconciliation
