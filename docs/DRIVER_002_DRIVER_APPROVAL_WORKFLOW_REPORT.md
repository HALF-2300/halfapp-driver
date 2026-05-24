# DRIVER-002 — Formal Driver Approval Workflow Final Report

**Date:** 2026-05-22  
**Verdict:** **GO**

| Status item | Result |
|-------------|--------|
| DRIVER-002 formal approval workflow | **GO** |
| `driver_approvals` source of truth | **GO** |
| Admin approval endpoints | **GO** |
| Online / accept / dispatch gates | **GO** |

**Lane rule:** Do not continue modifying lifecycle, claim-lock, or dispatch-cascade logic in this lane unless explicitly rescoped.

---

## Summary

Drivers must be **admin-approved** before going online (`PATCH /drivers/me/status`), accepting rides (`POST /drivers/accept-ride/{id}`), or entering dispatch candidate pools. Approval state lives in **`driver_approvals`** — not `users.availability` strings. Suspended drivers cannot take new marketplace actions but may **complete an in-flight** ride assigned before suspension.

---

## Files changed

| Area | Paths |
|------|--------|
| Model | `backend/models/driver_approval.py` |
| Migration | `backend/alembic/versions/0012_driver_approvals_foundation.py` |
| Service | `backend/services/driver_approval.py` |
| Eligibility | `backend/services/claim_eligibility.py` |
| Auth | `backend/services/auth.py` (`create_user` + approval row) |
| Admin API | `backend/routes/admin_driver_approval.py` (mounted at `/admin`) |
| Driver API | `backend/routes/drivers.py` (online + ride actions) |
| Dispatch | `backend/services/ride_dispatch_cascade.py` via `is_driver_dispatch_available` |
| Tests | `backend/tests/test_driver_approval.py`, `backend/tests/driver_test_helpers.py`, explicit `driver_approval_status` in ride-flow tests |
| App | `backend/main.py` |

---

## Migration / table

**`driver_approvals`**

| Column | Notes |
|--------|--------|
| `driver_id` | FK `users`, unique |
| `status` | `pending`, `approved`, `rejected`, `suspended` (CHECK in migration) |
| `reason` | nullable |
| `reviewed_by` | nullable admin user id |
| `reviewed_at` | nullable |
| `created_at`, `updated_at` | audit |

---

## Default approval state

| Case | Behavior |
|------|----------|
| New driver (`create_user`, `POST /auth/register`) | **`pending`** |
| Existing drivers at migration `0012` | **Grandfathered `approved`** (one-time SQL backfill) |
| Tests needing marketplace access | Pass **`driver_approval_status="approved"`** to `create_user` or call **`approve_driver_for_tests()`** in `tests/driver_test_helpers.py` |
| Hidden test auto-approve | **Removed** — no `HALFAPP_ENV=test` bypass |

---

## Admin endpoints

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/admin/drivers?approval_status=pending` (alias `?status=`) | admin JWT |
| `PATCH` | `/admin/drivers/{driver_id}/approval` `{ status, reason? }` | admin JWT |

**PATCH response** includes: `driver_id`, `status`, `reason`, `reviewed_by`, `reviewed_at`, plus nested `driver` / `approval` views.

**Errors:** invalid filter/status → structured `400`/`422` with `error: invalid_approval_status`. Rider/driver tokens → **403**.

---

## Online / offline guard

`assert_driver_approved_for_online` in `PATCH /drivers/me/status`:

| Approval | HTTP | `detail.error` |
|----------|------|----------------|
| `pending` | 403 | `driver_not_approved` |
| `rejected` | 403 | `driver_rejected` |
| `suspended` | 403 | `driver_suspended` |
| `approved` | 200 | (if location / DRIVER-001B rules pass) |

---

## Accept ride guard

`assert_driver_approved_for_claim` runs **before** `claim_ride` (RIDE-002 lock unchanged):

| Approval | Result |
|----------|--------|
| `pending` | 403 `driver_not_approved` |
| `rejected` | 403 `driver_rejected` |
| `suspended` | 403 `driver_suspended` |
| `approved` | existing claim eligibility + atomic lock |

---

## Dispatch / cascade eligibility

`is_driver_dispatch_available` requires **`driver_approvals.status == approved`** plus `driver_status.online` and fresh location.

- `GET /drivers/available-rides` — non-approved see empty pool  
- `ride_dispatch_cascade._eligible_driver_ids` — skips non-approved via `is_driver_dispatch_available`  
- `GET /internal/available-drivers` — approved + online + fresh only  

---

## Legacy profile fields

| Field | Role |
|-------|------|
| `driver_approvals.status` | **Source of truth** for pending / approved / rejected / suspended |
| Active ride rows (`accepted`, `driver_arrived`, `in_progress`) | **Source of truth** for on-trip busy |
| `users.availability=busy` | Compatibility guard only (still blocks new claims) |
| `users.availability` pending/rejected/suspended | **No longer enforced** — approval table replaces interim string checks |

---

## Suspended driver with active ride

- **No ride corruption** on suspend.  
- **Cannot** accept / decline new pool rides / hide while suspended.  
- **May** `arrive` / `start` / `complete` on ride already assigned to that driver (documented MVP: finish in-flight trip; no admin cancel workflow in this task).

---

## Tests added / updated

**`test_driver_approval.py`:** defaults, admin list/approve/reject/suspend, role guards, online/accept blocks, dispatch pool, cascade skip pending, suspended complete in-flight, structured 422.

**Regression helpers:** `driver_approval_status="approved"` added across ride-flow test factories.

---

## Commands run (actual output)

```text
cd backend
python -m pytest tests/test_driver_approval.py -q
# 22 passed in ~14s

python -m pytest tests/test_driver_approval.py tests/test_auth_jwt_middleware.py tests/test_ride_001_transition_guards.py tests/test_ride_claim_lock_concurrency.py tests/test_ride_003_dispatch_cascade.py tests/test_driver_001b_presence_busy_guard.py -q
# 68 passed in ~40s

python -m pytest tests/test_ride_state_machine.py tests/test_ride_lifecycle.py tests/test_pricing_ledger_v01.py tests/test_route_snapshots_foundation.py tests/test_rbac.py -q
# 38 passed in 21.76s
```

---

## Blockers

None for DRIVER-002 scope.

---

## Intentionally not built

Document upload, Checkr/background checks, insurance verification, legal/compliance workflows, Stripe/payments, OSRM runtime, Redis matching, WebSockets, push notifications, admin dashboard redesign, UI redesign, claim-lock rewrite, lifecycle rewrite, dispatch cascade rewrite, full incident workflow for suspended active rides.

## Post-GO follow-up (not DRIVER-002 scope)

- **`hide` / `decline-dispatch`:** No approval guard; mutations are per-driver visibility or dispatch-log only on unassigned rides / active offers (cascade pool is approval-filtered). Acceptable for GO.
- **`decline-ride`:** Suspended driver with an **accepted** ride can still release the ride to the pool (no `assert_driver_can_perform_ride_action`). Track in test-isolation or a small guard lane — see `docs/HALFAPP_DRIVER_APPROVAL_GATE_01_REPORT.md` § Follow-up.
- **Test approval default:** `HALFAPP_ENV=test` only in pytest `conftest`; use `driver_approval_status=` or `tests/driver_test_helpers.approve_driver_for_tests()` explicitly in tests.
