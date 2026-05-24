# RIDE-001 — State Machine Guards (Formal Audit + Gap Patch)

**Date:** 2026-05-22 (re-verified)  
**Verdict:** **GO**

| Status item | Result |
|-------------|--------|
| Correct repo proof | **GO** — `halfapp-driver` backend, not HalfStory |
| RIDE-001 transition guards | **GO** |
| Structured lifecycle 409s | **GO** |
| Terminal status immutability | **GO** |
| Event audit on valid transitions | **GO** (via existing `events` table) |
| Regression suites | **GO** — 82 tests passed (see below) |

**Lane rule:** Do not expand lifecycle, dispatch, payments, or architecture in this lane unless explicitly rescoped.

---

## Correct repo proof

| Artifact | Path | Present |
|----------|------|---------|
| Backend root | `C:\Users\him\Desktop\halfapp-driver\backend\` | yes |
| Lifecycle service | `backend/services/lifecycle.py` | yes — `next_ride_status`, `InvalidRideTransition`, `_TERMINAL_RIDE_STATUSES` |
| Transition errors | `backend/services/transition_errors.py` | yes — `invalid_state_transition_detail` |
| Contract doc | `docs/RIDE_LIFECYCLE_CONTRACT.md` | yes |
| Driver app (UI) | `driver-app/` (sibling; not the backend) | yes |
| RIDE-001 tests | `backend/tests/test_ride_001_transition_guards.py` | yes — 18 cases |
| Related tests | `test_lifecycle_contract.py`, `test_ride_lifecycle.py`, `test_ride_state_machine.py`, … | yes |

**Not the target:** `HalfStory` film engine — no `backend/services/lifecycle.py` there.

---

## Endpoints audited (active MVP — `backend/main.py`)

| Route | Method | Actor | Source status(es) | Target status | Guard |
|-------|--------|-------|-------------------|---------------|-------|
| `/rides/` | POST | rider | — | `requested` | create |
| `/rides/{id}/cancel` | POST | rider | `requested`, `accepted`, `driver_arrived`, `in_progress` | `cancelled` | `next_ride_status(..., CANCEL, customer)` |
| `/drivers/accept-ride/{id}` | POST | driver | `requested` | `accepted` | accept + claim policy |
| `/drivers/decline-ride/{id}` | POST | driver | `accepted` (assigned) | `requested` | `release_accepted_ride_to_pool` |
| `/drivers/arrive-pickup/{id}` | POST | driver | `accepted` | `driver_arrived` | `next_ride_status(..., ARRIVE)` |
| `/drivers/start-ride/{id}` | POST | driver | `driver_arrived` | `in_progress` | `next_ride_status(..., START)` |
| `/drivers/complete-ride/{id}` | POST | driver | `in_progress` | `completed` | `next_ride_status(..., COMPLETE)` + pricing lock |
| `/drivers/simulate-ride` | POST | driver | — | `requested` | dev flag only; no lifecycle transition matrix |

**No dedicated driver-cancel terminal endpoint** — driver backs out via `decline-ride` (`accepted` → `requested`). Rider cancel via `/rides/{id}/cancel`.

**Internal (non-HTTP):** dispatch exhaustion `requested` → `cancelled` (`lifecycle_reason=no_drivers_available`); not rider cancel.

---

## Allowed transition table

| From | Action | Actor | To |
|------|--------|-------|-----|
| `requested` | accept | driver | `accepted` |
| `accepted` | arrive | driver | `driver_arrived` |
| `driver_arrived` | start | driver | `in_progress` |
| `in_progress` | complete | driver | `completed` |
| `requested` | cancel | rider | `cancelled` |
| `accepted` | cancel | rider | `cancelled` |
| `driver_arrived` | cancel | rider | `cancelled` |
| `in_progress` | cancel | rider | `cancelled` |
| `accepted` | decline | driver | `requested` | pool release (documented in `RIDE_LIFECYCLE_CONTRACT.md`) |

**Additional enum values not on happy path:** `offered` (reserved, not API-emitted).

---

## Blocked transition table

| From | Attempted to | HTTP | Payload |
|------|----------------|------|---------|
| `requested` | `completed` / `driver_arrived` / `in_progress` | 409 | `invalid_state_transition` |
| `accepted` | `completed` | 409 | `invalid_state_transition` |
| `driver_arrived` | `completed` | 409 | `invalid_state_transition` |
| `completed` | any lifecycle action | 409 | `invalid_state_transition` |
| `cancelled` | `accepted` / `in_progress` / `completed` | 409 | `invalid_state_transition` or claim-blocked |
| invalid status string | any (unit) | — | `InvalidRideTransition` at `normalize_ride_status` |

Failed transitions do **not** mutate `rides.status` (see `test_invalid_transition_does_not_mutate_ride_status`).

---

## Structured error shape (proof)

HTTP **409** `detail` object:

```json
{
  "error": "invalid_state_transition",
  "code": "invalid_state_transition",
  "ride_id": 123,
  "from_status": "requested",
  "to_status": "completed",
  "state_changed": false,
  "message": "driver cannot complete ride in status requested"
}
```

Implemented in `backend/services/transition_errors.py`; raised via `drivers._raise_invalid_transition` and `rider_rides.cancel_ride`.

**Related 409s (not lifecycle matrix):** claim conflict detail, dispatch decline, repeat `complete-ride` when `financial_locked` (plain string — lock still holds).

---

## Completed ride immutability

| Rule | Enforcement |
|------|-------------|
| No status change after `completed` | `_assert_not_terminal` in `next_ride_status` |
| Financial lock | `ride_pricing.financial_locked` on complete; repeat complete → 409 |
| No route/pricing mutation after lock | `PricingLockedError` / locked guard on `complete-ride` |

---

## Event / audit behavior

**No dedicated `ride_events` table.** Valid transitions append:

- `services.metrics.record_event` → `events` (`entity_type=ride`, e.g. `ride.accepted`, `ride.arrived_pickup`, `ride.started`, `ride.completed`, `ride.cancelled`)
- `marketplace_ledger_events` mirrored from domain events

**Test:** `test_valid_accept_records_audit_event` asserts `ride.accepted` row after successful accept.

---

## Files changed (this re-verification)

| File | Change |
|------|--------|
| `backend/tests/test_ride_001_transition_guards.py` | Strengthened `cancelled` matrix asserts; added `test_valid_accept_records_audit_event` |
| `docs/RIDE_001_STATE_MACHINE_GUARDS_REPORT.md` | Re-verified report with fresh test output |

No changes to `lifecycle.py` transition table (already correct).

---

## Tests added/updated

**`test_ride_001_transition_guards.py` (18 tests):**

| Test | Covers |
|------|--------|
| `test_requested_to_accepted_succeeds` | valid |
| `test_accepted_to_driver_arrived_succeeds` | valid |
| `test_driver_arrived_to_in_progress_succeeds` | valid |
| `test_in_progress_to_completed_succeeds` | valid |
| `test_requested_to_cancelled_succeeds` | valid |
| `test_accepted_to_cancelled_succeeds` | valid |
| `test_requested_to_completed_rejected` | invalid skip |
| `test_accepted_to_completed_rejected` | invalid skip |
| `test_driver_arrived_to_completed_rejected` | invalid skip |
| `test_completed_to_cancelled_rejected` | terminal |
| `test_completed_to_in_progress_rejected` | terminal |
| `test_completed_to_accepted_returns_structured_conflict` | terminal |
| `test_cancelled_to_accepted_rejected` | terminal |
| `test_cancelled_to_completed_rejected` | terminal |
| `test_cancelled_to_in_progress_rejected` | terminal |
| `test_invalid_transition_does_not_mutate_ride_status` | no mutation |
| `test_completed_financial_lock_remains_intact` | immutability |
| `test_valid_accept_records_audit_event` | audit |

**Unit:** `test_lifecycle_contract.py::test_invalid_ride_status_string_raises_invalid_transition`

---

## Commands run (exact output summary)

```text
cd C:\Users\him\Desktop\halfapp-driver\backend

