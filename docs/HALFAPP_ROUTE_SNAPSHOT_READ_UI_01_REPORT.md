# Final Report: HALFAPP_ROUTE_SNAPSHOT_READ_UI_01

**Verdict: GO**  
**Date:** 2026-05-22  
**Scope:** Read-only driver route snapshot / route truth UI over existing `route_snapshots` and ride provider fields. Not OSRM runtime proof. Not a navigation engine slice.

## Files changed

| Area | Files |
|------|--------|
| Backend read projection | `backend/services/route_snapshots_read.py` (new) |
| Snapshot public view | `backend/services/route_snapshots.py` — added `id` to `route_snapshot_public_view` |
| API | `backend/routes/drivers.py` — extended `GET /drivers/rides/{ride_id}/route-snapshots` |
| Backend tests | `backend/tests/test_route_snapshot_read_ui.py` (new) |
| Driver UI | `driver-app/src/components/cockpit/RouteTruthDetails.jsx` (new) |
| Driver utils | `driver-app/src/utils/routeTruthFormat.js` (new) |
| Integration | `TripTruthDetails.jsx`, `TripAuditReceipt.jsx`, `api.js` |
| Frontend tests | `driver-app/tests/unit/routeTruthDetails.test.js`, `cockpitLayout.test.js` |
| Engineering context | `driver-app/src/utils/engineeringIntelligenceContext.js` |

## Endpoint shape

`GET /drivers/rides/{ride_id}/route-snapshots` (read-only, driver access via `_driver_can_access_ride_truth`)

```json
{
  "ride_id": 123,
  "route_truth": {
    "current_provider": "haversine_fallback",
    "used_fallback": true,
    "osrm_runtime_claim": "not_proved",
    "production_routing_claim": "not_proved",
    "traffic_provider": "none",
    "route_confidence": "medium",
    "route_calculated_at": "..."
  },
  "snapshots": [
    {
      "id": 1,
      "snapshot_role": "quote",
      "route_provider": "haversine_fallback",
      "used_fallback": true,
      "distance_meters": 12345,
      "duration_seconds": 900,
      "geometry_hash": "...",
      "request_hash": "...",
      "response_hash": "...",
      "pricing_id": 123,
      "created_at": "..."
    }
  ],
  "copy": {
    "routing_label": "Estimated route",
    "osrm_status": "OSRM runtime not proved",
    "estimate_note": "Haversine estimate — not a live road-network route."
  },
  "truth_labels": ["BACKEND_OWNED", "READ_ONLY_ROUTE_SNAPSHOTS", "NO_PRODUCTION_OSRM_CLAIM"]
}
```

Uses existing field names (`snapshot_role`, `route_provider`, etc.). No invented metrics.

## UI behavior

- **`RouteTruthDetails`** — collapsed by default; loads snapshots when expanded.
- **`TripTruthDetails`** — embeds `RouteTruthDetails` when `showRouteProvider` (cockpit completed summary, active trip details).
- **`TripAuditReceipt`** — route truth section uses `RouteTruthDetails` with `rideId`.
- Shows: routing label, provider, fallback yes/no, OSRM status, snapshot roles, distance/duration, collapsed technical proof (snapshot id, geometry hash, timestamps).
- No map clutter, no route editing, no new dependencies.

## Route truth wording

| Label | Value |
|-------|--------|
| Fallback | “Estimated route” + estimate note (not road-network proof) |
| OSRM | “OSRM runtime not proved” |
| Production routing | `production_routing_claim: not_proved` (API only; not shown as a user-facing “production OSRM” claim) |

## OSRM claim status

**`osrm_runtime_claim: not_proved`** — unchanged. No production OSRM or road-accurate claims in driver `src` (guards pass; forbidden phrases only in test helpers / negative matchers).

## Commands run

```text
cd backend && python -m pytest -q
cd driver-app && npm test
cd driver-app && npm run build
cd driver-app && npm run test:e2e:ride-flow
```

## Test results

| Command | Result |
|---------|--------|
| Backend `pytest -q` | **262 passed** |
| `npm test` | **77 passed** |
| `npm run build` | **OK** |
| `npm run test:e2e:ride-flow` | **1 passed** |

## Remaining next slice

- **SELF_HOSTED_ROUTING_PROOF_V0_1 runtime** — Docker/OSRM on host; only then may `osrm_runtime_claim` change.
- Optional: polyline preview in audit (still read-only; separate from this slice).

## Closed lanes (not reopened)

HALFAPP_DRIVER_AUDIT_READ_UI_01, AUTH-001, RIDE-001..003, DRIVER-001B, DRIVER-002, cockpit E2E lock, dispatch/lifecycle/pricing logic.
