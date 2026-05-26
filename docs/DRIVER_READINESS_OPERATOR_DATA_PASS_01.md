# Driver Readiness Operator Data Pass 01

**Date:** 2026-05-25  
**Status:** **GO** for closed-beta driver readiness shaping. **Public launch remains NO_GO.**

---

## Goal

Move DriverReadinessV1 from mostly app-side checklist logic into a real operator-owned data path:

- driver submits profile, vehicle, license, and insurance policy
- ops records insurance expiry and vehicle readiness
- driver app blocks going online until profile, vehicle, docs, insurance, expiry, backend, and manual approval are satisfied
- completion and earnings copy remains recorded-obligation only, not payout execution

---

## What Changed

| Area | Change |
|------|--------|
| Backend schema | Added Alembic head `0036_driver_readiness_fields`: `users.insurance_expires_at`, `users.vehicle_ready` |
| Driver profile API | `GET/PUT /drivers/profile` now exposes `vehicle_year`, `vehicle_ready`, and `insurance_expires_at` |
| Ops API | Added `PATCH /admin/drivers/{driver_id}/readiness` for operator readiness review |
| Ops app | Drivers table shows readiness status and lets ops mark a closed-beta driver vehicle/insurance as reviewed |
| Driver app | Readiness gate now blocks missing ops vehicle review and missing insurance expiry, not only missing self-entered fields |
| Offline mock proof | Dev-only mock drivers now carry explicit closed-beta readiness data; mock ride writes use labeled local data without waiting on a dead backend |
| Owner runbook | Owner verification script and manual runbook now seed/verify readiness before going online |
| Tests | Added/updated backend, driver-app, and Playwright tests for operator readiness fields, online-gate blockers, and the full closed-beta driver loop |

---

## New Driver Flow

Offline → readiness check → ops-reviewed vehicle/insurance → online → ride offer → accept → trip → completion receipt

The driver sees why they cannot go online, for example:

- profile incomplete
- vehicle information missing
- vehicle pending operations review
- license/docs missing
- insurance missing
- insurance expiry missing
- insurance expired
- beta approval/manual operations required
- backend unavailable

---

## Honest Limits

- Vehicle readiness and insurance expiry are operator-reviewed fields, not external document verification.
- No proof-of-delivery exists yet.
- No wallet, instant payout, deposited, or bank-transfer product claim exists.
- Completion receipt means fare obligation recorded; payout execution is not performed in the trusted-driver beta lane.
- G3 owner courier day remains human-only and pending until `OWNER_COURIER_DAY_REPORT_01.md` is filled.

---

## Commands Run

```powershell
cd driver-app
npm test
# Result: 159 passed, 0 failed; assert-no-ai-providers OK; assert-no-money-claims OK

npm run build
# Result: PASS

npx playwright test tests/smoke-mvp.spec.ts
# Result: 1 passed

cd ../ops-app
npm run build
# Result: PASS

cd ../backend
py -3.11 -m pytest -q tests/test_driver_profile_read.py tests/test_driver_settings_profile_slice02.py tests/test_ops_phase4.py tests/test_active_route_surface.py
# Result: 15 passed, 12 warnings

py -3.11 -m alembic upgrade head
py -3.11 -m alembic current
# Result: 0036_driver_readiness_fields (head) on SQLite dev DB

# Fresh PostgreSQL 16 temporary cluster, port 55434
$env:DATABASE_URL='postgresql+psycopg2://halfapp@127.0.0.1:55434/halfapp_test'
py -3.11 -m alembic upgrade head
py -3.11 -m alembic current
# Result: 0036_driver_readiness_fields (head)

py -3.11 -m pytest -q tests/test_alembic_postgres_upgrade_head.py tests/test_postgres_claim_race_proof_01.py
# Result: 2 passed, 4 warnings

cd ..
py -3.11 -m py_compile scripts\owner_runbook_verify.py
# Result: PASS
```

---

## Remaining Blockers

| Blocker | Next Action |
|---------|-------------|
| Owner courier day | Owner runs `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md` and fills `docs/OWNER_COURIER_DAY_REPORT_01.md` |
| Legal/insurance verification | Replace ops-entered expiry with real document intake and policy review |
| Proof of delivery | Pick POD as the next product fork only after owner day |
| Public launch | Still blocked by legal, hosting, mobile-store, support, insurance, and payout proof |
