# HalfApp Execution Backlog

**Date:** 2026-05-22 (reconciled)  
**Order:** `HALFAPP_TRUTH_SYNC_BACKLOG_RECONCILIATION_01`  
**Status:** aligned with implemented v0.1 spine — **do not reopen closed P0 lanes without explicit rescope**

Authoritative planning snapshot: `docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md`  
Operational truth: `docs/CURRENT_TRUTH.md`

This backlog preserves the active product spine: `backend`, `driver-app`, and `docs/RIDE_LIFECYCLE_CONTRACT.md`. Tickets below are **classified against code and proof** as of full backend pytest green (`383 passed, 9 skipped` on 2026-05-25; see `docs/BACKEND_PYTEST_DRIFT_CLOSURE_01.md`).

---

## Do not reopen without rescope (closed lanes)

| Lane | Verdict | Proof |
|------|---------|-------|
| AUTH-001 | **GO** | `tests/test_auth_jwt_middleware.py`, `tests/test_rbac.py`; `docs/AUTH_001_JWT_ROLE_CLAIMS_REPORT.md` |
| RIDE-001 | **GO** | `tests/test_ride_001_transition_guards.py`; `docs/RIDE_001_STATE_MACHINE_GUARDS_REPORT.md` |
| RIDE-002 | **GO** | `tests/test_ride_claim_lock_concurrency.py`; `docs/RIDE_002_ATOMIC_CLAIM_LOCK_REPORT.md` |
| RIDE-003 | **GO** | `tests/test_ride_003_dispatch_cascade.py`; `docs/RIDE_003_DISPATCH_CASCADE_REPORT.md` |
| DRIVER-001B | **GO** | `tests/test_driver_001b_presence_busy_guard.py` |
| DRIVER-002 | **GO** | `tests/test_driver_approval.py`; `docs/DRIVER_002_DRIVER_APPROVAL_WORKFLOW_REPORT.md` |
| TEST-ISOLATION-01 | **GO** | `tests/conftest.py` per-test wipe; `docs/HALFAPP_TEST_ISOLATION_AND_P0_GATE_STABILIZATION_01_REPORT.md` |
| HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01 | **GO** | `tests/test_production_guards.py`; `backend/production_guards.py`; `docs/HALFAPP_PRODUCTION_GUARDS_SECRET_SIMULATION_CORS_01.md` |
| HALFAPP_ENGINEERING_INTELLIGENCE_SAFE_SHELL_01 | **GO** | `tests/test_engineering_intelligence_status.py`; `driver-app` `#/engineering-intelligence` — **LOCAL_CONTEXT_ONLY** |

Agents must **not** rebuild these lanes unless a new order explicitly rescopes them.

---

## Ticket classification (Epics 1–6)

