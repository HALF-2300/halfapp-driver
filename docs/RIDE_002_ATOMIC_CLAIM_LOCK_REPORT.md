# RIDE-002 — Atomic Claim Lock for Ride Accept / Decline

**Date:** 2026-05-22  
**Verdict:** **GO**

## Summary

Ride accept uses a single driver endpoint with database-level atomic claim (`SELECT … FOR UPDATE` + conditional `UPDATE`). Exactly one driver wins under concurrent load; losers receive structured HTTP 409. Ineligible drivers receive HTTP 403 without mutating the ride. Decline on unassigned pool rides does not claim; full dispatch timeout/cascade remains deferred to RIDE-003.

## Claim endpoint

| Item | Value |
|------|--------|
| **Method / path** | `POST /drivers/accept-ride/{ride_id}` |
| **Router** | `backend/routes/drivers.py` (`prefix="/drivers"`) |
| **Auth** | Bearer JWT, `require_role("driver")` (`DRIVER_ACCESS`) |
| **Decline (no claim)** | `POST /drivers/decline-ride/{ride_id}` — valid only from `accepted` assigned to caller; unassigned `requested` → 409, ride unchanged |

## Lock / atomic update mechanism

Implemented in `OpenBoardDispatchPolicy.claim_ride` (`backend/services/dispatch.py`):

1. `SELECT … FOR UPDATE` on the ride row (serializes competing transactions on PostgreSQL).
2. Conditional `UPDATE` with `WHERE id = :ride_id AND driver_id IS NULL AND status = 'requested'`.
3. On success: `driver_id`, `status = accepted`, `accepted_at = now()` (no separate `claimed_at` column).
4. `rowcount != 1` → `RideAlreadyClaimed` / `RideNotAvailable` → HTTP 409 with `claim_conflict_detail()`.

## Driver eligibility (403, no ride mutation)

`assert_driver_eligible_for_claim` (`backend/services/claim_eligibility.py`), invoked from `accept_ride` after ride-not-found and **before** policy claim:

| Check | Failure |
|--------|---------|
| `is_active` | 403 `account_deactivated` |
| Profile `availability` in `pending`, `rejected`, `suspended` | 403 (proxy until DRIVER-002 approval column) |
| Profile `busy` or another active ride (`accepted` / `driver_arrived` / `in_progress`) | 403 `driver_busy` |
| Effective presence ≠ `available` | 403 `driver_offline` |
| Wrong JWT lane (rider/admin) | 403 via RBAC (before handler) |

Profile availability is captured before presence sync so `PUT /drivers/presence` cannot clear blocked approval strings.

## Conflict response (409)

Losers receive FastAPI `detail` object from `claim_conflict_detail()`:

```json
{
  "detail": "Ride already claimed",
  "ride_id": 1,
  "claim_result": "lost",
  "truth_status": "backend_conflict",
  "reason": "ride_already_claimed",
  "state_changed": false,
  "current_status": "accepted",
  "assigned_driver_id": 42
}
```

No private driver PII beyond `assigned_driver_id` (existing contract). Losing driver is not assigned the ride (`GET /drivers/my-rides` excludes it).

## Decline / dispatch cascade

- **Decline:** releases assigned `accepted` ride back to `requested` with optional `lifecycle_reason`; does not assign `driver_id` on pool rides.
- **Hide/dismiss:** `POST /drivers/rides/{ride_id}/hide` for unassigned `requested` (visibility only).
- **Deferred (RIDE-003):** timeout-driven cascade, broadcast decline fan-out, Redis locks, push.

## Concurrent accept test

| Metric | Value |
|--------|--------|
| File | `backend/tests/test_ride_claim_lock_concurrency.py` |
| Drivers | **10** (`COMPETING_DRIVER_COUNT`) |
| Expected | 1× HTTP 200, 9× HTTP 409 |
| DB proof | Single `driver_id` on ride; winner id matches 200 response body |

## Test results

Command:

```text
cd backend
python -m pytest tests/test_ride_claim_eligibility.py tests/test_ride_claim_lock_concurrency.py tests/test_ride_transparency_and_claim_conflict.py tests/test_ride_state_machine.py tests/test_dispatch_auditability.py tests/test_ride_lifecycle.py tests/test_ride_settlement_ledger.py tests/test_route_snapshots_foundation.py tests/test_ride_flow_ui_proof.py -v --tb=no
```

Output (2026-05-22):

```text
============================= 51 passed in 29.73s =============================
```

### Required scenarios

| ID | Scenario | Status |
|----|----------|--------|
| A | 10-way concurrent accept | PASS |
| B | Offline / pending / rejected / suspended / busy / rider token → 403 | PASS (`test_ride_claim_eligibility.py`) |
| C | Second accept after success → 409 | PASS |
| D | Winner/loser `my-rides` refresh | PASS (`test_winner_and_loser_refresh_state_after_concurrent_claim`) |
| E | Lifecycle, settlement, route snapshots, dispatch audit, ride-flow UI proof | PASS |

Driver-app trust E2E (`driver-app/tests/trust-mock-off/ride-transparency-conflict.spec.ts`) not re-run in this task (requires Playwright + live stack).

## Files changed

| File | Change |
|------|--------|
| `backend/services/claim_eligibility.py` | **New** — eligibility guards |
| `backend/routes/drivers.py` | Eligibility + conflict ordering; 403 for driver-unavailable |
| `backend/services/presence.py` | Do not overwrite blocked profile availability on presence sync |
| `backend/tests/test_ride_claim_eligibility.py` | **New** — 403/409 eligibility tests |
| `backend/tests/test_ride_state_machine.py` | Offline accept expects 403 |
| `docs/RIDE_LIFECYCLE_CONTRACT.md` | Document eligibility + atomic claim |
| `docs/RIDE_002_ATOMIC_CLAIM_LOCK_REPORT.md` | **This report** |

Pre-existing (verified, not authored in this pass): `backend/services/dispatch.py`, `backend/services/transparency.py`, `backend/tests/test_ride_claim_lock_concurrency.py`, transparency/audit tests.

## Blockers

None for RIDE-002 scope.

**Note:** Dedicated driver **approval** column (DRIVER-002) is not migrated yet; `users.availability` strings `pending` / `rejected` / `suspended` act as interim gates.

## Intentionally not built

- Redis distributed lock  
- Complex matching / nearest-driver  
- WebSockets / push notifications  
- Payments / Stripe / insurance / PBOT  
- OSRM runtime / Google / Mapbox routing changes  
- UI redesign  
- Full decline timeout cascade (RIDE-003)  
- `claimed_at` column (`accepted_at` used)
