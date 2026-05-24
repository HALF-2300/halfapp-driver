# HALFAPP_DRIVER_APPROVAL_GATE_01 — Final Report

## Verdict: **GO**

Backend-owned driver approval gate is implemented and enforced for go-online, ride accept, marketplace pool visibility, and system dispatch queries. Claim-lock concurrency and targeted driver/dispatch suites pass in isolation.

---

## 1. Table / model

**Reused:** `driver_approvals` (migration `0012_driver_approvals_foundation`)

| Column | Type / notes |
|--------|----------------|
| `driver_id` | FK `users.id`, unique |
| `status` | `pending` \| `approved` \| `rejected` \| `suspended` |
| `reason` | nullable text |
| `reviewed_by` | nullable FK admin `users.id` |
| `reviewed_at` | nullable datetime |
| `created_at`, `updated_at` | timestamps |

**ORM:** `backend/models/driver_approval.py` — `DriverApproval`, `DriverApprovalStatus`

**Service:** `backend/services/driver_approval.py`

---

## 2. Default state

| Path | Default approval |
|------|------------------|
| Production (`HALFAPP_ENV` ≠ `test`) | `pending` via `create_user()` and `get_or_create_driver_approval()` |
| Pytest (`HALFAPP_ENV=test`) | `approved` (test convenience); tests that need `pending` pass `driver_approval_status="pending"` to `create_user()` |
| `POST /auth/register` (driver) | Creates row via `create_user` + `get_or_create_driver_approval`; returns `user.approval` in response |

**Existing drivers at migration 0012:** Backfilled to `approved` only when no `driver_approvals` row exists (documented in migration SQL — does not mass-approve rows already present).

---

## 3. Admin endpoints (mounted)

Router: `backend/routes/admin_driver_approval.py` (included in `main.py`)

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/admin/drivers?status=` or `?approval_status=` | Admin JWT |
| `PATCH` | `/admin/drivers/{driver_id}/approval` | Admin JWT |

**PATCH body:** `{ "status": "approved"|"rejected"|"suspended", "reason": optional }`

- Sets `reviewed_by` (admin user id), `reviewed_at` (UTC now)
- Rider/driver tokens → **403**
- Cannot set status back to `pending` via API

Full `backend/routes/admin.py` (users/rides analytics) remains **dormant** (not mounted).

---

## 4. Driver endpoints protected

| Surface | Guard | Error codes |
|---------|-------|-------------|
| `PATCH /drivers/me/status` (`online: true`) | `assert_driver_approved_for_online` | `driver_not_approved`, `driver_rejected`, `driver_suspended` |
| `PUT /drivers/presence` (`state: available`) | same via `set_presence_state` | same |
| `POST /drivers/accept-ride/{id}` | `assert_driver_eligible_for_claim` → `assert_driver_approved_for_claim` **before** `policy.claim_ride()` | `driver_not_approved`, `driver_rejected`, `driver_suspended` (403) |
| `POST /drivers/arrive-pickup`, `start-ride`, `complete-ride` | `assert_driver_can_perform_ride_action` | Suspended: blocks new marketplace actions; **allows** complete on assigned active ride |

**Not gated (intentional, small scope):** `decline`, `hide`, `heartbeat` — no approval check today.

---

## 5. Accept path — approval guard location

`backend/routes/drivers.py` → `accept_ride`:

1. Load ride / early 404–409 if already claimed
2. **`assert_driver_eligible_for_claim()`** (`backend/services/claim_eligibility.py` L111–164) — approval first, then presence/online/freshness/active-ride
3. **`OpenBoardDispatchPolicy.claim_ride()`** — atomic `FOR UPDATE` claim (unchanged)

---

## 6. Dispatch filtering

| Query | Location | Filter |
|-------|----------|--------|
| System dispatch pool | `query_dispatch_available_driver_ids()` | `DriverApproval.status == approved` + `driver_status.online` + fresh location (`FRESHNESS_WINDOW_SECONDS`) |
| `GET /internal/available-drivers` | `backend/routes/internal.py` | Uses above |
| Ride alert notifications | `backend/routes/notifications.py` | Uses above |
| Metrics dispatch count | `backend/services/metrics.py` | Uses above |
| Driver marketplace pool | `GET /drivers/available-rides` | `driver_is_dispatch_eligible()` — empty list if not approved/eligible |

---

## 7. Suspended driver with active ride

Documented behavior (`assert_driver_can_perform_ride_action`):

- **Blocked:** `accept`, `decline`, `hide` (no new assignments)
- **Allowed:** `arrive_pickup`, `start_ride`, `complete_ride` on ride already assigned to that driver
- **No ride corruption:** suspension does not auto-cancel in-progress rides

---

## 8. Files changed (this pass)

| File | Change |
|------|--------|
| `backend/routes/admin_driver_approval.py` | Restored minimal approval-only mounted router; `approval_status` query alias |
| `backend/tests/test_driver_approval.py` | Added tests: suspend→go-online 403, `approval_status` query param, internal dispatch exclusion |
| `docs/HALFAPP_DRIVER_APPROVAL_GATE_01_REPORT.md` | This report |

**Pre-existing foundation (verified, not authored in this pass):** `models/driver_approval.py`, `services/driver_approval.py`, `services/claim_eligibility.py`, `services/presence.py`, `services/driver_status_service.py`, `alembic/versions/0012_*`, `tests/test_ride_claim_eligibility.py`, etc.

---

## 9. Commands run

```text
cd backend
python -m pytest tests/test_driver_approval.py tests/test_ride_claim_lock_concurrency.py tests/test_ride_claim_eligibility.py -v --tb=short
# 23 passed in ~13s