python -m pytest tests/test_ride_001_transition_guards.py tests/test_lifecycle_contract.py \
  tests/test_ride_state_machine.py tests/test_ride_lifecycle.py tests/test_rider_cancel.py \
  tests/test_ride_claim_lock_concurrency.py tests/test_pricing_ledger_v01.py -q
# 54 passed in 71.61s

python -m pytest tests/test_ride_001_transition_guards.py -v --tb=no
# 18 passed in 28.10s

python -m pytest tests/test_route_snapshots_foundation.py -q
# 10 passed in 13.00s
```

**Total regression for this audit:** 82 passed, 0 failed.

---

## Remaining gaps (non-blocking — PARTIAL notes)

| Gap | Severity |
|-----|----------|
| Repeat `complete-ride` when already `financial_locked` returns plain string 409, not `invalid_state_transition` | Low — lock intact |
| `hide-ride` / dispatch decline use non-lifecycle 409 strings | Low — not status transitions |
| No dedicated `ride_events` table | Documented — `events` + ledger sufficient |
| Unmounted `admin.py` state overrides | Out of scope |

---

## Intentionally not built

- Status renames; new statuses (`expired`, etc.)
- WebSockets, Redis, OSRM, Stripe, payments redesign
- HalfStory / film engine changes
- Full event-sourcing / `ride_events` table
- Driver-cancel as separate terminal status (decline-to-pool is the MVP pattern)

---

## What this proves

- Ride lifecycle guards are enforced in the **correct** backend before motion/completion side effects.
- Invalid transitions return structured **409** with `state_changed: false`.
- Terminal rides and financial locks hold under regression tests.
- Existing claim, pricing, lifecycle, and route snapshot suites remain green.

## What this does NOT prove

- Production dispatch fairness, payments settlement, or real-time push
- Every 409 in the API uses `invalid_state_transition` (claim/hide lanes differ by design)
