# RIDE_FLOW_UI_PROOF_V0_2 — Final Report

**Date:** 2026-05-22  
**Verdict:** **GO**

UI ride loop is proven end-to-end on the v0.1 foundation (pricing ledger, Leaflet/OSM in-app map, external Google Maps only, haversine/OSRM routing abstraction with runtime OSRM frozen).

---

## UI flow proven

| Step | Proof |
|------|--------|
| Driver online | `setDriverAvailable` + `sheet-online-idle`; presence `available` before/after reload |
| Incoming request | Dev rider API `createRiderTrip` → `sheet-request-incoming` |
| Pricing quote | `ride-payout-summary`, `rider-platform-service-fee` = **$1.50** on incoming |
| Route metadata | `map-view` `data-route-provider` (incl. `haversine_fallback` when OSRM down); `data-traffic-provider` disabled/none; `data-google-fallback=false` |
| Accept | `accept-ride-btn` → `sheet-accepted_to_pickup` |
| Arrive / start | `advance-accepted_to_pickup` → `sheet-arrived_pickup` → `advance-arrived_pickup` → `sheet-in_progress` |
| Complete | `advance-in_progress` with `tip_cents=400`, `toll_cents=200` → `ride-flow-completed-summary` |
| Ledger UI | `pricing-financial-locked`, rider fare/commission/service fee, `driver-total-payout` |
| External nav | `open-pickup-google-maps` → `window.open` URL `https://www.google.com/maps/dir/?api=1&destination=...`; **no** `iframe[src*="google"]` |
| Refresh persistence | `page.reload()` → completed summary + locked pricing + $1.50 still visible; API ride still `completed` + `financial_locked` |

---

## Lifecycle statuses used (not migrated)

| UI sheet / driver state | Backend `status` |
|-------------------------|------------------|
| Incoming | `requested` |
| To pickup | `accepted` |
| At pickup | `driver_arrived` |
| In progress | `in_progress` |
| Completed | `completed` |

---

## Pricing fields shown / exposed

**UI (completed):** `ride-flow-completed-summary` — `pricing-financial-locked`, `rider-ride-fare`, `rider-platform-commission`, `rider-platform-service-fee` ($1.50), `driver-total-payout`.

**API (`GET /drivers/my-rides` after complete):**

- `status` = `completed`
- `pricing.financial_locked` = `true`
- `pricing.driver_shareable_fare_cents`
- `pricing.platform_commission_cents` (20% of shareable)
- `pricing.platform_service_fee_cents` = **150**
- `pricing.platform_revenue_cents` (via ledger)
- `pricing.driver_ride_payout_cents` / `driver_commission_cents`
- `pricing.driver_total_payout_cents` = ride payout + tip (tip **not** commissioned)
- `pricing.customer_total_cents` = shareable + 150 + tip + toll
- `pricing.tip_cents` = 400 (fixture)
- `pricing.toll_cents` = 200 (pass-through fixture)
- `route_provider` / `traffic_provider` / `traffic_aware=false`

---

## Ambiguous legacy fields (audited)

| Field | Meaning | UI handling |
|-------|---------|---------------|
| `fare_amount` | Driver payout in **dollars** when ledger present | Labels: “Est. driver payout” / “Driver payout” |
| `fare_earned` | Driver earnings on complete — **not** customer fare | Documented in `ridePricingDisplay.js` |

Legacy fields **not removed** (other flows may depend on them).

---

## Files changed (this proof lane)

| File | Change |
|------|--------|
| `driver-app/tests/ride-flow-ui-proof.spec.ts` | Full E2E: request → accept → arrive → start → complete; tip/toll fixtures; API ledger asserts; reload persistence; map provider accepts `haversine_fallback`; `customer_total_cents` exact sum assert |
| `driver-app/tests/helpers/rideFlowApi.ts` | Portland coords for rider trip creation |
| `docs/RIDE_FLOW_UI_PROOF_V0_2_STATUS.md` | This report |

Existing v0.1 UI (no new business scope): `RidePayoutSummary.jsx`, `MarketplaceBottomSheet.jsx`, `ridePricingDisplay.js`, `playwright.ride-flow.config.js`, `backend/tests/test_ride_flow_ui_proof.py`.

---

## Commands run (actual output)

### Backend (pricing + ride-flow + OSRM unit)

```
cd backend && python -m pytest tests/test_ride_flow_ui_proof.py tests/test_osrm_self_hosted_routing.py tests/test_pricing_ledger_v01.py -q
...............                                                          [100%]
15 passed in 5.38s
```

### Driver-app unit

```
cd driver-app && npm test
# tests 50, pass 50, fail 0
```

### E2E ride-flow (GO)

```
cd driver-app
$env:PLAYWRIGHT_RIDE_FLOW_BACKEND_PORT="8014"
$env:PLAYWRIGHT_RIDE_FLOW_PORT="3028"
npm run test:e2e:ride-flow

  ok 1 ... rider request → driver accept → start → complete with locked payout summary (8.0s)
  1 passed (12.8s)
```

Use default ports `8011` / `3024` when free; override env vars if ports are occupied.

### Screenshot

`driver-app/test-results/ride-flow-ui-proof/completed-payout-summary.png` (137 KB, generated on passing run).

---

## Test results summary

| Suite | Result |
|-------|--------|
| `test_ride_flow_ui_proof.py` + OSRM + pricing v0.1 | **15 passed** |
| Driver-app unit (`npm test`) | **50 passed** |
| `npm run test:e2e:ride-flow` | **1 passed** |
| External navigation standalone | Not re-run (port 3022 conflict); covered in ride-flow spec + `externalNavigation` unit tests |

---

## Intentionally not built

Stripe/payments, insurance billing, Checkr, PBOT export, OSRM runtime/Docker proof, Google Maps embed, Mapbox/paid traffic, surge, vehicle tiers, admin redesign, MapLibre migration, status rename migration.

**OSRM runtime:** remains **NO_GO** / frozen per `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` until Docker/VPS + health curl + proof script shows `osrm_self_hosted`.

---

## How to reproduce

```bash
curl http://127.0.0.1:8011/health   # after webServer starts

cd driver-app && npm run test:e2e:ride-flow

cd backend && python -m pytest tests/test_ride_flow_ui_proof.py tests/test_osrm_self_hosted_routing.py tests/test_pricing_ledger_v01.py -q
cd ../driver-app && npm test
```

See also `docs/RUNTIME_PROOF_PROCEDURE.md` (dependency order for OSRM; this UI lane does not require OSRM up).