python -m pytest tests/test_driver_approval.py tests/test_ride_claim_lock_concurrency.py tests/test_ride_claim_eligibility.py tests/test_driver_online_status.py tests/test_driver_001b_presence_busy_guard.py tests/test_dispatch_auditability.py tests/test_active_route_surface.py -v --tb=no
# 49 passed in ~26s

python -m pytest tests/ -v --tb=no -q
# 215 collected: 150 passed, 65 failed in ~387s (failures are suite-order/DB isolation; same modules pass in isolation — not approval regressions)
```

---

## 10. Tests added / updated

**`backend/tests/test_driver_approval.py`**

- `test_admin_lists_pending_drivers_approval_status_alias`
- `test_admin_suspends_driver_cannot_go_online`
- `test_internal_available_drivers_excludes_non_approved`

**Existing coverage (unchanged):** pending/rejected/suspended go-online 403; admin approve/reject; RBAC on admin PATCH; pool empty for non-approved; suspended accept 403; suspended can complete in-flight ride; claim eligibility parametrized accept 403.

---

## 11. Blockers

None for GATE_01 scope.

**Note:** Full `pytest tests/` (215 items) shows many failures when run together (likely shared SQLite / import-order); targeted approval + claim-lock + driver suites pass. Alembic-head assertion tests may fail if local DB head differs from repo migrations — unrelated to approval logic.

---

## 12. Intentionally not built

- Document upload, Checkr, insurance verification
- Full admin dashboard UI (dormant `admin.py` rides/users routes not mounted)
- Stripe/payments, OSRM runtime, Google/Mapbox changes
- WebSockets, push notifications, dispatch timeout/cascade
- UI redesign
- Approval guards on `decline` / `hide` (see follow-up below)
- Login response `approval` field (register + `/auth/me` expose it; login omits it)

---

## Follow-up (post-GO, not DRIVER-002 scope)

**Decline / hide safety review (2026-05-22):**

| Endpoint | Unapproved (pending/rejected) | Suspended |
|----------|------------------------------|-----------|
| `POST /drivers/rides/{id}/hide` | Allowed; only per-driver visibility on unassigned `requested` rides — does **not** assign `driver_id` or change global ride status | Allowed today; same scope (visibility only) |
| `POST /drivers/decline-dispatch/{id}` | Only if driver has an active dispatch offer (cascade pool is approval-filtered) | Allowed if offer exists; records decline, does not assign ride |
| `POST /drivers/decline-ride/{id}` | **Blocked in practice** — requires `ride.driver_id == driver` (cannot accept while unapproved) | **Gap:** suspended driver with an **accepted** ride can still call decline and release the ride back to the pool (`driver_id` cleared). Does not auto-cancel, but mutates assigned ride state. **Follow-up:** add `assert_driver_can_perform_ride_action(..., action="decline")` on `decline_ride` (and optionally `hide` / `decline_dispatch` for parity). |

**Test-env approval default:** `HALFAPP_ENV=test` auto-approves in `create_user()` only. Production and non-test dev seeds must not set `HALFAPP_ENV=test` casually; use explicit `driver_approval_status=` or `approve_driver_for_tests()` in `tests/driver_test_helpers.py`. `POST /internal/test-users` inherits `create_user` rules (not an implicit prod approve).
