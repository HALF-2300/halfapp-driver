# Final Report: HALFAPP_DRIVER_ROUTE_TRUTH_E2E_LOCK_01

**Verdict: GO**  
**Date:** 2026-05-22  
**Scope:** Playwright E2E lock for route truth / route snapshot read UI (`RouteTruthDetails` on trip audit receipt). Test-only slice + stable `data-testid` attributes.

## Summary

Added `npm run test:e2e:route-truth-flow` proving that a completed ride with backend route snapshots shows honest route truth on the **Trip audit** receipt: **Estimated route** label, **OSRM runtime not proved**, **production_routing_claim: not_proved**, snapshot list, and expandable technical proof (snapshot id, timestamp, geometry hash). No production OSRM or road-accurate claims appear in visible copy.

## Files changed

| File | Change |
|------|--------|
| `driver-app/tests/route-truth-flow-ui-proof.spec.ts` | New E2E spec `ROUTE_TRUTH_FLOW_UI_PROOF_V0_1` |
| `driver-app/playwright.route-truth-flow.config.js` | Isolated stack (ports **3037** / **8014**) |
| `driver-app/scripts/ensure-route-truth-flow-ports-free.mjs` | Pre-test port cleanup |
| `driver-app/package.json` | `pretest:e2e:route-truth-flow`, `test:e2e:route-truth-flow` |
| `driver-app/tests/helpers/rideFlowApi.ts` | `fetchRouteSnapshots()` helper |
| `driver-app/src/components/cockpit/RouteTruthDetails.jsx` | `route-truth-snapshot-id`, `route-truth-snapshot-timestamp`, `route-truth-request-hash` test ids |
| `driver-app/tests/unit/routeTruthDetails.test.js` | Assert E2E test ids in component source |

No backend lifecycle, dispatch, pricing, settlement, PSP, dossier, or AI changes.

## E2E path proven

1. **Seed ride** — `completeRideViaApi` (accept → complete creates route snapshots)
2. **API pre-check** — `GET /drivers/rides/{id}/route-snapshots`: `snapshots.length >= 1`, `used_fallback`, `osrm_runtime_claim` / `production_routing_claim` = `not_proved`, `routing_label` = `Estimated route`
3. **Open audit receipt** — `/#/driver/trips/{rideId}/audit`
4. **Expand route truth** — `route-truth-details-toggle` → wait for route-snapshots GET
5. **Assert route truth UI** — `route-truth-details`, `route-truth-routing-label` (Estimated route), `route-truth-osrm-status` (not proved), `route-truth-estimate-note`, `route-truth-snapshot-list`
6. **Expand technical route proof** — `route-truth-technical-toggle`
7. **Assert technical fields** — `route-truth-production-claim` (`not_proved`), `route-truth-snapshot-id`, `route-truth-snapshot-timestamp`, `route-truth-geometry-hash` (when backend provides hash)
8. **Forbidden routing scan** — no production OSRM / road-accurate / nearest-driver phrases in visible route body

## Route truth wording confirmation

| Claim | Shown in E2E |
|-------|----------------|
| Routing label | **Estimated route** |
| OSRM runtime | **not proved** |
| Production routing | **not_proved** |
| Fallback note | Haversine estimate (not live road-network) |
| Forbidden | production osrm, road-accurate, nearest-driver — **absent** |

## Technical proof expand/collapse result

- **Route truth section:** collapsed by default → body visible after toggle; snapshots load from API
- **Technical proof (route):** collapsed by default → `route-truth-technical-body` visible after `route-truth-technical-toggle` click

## OSRM claim status

- Backend and UI remain **`not_proved`** — no OSRM runtime GO claim introduced
- E2E asserts API + visible copy stay honest

## Commands run

```text
cd driver-app
npm test                                                  → 78 passed
npm run build                                             → OK
npm run test:e2e:ride-flow                                  → 1 passed
npm run test:e2e:audit-flow                                 → 1 passed
npm run test:e2e:route-truth-flow                           → 1 passed

cd backend
py -3.11 -m pytest tests -q                               → 265 passed, 1 skipped
```

## Test results

| Suite | Result |
|-------|--------|
| Driver unit | 78 passed |
| Driver build | OK |
| Ride-flow E2E | 1 passed |
| Audit-flow E2E | 1 passed |
| **Route-truth-flow E2E** | **1 passed** |
| Backend full | 265 passed, 1 skipped |

## Remaining next slice

Per program backlog — e.g. **OSRM Docker/VPS runtime proof** (infra, not driver UI claim), **Postgres claim-race suite**, or next driver trust slice from Report 03. Route snapshot read UI + route-truth E2E are locked; do not add route-truth features without a new slice ID.

## Closed lanes (not reopened)

HALFAPP_ROUTE_SNAPSHOT_READ_UI_01, HALFAPP_DRIVER_AUDIT_READ_UI_01, HALFAPP_DRIVER_AUDIT_E2E_LOCK_01, ride-flow E2E lock, cockpit polish, P0 backend lanes.