| Ticket | Classification | Proof / boundary |
|--------|----------------|------------------|
| **1.1** Quarantine legacy UI | **DONE_PROVEN** | `frontend/README.md` inactive; active UI `driver-app/` only |
| **1.2** Production build guardrails | **DONE_PROVEN** | `driver-app/scripts/assert-prod-truth.mjs` + `prebuild`; `npm run build` rejects mock/guard bypass in prod |
| **1.3** Lock contract drift | **DONE_PROVEN** | `backend/scripts/print_openapi_driver_rides.py` + lifecycle tests + `tests/test_openapi_surface_does_not_drift.py` snapshot gate |
| **2.1** Alembic wiring | **DONE_PROVEN** | `backend/alembic/`; startup `run_migrations` in `main.py`; `tests/test_v01_foundation.py` |
| **2.2** Initial schema migration | **DONE_PROVEN** | `0001`–`0015` revisions; fresh DB via `alembic upgrade head` |
| **2.3** Remove runtime schema patches | **PARTIAL** | Alembic is primary; `ensure_ride_lifecycle_columns()` still in `database.py` (legacy SQLite safety) |
| **3.1** Ride visibility records | **DONE_PROVEN** | `models/metrics.py` `RideVisibility`; `tests/test_dispatch_auditability.py` |
| **3.2** Claim attempt audit rows | **DONE_PROVEN** | `RideClaimAttempt`; race/conflict tests in `test_ride_claim_lock_concurrency.py`, `test_ride_transparency_and_claim_conflict.py` |
| **3.3** Return dispatch metadata | **DONE_PROVEN** | `GET /drivers/available-rides` policy version + rank; `test_dispatch_auditability.py` |
| **3.4** Backend-backed hide/dismiss | **DONE_PROVEN** | `POST /drivers/rides/{ride_id}/hide`; `test_dispatch_auditability.py` |
| **4.1** Marketplace ledger model | **DONE_PROVEN** | `marketplace_ledger_events` migration `0005`; `tests/test_marketplace_ledger_events.py` |
| **4.2** Emit lifecycle/dispatch events | **DONE_PROVEN** | Emitters in `services/ledger.py`, drivers/rider routes; `test_marketplace_ledger_events.py`, lifecycle tests |
| **5.1** Route snapshot schema | **DONE_FOUNDATION_ONLY** | `route_snapshots` table `0010`; `tests/test_route_snapshots_foundation.py` — **not** full UI read surface |
| **5.2** UI spatial claims contract-bound | **PARTIAL** | `rideModel.js`, `MapHome.jsx` use backend fields; ride-flow E2E **GO**; no dedicated snapshot-read UI |
| **6.1** Fare ledger entries (`fare_ledger_entries`) | **STALE_OR_SUPERSEDED** | v0.1 uses **`ride_pricing`** + `tests/test_pricing_ledger_v01.py` — do not add parallel fare_ledger table without rescope |
| **6.2** Payout batch records | **NOT_STARTED** | **Forbidden:** no PSP/payout execution — `settlement_entries` obligation rows only (`tests/test_ride_settlement_ledger.py`) |

---

## Next executable work queue

### P0 (product completion + internal owner-car testing — not external beta)

See **`docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`** for ordered slices. **External trusted-driver beta is deferred.**

| Item | Why | Proof target |
|------|-----|--------------|
| **Internal owner test mode + runbook** | Owner-car validation without beta ops | `INTERNAL_OWNER_TEST_MODE_01` in product completion roadmap |
| **OSRM runtime proof** (Docker/VPS) | Code path GO; runtime **NO_GO** | `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md`, `docs/RUNTIME_PROOF_PROCEDURE.md` |
| **Postgres claim-race CI** | Manual proof exists; need repeatable CI + PG migrations | `docs/HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01_REPORT.md`; CI matrix on PostgreSQL |
| **Dossier Path A vs B decision** | Dual spine risk (document only) | `docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md` — keep **PARALLEL_NOT_WIRED** for driver app |

### P1 (hardening + remaining driver surfaces)

| Item | Notes |
|------|-------|
| ~~Profile / settings shell~~ | **DONE** — `docs/PROFILE_SETTINGS_SHELL_01.md`; vehicle/contact/session/preferences all via API; AppShellLayout; no mock data |
| ~~Notifications product UI~~ | **DONE** — `docs/NOTIFICATIONS_PRODUCT_UI_01.md`; backend-only, DEV-gated demo tab, AppShellLayout; stale heading E2E fixed |
| ~~Cockpit session resilience~~ | **DONE (code) / TODO (E2E)** — `docs/COCKPIT_SESSION_RESILIENCE_01.md`; backend + frontend shipped; live-stack E2E run is owner-runnable |
| ~~Driver closed-beta readiness shaping~~ | **DONE** — `docs/DRIVER_APP_REAL_APP_SHAPING_PASS_01.md`; DriverReadinessV1, go-online gate, ride offer expired/conflict states, honest completion receipt; `npm test` 158 passed; `npm run build` passed |
| ~~Settlement / calculation copy lock~~ | **DONE** — `docs/TRIPS_EARNINGS_POLISH_01.md`; delivery vocabulary aligned across trips/earnings/chart; 150 npm tests pass |
| ~~Token revocation / refresh design~~ | **DONE** — `docs/TOKEN_SESSION_SAFETY_01.md`; migration 0016, rotation, logout-all; `test_auth_refresh_rotation.py` |
| ~~CORS hardening + observability~~ | **DONE** — `docs/DEPLOY_CORS_OBSERVABILITY_01.md`; CORS hardened; structured request logging middleware with `driver_id`/`ride_id` correlation |
| ~~Contract drift CI (Ticket 1.3)~~ | **DONE** — `docs/OPENAPI_TRUTH_SYNC_01.md`; `test_openapi_surface_does_not_drift.py` in `truth-and-drift` CI job |

