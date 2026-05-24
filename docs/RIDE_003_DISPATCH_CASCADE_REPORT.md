# RIDE-003 — Request Timeout + Dispatch Cascade Final Report

**Date:** 2026-05-22  
**Verdict:** **GO**

## Summary

Sequential dispatch offers prevent `requested` rides from hanging when drivers ignore, decline, or miss an offer. Timeouts cascade to the next eligible driver; after three failed attempts the ride is terminalized with `lifecycle_reason=no_drivers_available` (storage status `cancelled`). RIDE-002 atomic claim lock is unchanged and remains the accept source of truth.

## Migration / tables

| Artifact | Detail |
|----------|--------|
| **Table** | `ride_dispatch_log` (reused; not `RideClaimAttempt`) |
| **Migrations** | `0014_dispatch_cascade` — log table + ride columns; `0015_dispatch_log_reason` — `reason`, `created_at` when missing |
| **Ride columns** | `dispatch_driver_id` (current candidate), `dispatch_expires_at`, `dispatch_attempt_count` |

### Schema mapping (task → implementation)

| Task field | Implementation |
|------------|----------------|
| `current_candidate_driver_id` | `rides.dispatch_driver_id` |
| `dispatch_attempts_count` | `rides.dispatch_attempt_count` |
| `dispatch_expires_at` | `rides.dispatch_expires_at` |
| `no_drivers_reason` | `rides.lifecycle_reason = "no_drivers_available"` + `status = cancelled` |
| `result=sent` | `ride_dispatch_log.result = "sent"` (`pending` is legacy alias) |
| `skipped_ineligible` | `ride_dispatch_log.result = "skipped_ineligible"`, `attempt_number=0`, `reason` set |

## Config

| Variable | Default | Purpose |
|----------|---------|---------|
| `DISPATCH_REQUEST_TIMEOUT_SECONDS` | 30 | Offer TTL (alias: `HALFAPP_DISPATCH_TIMEOUT_SECONDS`) |
| `DISPATCH_MAX_ATTEMPTS` | 3 | Max sequential offers before exhaustion |
| `HALFAPP_OPEN_BOARD_DISPATCH` | unset / `0` in RIDE-003 tests | `1` disables sequential cascade (open-board pool) |

## Candidate eligibility

Uses existing gates (no new DRIVER-002 workflow):

- `driver_approvals.status = approved` (`query_dispatch_available_driver_ids` / `is_driver_dispatch_available`)
- `driver_status.online` + location freshness (DRIVER-001)
- Effective presence `available` (not offline/stale/disconnected/paused)
- No active ride (`accepted` / `driver_arrived` / `in_progress`)
- Not already offered/declined/timed out on this ride
- Legacy profile blocks via `claim_eligibility` patterns where applicable

**Ordering:** Haversine distance to pickup when coordinates exist; else `(inf, driver_id)` for deterministic sort.

## Services (deterministic processor)

| Function | Role |
|----------|------|
| `start_dispatch_for_ride` | First/next offer on unassigned `requested` ride |
| `process_dispatch_timeouts` | Expire overdue offers |
| `process_expired_dispatches` | Alias for timeout processor |
| `expire_current_attempt_and_cascade` | Timeout one ride and advance |
| `dispatch_next_candidate` | Alias for `start_dispatch_for_ride` |
| `refresh_open_dispatch_offers` | Sync processor on `GET /drivers/available-rides` (in-process v0.1; not a production job queue) |

## Endpoint behavior

| Endpoint | Change |
|----------|--------|
| `POST /rides/` (rider create) | Calls `start_dispatch_for_ride` after commit path |
| `GET /drivers/available-rides` | Runs `refresh_open_dispatch_offers`; filters via `ride_visible_to_driver` (only current candidate sees targeted offer) |
| `POST /drivers/accept-ride/{id}` | Unchanged claim lock; `record_dispatch_accepted`; sequential mode blocks non-candidates with 409 |
| `POST /drivers/decline-dispatch/{id}` | **New** — decline current offer, log `declined`, cascade without assigning `driver_id` |
| `POST /drivers/decline-ride/{id}` | Unchanged — release assigned `accepted` ride only |

## Decline / accept / exhaustion

- **Decline dispatch:** Current candidate only; others get 409; ride stays `requested`; next candidate offered.
- **Accept before timeout:** Claim lock wins; dispatch fields cleared; later `process_dispatch_timeouts` no-ops (ride not `requested`).
- **Max attempts:** Three timeouts/declines → `cancelled` + `lifecycle_reason=no_drivers_available`; no further offers.

## Tests

```text
cd backend
python -m pytest tests/test_ride_003_dispatch_cascade.py tests/test_ride_claim_lock_concurrency.py tests/test_ride_claim_eligibility.py tests/test_ride_state_machine.py tests/test_ride_lifecycle.py tests/test_dispatch_auditability.py -q
```

**Result (2026-05-22 verification):**

```text
python -m pytest tests/test_ride_003_dispatch_cascade.py tests/test_ride_claim_lock_concurrency.py tests/test_driver_001b_presence_busy_guard.py tests/test_ride_state_machine.py -v
27 passed in 22.00s
```

Full backend suite:

```text
python -m pytest tests/ -q
```

**Result:** `227 passed in 116.04s`

### Scenario coverage

| ID | Scenario | Status |
|----|----------|--------|
| A | No response → timeout → next driver | PASS |
| B | Accept before timeout → no second offer | PASS |
| C | Decline → cascade to B | PASS |
| D | Three failures → no drivers | PASS |
| E | Offline + busy skipped_ineligible logged; ineligible accept 409 | PASS |
| F | 10-driver claim lock regression | PASS |
| G | State machine / lifecycle | PASS |

## RIDE-002 regression

`test_ride_claim_lock_concurrency.py`: **1×200, 9×409** — claim lock not weakened. RIDE-003 tests use `monkeypatch` for `HALFAPP_OPEN_BOARD_DISPATCH=0` so open-board claim tests are unaffected.

## Files changed

- `backend/services/ride_dispatch_cascade.py` — cascade core, aliases, nearest sort, skipped_ineligible
- `backend/models/ride_dispatch_log.py` — `sent`, `skipped_ineligible`, `reason`, `created_at`
- `backend/routes/drivers.py` — visibility filter, decline-dispatch, accept integration
- `backend/routes/rider_rides.py` — start dispatch on create
- `backend/alembic/versions/0014_*`, `0015_*`
- `backend/tests/test_ride_003_dispatch_cascade.py`
- `backend/tests/test_v01_foundation.py`, `test_dossier_dispatch_ledger_slice.py` (alembic head)
- `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md`
- `docs/RIDE_003_DISPATCH_CASCADE_REPORT.md`

## Blockers

None for RIDE-003 scope.

## Intentionally not built

- Redis / job queue / WebSockets / push
- Stripe, insurance, PBOT, Checkr, OSRM runtime, Mapbox/Google
- UI redesign, formal DRIVER-002 expansion beyond existing approval table usage
- Route pricing changes
- Production cron/scheduler (documented: call `process_expired_dispatches` from scheduler later; v0.1 uses request-path refresh)
