# HALFAPP_ROUTE_SNAPSHOTS_FOUNDATION_01

**Date:** 2026-05-22  
**Scope:** Durable backend route evidence (`route_snapshots` table + read API). No OSRM runtime GO claims.

---

## Verdict

**GO** — `route_snapshots` table, quote/complete persistence, driver read endpoint, and backend tests green.

---

## What changed

| Area | Change |
|------|--------|
| Model | `backend/models/route_snapshot.py` — `route_snapshots` table |
| Migration | `0010_route_snapshots_foundation` |
| Service | `backend/services/route_snapshots.py` — create, hash, sanitize provenance |
| Wiring | `POST /rides/`, `POST /drivers/simulate-ride` → `snapshot_role=quote`; `POST /drivers/complete-ride/{id}` → `snapshot_role=complete` |
| API | `GET /drivers/rides/{ride_id}/route-snapshots` (read-only, driver-scoped) |
| Tests | `backend/tests/test_route_snapshots_foundation.py` (10 tests) |
| Route inventory | Added `/drivers/rides/{ride_id}/route-snapshots` to active MVP surface |

---

## Route snapshot contract

Each row answers:

- **Which ride?** `ride_id`
- **When / which lifecycle step?** `created_at`, `snapshot_role` (`quote`, `accept`, `complete`, `refresh`, `diagnostic`)
- **Which provider?** `route_provider` (e.g. `haversine_fallback`, `osrm_self_hosted`)
- **Fallback honest?** `used_fallback` boolean
- **Distance/duration used?** `distance_meters`, `duration_seconds`
- **Geometry evidence?** `geometry_polyline`, `geometry_hash` (nullable when no polyline)
- **Stable audit hashes?** `request_hash`, `response_hash` from sanitized JSON
- **Pricing link?** `pricing_id` → `ride_pricing.ride_id` when pricing row exists
- **Internal provenance?** `provenance_json` stored server-side; **not** exposed on the public API (secrets stripped before persist)

Route snapshots prove **what the backend recorded**. They do **not** prove production OSRM is running unless OSRM runtime proof is **GO**. `haversine_fallback` snapshots are honest fallback evidence, not road-network evidence.

---

## What is now proved

- Quote-time route estimates for rider-created and simulation rides create durable `quote` snapshots linked to `ride_pricing`.
- Completion creates a `complete` snapshot from final ride route fields + locked pricing (no silent re-route at complete).
- Provider and `used_fallback` are stored honestly from `RouteEstimate` or ride metadata.
- Drivers with dispatch visibility/claim/assignment access can read snapshot summaries; unrelated drivers get `403`.
- Request/response hashes are stable for identical sanitized payloads; provenance sanitization drops API keys, tokens, and raw URLs.

---

## What is still not proved

- Production OSRM runtime on deploy targets (`SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` remains **NO_GO** unless separately proven).
- Road-network geometry polyline storage (overview not requested from OSRM in v0.1).
- `accept` / `refresh` / `diagnostic` snapshot roles at accept-time or mid-ride refresh (only `quote` + `complete` wired in this slice).
- Driver-app UI surfacing of route snapshots (API only).

---

## Verification

```powershell
cd c:\Users\him\Desktop\halfapp-driver
py -3.11 scripts\print_active_routes.py

cd backend
python -m pytest -q
# 136 passed

cd ..\driver-app
npm run build
npm test
npm run test:e2e:ride-flow
npm run test:e2e:trust
```

---

## Remaining blockers

- OSRM runtime proof lane still separate.
- Financial settlement / payout ledger not in scope.
- Optional: wire `accept` snapshot on claim if accept-time route re-estimate is added later.

---

## Next recommended task

**`HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01`** (route-runtime truth) or **`HALFAPP_FINANCIAL_SETTLEMENT_BOUNDARY_OR_LEDGER_01`** (money truth), depending on program priority.
