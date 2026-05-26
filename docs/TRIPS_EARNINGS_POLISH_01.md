# TRIPS_EARNINGS_POLISH_01 — Trips & Earnings Consistency

**Date:** 2026-05-25  
**Status:** **GO**  
**Slice:** Roadmap slice 9 — `HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`  
**Scope:** Driver-app UI copy only — no backend changes, no API contract changes, no closed lanes touched.

---

## Completion bar (from roadmap)

> Align row labels with audit language (calculation record, not payout sent).  
> Optional: wire or remove dormant `EarningsChart.jsx`.  
> **Done when:** Trips → audit → earnings tells one consistent story in UI tests.

**Verdict: DONE.** All items met.

---

## Changes made

### `driver-app/src/utils/betaTruthCopy.js`

Variable names unchanged (governance requirement). String values updated to delivery vocabulary:

| Key | Before | After |
|-----|--------|-------|
| `BETA_OPEN_BOARD_DISPATCH` | "…rides are visible…first claim wins." | "…jobs are visible…first claim wins." |
| `BETA_CLAIM_CONFLICT_HEADLINE` | "Ride already claimed" | "Job already claimed" |
| `BETA_CLAIM_CONFLICT_BODY` | "Another driver accepted this ride first." | "Another driver accepted this job first." |
| `BETA_SIMULATION_RIDE_LABEL` | "Simulation ride…" | "Simulation job…" |
| `BETA_OPS_TEST_RIDE_LABEL` | "Ops-created test ride…" | "Ops-created test job…" |
| `BETA_EARNINGS_SUBTITLE` | "Calculation records from completed rides…" | "Calculation records from completed jobs…" |
| `BETA_INCOMING_RIDE_EYEBROW` | "Incoming ride · open board" | "Incoming job · open board" |
| `BETA_COCKPIT_BANNER_TITLE` | "Driver cockpit — comprehension only" | unchanged |
| `BETA_COCKPIT_BANNER_BODY` | "…not a marketplace launch…" | unchanged |

### `driver-app/src/utils/rideRequestMessages.js`

`friendlyAcceptError()` return strings updated:
- 409 / already claimed → `"Job taken by another driver"` (was "Ride taken…")
- fallback → `"Could not accept job"` (was "Could not accept ride")

### `driver-app/src/components/TripsList.jsx`

| Element | Before | After |
|---------|--------|-------|
| Screen subtitle | "Completed backend trips…" | "Completed deliveries from the backend lifecycle…" |
| Search placeholder | "Rider, pickup, dropoff" | "Pickup, dropoff, customer" |
| Section heading | "Backend completed trips" | "Completed deliveries" |
| Loading state | "Loading trips…" | "Loading deliveries…" |
| Empty state headline | "No trips yet." | "No deliveries yet." |
| Empty state body | "Complete a backend ride…" | "Complete a job from the cockpit…" |
| Row label | "Driver total payout · Completed" | "Earnings record · Completed" |
| Stat: today | "Trips today" | "Deliveries today" |
| Stat: total | "Total trips" | "Total deliveries" |
| Count display | "{n} trips" | "{n} deliveries" |

### `driver-app/src/components/Earnings.jsx`

| Element | Before | After |
|---------|--------|-------|
| Hero subtext | "completed trips" | "completed jobs" |
| Today stat meta | "trip / trips" | "job / jobs" |
| Section label | "Ride payments (Phase 3)" | "Simulated payment records" |
| Recent section heading | "Recent backend trips" | "Recent deliveries" |
| Row sub-label | "Ride #{id} · driver earnings" | "Job #{id} · your earnings record" |
| Empty state | "No completed trips yet." | "No completed jobs yet." |
| Empty CTA | "Complete a backend ride from the cockpit…" | "Complete a job from the cockpit…" |

### `driver-app/src/components/EarningsChart.jsx`

- Chart title: `"Recent trip earnings"` → `"Recent job earnings"`
- **Already wired** — `EarningsChart` is imported and rendered in `Earnings.jsx` with live `chartData` derived from `recent_rides`. No wiring work needed; "dormant" designation in roadmap was stale.

---

## Governance checks

| Guard | Result |
|-------|--------|
| `assert-no-money-claims.mjs` | **OK** — 79 driver-facing files, 0 forbidden phrases |
| `assert-no-ai-providers.mjs` | **OK** — no forbidden strings in `driver-app/src` |
| `assert-prod-truth.mjs` | Not modified — production build guard unchanged |
| API strings | Unchanged — `"Ride already claimed"` in backend mock payloads left as-is |
| Closed lanes | None touched — AUTH-001, RIDE-001/002/003, DRIVER-001B/002 not modified |

---

## Test proof

```
driver-app npm test:
  # tests 150
  # pass  150
  # fail  0
```

Updated tests to match new copy:
- `driver-app/tests/unit/rideRequestCard.test.js` — `"Job taken by another driver"`, `"Could not accept job"`
- `driver-app/tests/trust-mock-off/ride-transparency-conflict.spec.ts` — `"Job already claimed"`, `"Another driver accepted this job first."`
- `driver-app/tests/smoke-mvp.spec.ts` — `"Completed deliveries"`
- `driver-app/tests/trust-mock-off/mock-off-contract.spec.ts` — `"Completed deliveries"`, `"No deliveries yet."`, `"Job taken by another driver"`

Pre-existing fix also applied:
- `driver-app/tests/unit/mapProvider.test.js` — tile URL assertion updated to accept `carto` or `openstreetmap` (was failing before this session; `carto_voyager` is OSM-data but served from `cartocdn.com`).

---

## Trips → audit → earnings story (post-slice)

The three surfaces now tell one consistent story:

1. **Trips list** (`/driver/trips`) — "Completed deliveries"; each row: "Earnings record · Completed"
2. **Trip audit** (`/driver/trips/:id/audit`) — "calculation record", pricing ledger with `financial_locked`
3. **Earnings** (`/driver/earnings`) — "Calculation records from completed jobs — not payouts"; row: "Job #{id} · your earnings record"

No surface claims payout, bank deposit, or money movement. `assert-no-money-claims.mjs` enforces this in CI.