### P2 (deferred product)

| Item | Notes |
|------|-------|
| PSP design **or** hard no-payout lock | Payments remain **NO_GO** |
| Rider app | Only after honesty gates; API-only today |
| Full admin console | Only after RBAC + route-surface proof on live API |
| Remove `ensure_ride_lifecycle_columns` | After migration-only path verified for all dev DBs |

---

## Epic reference (historical — do not treat as greenfield)

The sections below preserve the original epic intent for traceability. **Implementation status is in the classification table above.**

### Epic 1: Stabilize The Active Spine

Goal: make truth discipline hard to violate.

#### Ticket 1.1: Quarantine Legacy UI — **DONE_PROVEN**

- Evidence: `frontend/README.md`, `docs/DORMANT_ROUTERS_INVENTORY.md`.

#### Ticket 1.2: Add Production Build Guardrails — **DONE_PROVEN**

- Evidence: `driver-app/scripts/assert-prod-truth.mjs`, `driver-app/package.json` `prebuild`.

#### Ticket 1.3: Lock Contract Drift — **DONE_PROVEN**

- `backend/tests/test_openapi_surface_does_not_drift.py` — snapshot at `tests/snapshots/openapi_paths.json`; runs in CI `truth-and-drift` job; fails on path set change.
- Dossier paths (`/supply`, `/demand`, `/trip`) explicitly excluded from snapshot when `HALFAPP_DOSSIER_SPINE_ENABLED` unset.
- Note: snapshot compares path set, not full RIDE_LIFECYCLE_CONTRACT schema — deep schema alignment is a P1-hardening item.

### Epic 2: Introduce Migration Discipline

Goal: versioned schema changes.

#### Tickets 2.1–2.2 — **DONE_PROVEN**

#### Ticket 2.3: Remove Runtime Schema Patches — **PARTIAL**

- `ensure_ride_lifecycle_columns()` remains; track under P2 cleanup.

### Epic 3: Dispatch Transparency Foundation

#### Tickets 3.1–3.4 — **DONE_PROVEN**

- Open-board default: `HALFAPP_OPEN_BOARD_DISPATCH=1`.
- Sequential cascade: RIDE-003 **GO** when flag `0` — do not rewrite.

### Epic 4: Append-Only Marketplace Event Ledger

#### Tickets 4.1–4.2 — **DONE_PROVEN**

- Not the dossier double-entry `ledger_*` spine (see dossier reconciliation doc).

### Epic 5: Route Snapshot Model

#### Ticket 5.1 — **DONE_FOUNDATION_ONLY**

#### Ticket 5.2 — **PARTIAL**

### Epic 6: Finance Ledger

#### Ticket 6.1 — **STALE_OR_SUPERSEDED** (use `ride_pricing`)

#### Ticket 6.2 — **NOT_STARTED** (payout batches — blocked by no-PSP boundary)

---

## Forbidden claims (unchanged)

Do not instruct agents or copy to claim:

- Payment processing, wallet, capture, or payout execution
- Production OSRM until runtime proof **GO**
- Nearest-driver geo auto-dispatch on the **driver-app** path
- Rider app UI, full admin console, or city-scale mobility OS
- Ride-product AI/LLM inference on dispatch/pricing/lifecycle

---

## Verification

```powershell
cd backend
py -3.11 -m pytest tests -q

cd ..\driver-app
npm test
npm run build

cd ..
py -3.11 scripts\verify_current_truth_backlog.py
```
