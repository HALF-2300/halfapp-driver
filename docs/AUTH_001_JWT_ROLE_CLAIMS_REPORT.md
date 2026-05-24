# AUTH-001 — JWT Role Claims Middleware

**Date:** 2026-05-22  
**Verdict:** **GO** (accepted 2026-05-22)

| Status item | Result |
|-------------|--------|
| AUTH-001 | **GO** |
| JWT role contract | **GO** |
| Active route lane protection | **GO** |

---

## Follow-up (pre–closed beta)

1. Keep intentionally public routes documented exactly as in [Routes intentionally public](#routes-intentionally-public) below.
2. Revisit dev/test endpoints (`POST /internal/test-users`, `POST /internal/test-login`) and confirm they remain gated by `ALLOW_TEST_USER_SEED` (and equivalent env flags) before closed beta.
3. `dossier_marketplace/*` stays **excluded** from primary launch readiness unless explicitly hardened later.
4. Unmounted routers (`admin`, `test`, legacy `rides`, `notifications`) are **not** launch-ready surfaces — do not count them toward demo or beta readiness.

Do not expand auth in this lane beyond maintenance of the above contract.

---

## Summary

HalfApp now has a single JWT + lane-guard contract for active FastAPI routes. Tokens carry `user_id`, JWT role (`rider` | `driver` | `admin`), `email`, `iat`, and `exp`. Protected routes return structured `401` errors (`unauthenticated`, `token_expired`, `invalid_token`) and lane mismatches return `403` with `error: forbidden`.

The authenticated caller is represented as `AuthPrincipal` (alias `AuthenticatedUser`) via FastAPI `Depends`, which is the project’s `request.user` equivalent.

---

## Files changed

| File | Change |
|------|--------|
| `backend/services/auth_errors.py` | **New** — structured auth error codes |
| `backend/services/auth.py` | JWT claims, rider/driver role mapping, `decode_token_result` |
| `backend/services/rbac.py` | Structured 401/403, `require_role()`, enriched `AuthPrincipal` |
| `backend/routes/auth.py` | Tokens issued via `create_access_token(user=user)` |
| `backend/routes/drivers.py` | `require_role("driver")`, public directory docstring |
| `backend/routes/rider_rides.py` | `require_role("rider")` |
| `backend/routes/internal.py` | `require_role("admin")`, test token issuance |
| `backend/routes/traffic_signals.py` | `require_role("driver")` |
| `backend/routes/admin.py` | `require_role("admin")` (dormant router; kept consistent) |
| `backend/routes/notifications.py` | `require_role("admin")` for admin lane |
| `backend/tests/test_auth_jwt_middleware.py` | **New** — AUTH-001 required cases |
| `backend/tests/test_rbac.py` | Structured 401 assertions, `create_access_token(user=…)` |
| `backend/tests/test_rbac_boundary.py` | Structured 403 assertions |

---

## Auth middleware

- **Token issue:** `backend/services/auth.py` — `create_access_token(user=…)` embeds `user_id`, `role` (`rider` not DB `customer`), `email`, `iat`, `exp`.
- **Token parse:** `decode_token_result()` distinguishes `token_expired` vs `invalid_token`.
- **Request user:** `resolve_principal()` in `backend/services/rbac.py` → `AuthPrincipal` / `AuthenticatedUser`.

---

## Role guard

- `require_role("rider" | "driver" | "admin")` — lane + role enforcement.
- `require_roles(...)` — retained for multi-role endpoints (e.g. `/auth/me`, notifications).
- Rules: rider↔driver cross-lane → 403; non-admin on admin lane → 403; admin on `/internal/system-health` → 200.

---

## Routes protected

| Router | Guard |
|--------|--------|
| `drivers` (except `GET /drivers/`) | `require_role("driver")` |
| `rider_rides` | `require_role("rider")` |
| `internal` (`GET /system-health`) | `require_role("admin")` |
| `traffic_signals` | `require_role("driver")` |
| `auth` (`GET /me`) | authenticated (any role) |

Driver ride lifecycle, earnings, route snapshots, dispatch, and transparency endpoints inherit `DRIVER_ACCESS` from `drivers.py`.

---

## Routes intentionally public

| Route | Why |
|-------|-----|
| `GET /health` | Liveness probe |
| `POST /auth/register`, `POST /auth/login` | Credential exchange |
| `GET /drivers/` | Open-board driver directory (documented in route docstring) |
| `POST /internal/test-users`, `POST /internal/test-login` | Playwright/API seeding; gated by `ALLOW_TEST_USER_SEED` |
| `dossier_marketplace/*` | Experimental spine; not primary app path; left open to avoid breaking foundation proofs |

**Not mounted (unchanged):** `routes/admin.py`, `routes/test.py`, legacy `routes/rides.py`, `routes/notifications.py` (per `main.py`).

---

## Test commands and output

```text
cd backend
python -m pytest tests/test_auth_jwt_middleware.py tests/test_rbac.py tests/test_rbac_boundary.py -q
# 16 passed

python -m pytest tests/test_route_snapshots_foundation.py tests/test_pricing_ledger_v01.py tests/test_ride_lifecycle.py tests/test_rider_cancel.py -q
# 32 passed (ride/pricing/snapshot slice)

python -m pytest tests/ -q
# 155 passed in ~55s
```

---

## Existing tests updated

- `test_rbac.py` — structured `401` detail; `create_access_token(user=user)`
- `test_rbac_boundary.py` — structured `403` detail

All other tests continue to pass with JWT `role: rider` for customer users (backward-compatible decode accepts `customer` claim).

---

## Blockers

None for AUTH-001 scope.

---

## Intentionally not built

- Full RBAC permission matrix
- OAuth / social login / magic links
- Stripe / payments
- Driver documents
- Admin dashboard redesign
- Dispatch / ride lifecycle changes
- UI redesign
- Token refresh / revocation (see `docs/HALFAPP_TOKEN_POLICY_SKETCH_01.md`)
