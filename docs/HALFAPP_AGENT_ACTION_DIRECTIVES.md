# HalfApp Agent Action Directives

Date: 2026-05-22 (status sync: `HALFAPP_TRUTH_SYNC_BACKLOG_RECONCILIATION_01`)  
Prior: 2026-05-18

Purpose: convert the HalfApp critical overview into an execution brief for the next coding agent. This is not a research document. It is an action plan for completing the program in the correct order.

Authoritative snapshot: `docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md`.  
Operational truth: `docs/CURRENT_TRUTH.md` · reconciled backlog: `docs/BACKLOG.md`.

## Action status tracker (v0.1)

| Action | Topic | Status | Notes |
|--------|-------|--------|-------|
| AUTH-001 | JWT role claims middleware | **GO** (accepted 2026-05-22) | JWT contract + lane guards on active routes; see `docs/AUTH_001_JWT_ROLE_CLAIMS_REPORT.md`. Pre–beta: re-check public/dev routes and env gates. Do not expand auth in this lane. |
| RIDE-002 | Atomic claim lock | **GO** (accepted 2026-05-22) | `POST /drivers/accept-ride/{ride_id}`; `dispatch.py` lock + conditional UPDATE; `claim_eligibility.py` accept-time guards; 10-driver concurrency proof. See `docs/RIDE_002_ATOMIC_CLAIM_LOCK_REPORT.md`. **Do not modify claim-lock code in this lane.** |
| RIDE-001 | State machine guards | **GO** (accepted 2026-05-22) | Formal audit + structured `invalid_state_transition` 409s; see `docs/RIDE_001_STATE_MACHINE_GUARDS_REPORT.md`. Do not expand lifecycle in this lane. |
| RIDE-003 | Request timeout + dispatch cascade | **GO** (accepted 2026-05-22) | `ride_dispatch_log` (sent/accepted/declined/timeout/skipped_ineligible); `dispatch_driver_id`, `dispatch_expires_at`, `dispatch_attempt_count`; 30s / 3 attempts; decline cascade; exhaustion `cancelled` + `lifecycle_reason=no_drivers_available`. See `docs/RIDE_003_DISPATCH_CASCADE_REPORT.md`. **Do not modify RIDE-003 unless explicitly rescoped.** Open-board: `HALFAPP_OPEN_BOARD_DISPATCH=1`. In-process timeout refresh accepted for v0.1. |
| DRIVER-001B | Presence / busy scope | **GO** | Backend-owned presence; busy/active-ride guards in `claim_eligibility.py`. |
| DRIVER-002 | Formal driver approval workflow | **GO** (2026-05-22) | `driver_approvals` + `/admin/drivers` approval API; gates online/accept/dispatch. See `docs/DRIVER_002_DRIVER_APPROVAL_WORKFLOW_REPORT.md`. Do not expand approval in this lane. |
| 1 | Lock active product boundary | **Largely done** — doc sync ongoing | `backend` + `driver-app` only; dossier not wired to UI |
| 2 | Backend-owned driver presence | **Done** | `/drivers/presence`, heartbeat, stale/disconnected |
| 3 | Backend ride hide/dismiss | **Done** | `POST /drivers/rides/{ride_id}/hide` |
| 4 | Dispatch auditability | **Done** | Visibility, claims, 409, transparency endpoint |
| 5 | Marketplace ledger events | **Done** | `marketplace_ledger_events` append-only |
| 6 | Migration discipline | **Done** | Alembic `0001`–`0009`, startup `run_migrations` |
| 7 | Financial ledger foundation | **Done (settlement boundary)** | `ride_pricing` lock + `settlement_entries`; no PSP/payout execution |
| 8 | Route snapshot foundation | **Done (foundation)** | `route_snapshots` table; quote/complete rows; read API; OSRM runtime still **NO_GO** |
| 9 | Production hardening | **Partial** | **SECRET_KEY guard GO** (`HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01`); CORS/simulation guards shipped; revocation/structured logging remain |

## P0 chain status (2026-05-22)

| Task | Status |
|------|--------|
| AUTH-001 | **GO** |
| RIDE-001 | **GO** |
| RIDE-002 | **GO** |
| RIDE-003 | **GO** |
| DRIVER-001B | **GO** (presence/busy scope) |
| DRIVER-002 | **GO** |

**HALFAPP_DRIVER_COCKPIT_RIDE_FLOW_E2E_LOCK_01: GO** — `docs/HALFAPP_DRIVER_COCKPIT_RIDE_FLOW_E2E_LOCK_01_REPORT.md`; `npm run test:e2e:ride-flow` **1 passed**.

**Next execution task (P0):** per `docs/BACKLOG.md` / `docs/CURRENT_TRUTH.md` (OSRM runtime proof, production hardening, etc.).

**Historical note:** RIDE-003 acceptance text that listed DRIVER-002 as “next / NOT BUILT” is **obsolete**; current truth has **DRIVER-002 GO**.

**HALFAPP_TEST_ISOLATION_AND_P0_GATE_STABILIZATION_01: GO** — `docs/HALFAPP_TEST_ISOLATION_AND_P0_GATE_STABILIZATION_01_REPORT.md` (full backend **254 passed**, one command).

**HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01: GO** — `docs/HALFAPP_PRODUCTION_GUARDS_SECRET_SIMULATION_CORS_01.md`; `tests/test_production_guards.py`.

**DRIVER-002 sub-status (accepted):** driver approval gate GO · admin approval API GO · go-online guard GO · accept-ride guard GO · dispatch approval filtering GO. Production default `pending`; tests pass explicit `driver_approval_status=approved` where needed.

**Closed lanes (do not reopen without explicit rescope):** AUTH-001, RIDE-001, RIDE-002, RIDE-003, DRIVER-001B, DRIVER-002, TEST-ISOLATION-01, HALFAPP_DRIVER_COCKPIT_RIDE_FLOW_E2E_LOCK_01, HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01, HALFAPP_ENGINEERING_INTELLIGENCE_SAFE_SHELL_01. Keep sequential cascade separate from open-board mode (`HALFAPP_OPEN_BOARD_DISPATCH=1`). No Redis/job queue/WebSockets/push/payments/OSRM/UI redesign in those lanes.

**DRIVER-002 follow-up:** `decline-ride` + suspended assigned ride — **closed** in test-isolation pass (403 `driver_suspended`; ride not released). `hide` / `decline-dispatch` remain unguarded (low risk).

**Deferred (infra):** `HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01` (when Docker/VPS available).

## Mission

Complete HalfApp by making the active `backend` and `driver-app` truthful, auditable, and production-ready before expanding the product surface.

Do not make the app look bigger before the backend can prove what the UI displays.

The core rule:

> Every important driver-facing fact must come from durable backend truth, not frontend inference.

## Current Product Boundary

Treat only these as active product surfaces:

- `backend`
- `driver-app`
- `docs/RIDE_LIFECYCLE_CONTRACT.md`
- `docs/HALFAPP_TRANSPARENCY_ARCHITECTURE.md`
- `docs/HALFAPP_EXPERT_PROGRAM_CRITICAL_OVERVIEW.md`

Treat these as inactive unless explicitly revived, registered, and tested:

- Legacy `frontend`
- Dormant backend routers not mounted by `backend/main.py`
- Dormant driver-app diagnostic/demo components
- LocalStorage mock systems
- Demo-only messaging

## Non-Negotiable Direction

Do not prioritize:

- Larger UI surface area
- Full rider app
- Admin dashboard
- Payment UI
- Nearest-driver marketing claims
- Fancy maps
- Legacy frontend revival

Prioritize:

- Backend-owned state
- Active driver app alignment
- Audit records
- Database migrations
- Deterministic dispatch behavior
- Financial correctness
- Route proof
- Production hardening

## Execution Order

### Action 1: Lock The Active Product Boundary

**Status: largely done** (governance docs reconciled with v0.1 in `HALFAPP_TRUTH_SYNC_V0_1_DOC_RECONCILIATION_01`).

Goal: prevent future work from accidentally using demo or legacy code.

Tasks:

- Confirm `backend` and `driver-app` are the only active product path.
- Mark legacy `frontend` as inactive or archive-only in documentation.
- Confirm unmounted backend routers are not described as active API.
- Identify dormant driver-app components and label them as inactive if they remain.
- Ensure mock mode and guard bypass cannot be silently enabled in production builds.

Done when:

- A new developer can identify the active app path quickly.
- No active doc presents unmounted routes as shipped behavior.
- No production-facing screen depends on browser localStorage as marketplace truth.

### Action 2: Make Driver Presence Backend-Owned

**Status: done.**

Goal: replace local online/offline truth with backend presence truth.

Tasks:

- Add `GET /drivers/presence`.
- Add `PUT /drivers/presence`.
- Add `POST /drivers/heartbeat`.
- Persist driver presence state on the backend.
- Add stale/disconnected state handling.
- Update the cockpit so online/offline state reads from and writes to the backend.
- Keep local UI state only as a cache of the backend response.

Done when:

- Browser refresh does not change driver marketplace truth.
- Backend can explain when a driver was `available`, `offline`, `paused`, `stale`, or `disconnected`.
- Dispatch does not depend on stale local browser state.

### Action 3: Replace Local Ride Hide With Backend Dismissal

**Status: done.**

Goal: make `Hide for now` a real marketplace fact or clearly label it as local-only.

Tasks:

- Add `POST /drivers/rides/{ride_id}/hide`.
- Add a ride visibility/dismissal record.
- Exclude active hidden rides from that driver's available ride list.
- Store dismissal reason, timestamp, driver ID, ride ID, and expiry/TTL.
- Update cockpit `Hide for now` to call the backend endpoint.

Done when:

- A hidden ride does not reappear to the same driver until the backend contract allows it.
- The backend can explain when and why the driver hid a ride.
- The UI does not imply a backend decline if only local filtering occurred.

### Action 4: Add Dispatch Auditability

**Status: done.**

Goal: make open-board dispatch explainable.

Tasks:

- Add dispatch policy metadata to available ride responses.
- Return deterministic ordering metadata.
- Record which rides became visible to which drivers.
- Record claim attempted, claim won, and claim lost events.
- Preserve atomic first-claim-wins behavior.
- Return clear `409 Conflict` responses when another driver wins.

Done when:

- Backend can explain why a ride appeared to a driver.
- Backend can explain why a claim failed.
- Backend records which dispatch policy made the decision.
- Concurrent claims cannot double-book a ride.

### Action 5: Add Marketplace Ledger Events

Status: implemented for the active backend ride/dispatch spine.

Goal: create an append-only audit trail for important marketplace facts.

Tasks:

- Add `marketplace_ledger_events`.
- Write events for:
  - ride created,
  - ride visible,
  - ride hidden,
  - claim attempted,
  - claim won,
  - claim lost,
  - ride declined/released,
  - ride cancelled,
  - ride completed,
  - earnings calculated.
- Include correlation IDs where practical.
- Include idempotency keys for critical writes where practical.
- Add tests proving event creation.

Done when:

- Important marketplace state changes are not represented only as mutable fields on `rides`.
- Future driver/admin audit views can be built from backend events.

Current implementation:

- `marketplace_ledger_events` is append-only at the database layer.
- Event rows include `idempotency_key`, `correlation_id`, `previous_event_hash`, and `event_hash`.
- Active ride creation, visibility, hide, claim, release, cancellation, completion, presence, and earning-calculation paths write events.

### Action 6: Add Database Migration Discipline

**Status: done** (Alembic through `0009_traffic_signal_aware`; CI drift check).

Goal: stop relying on startup schema mutation as the long-term schema strategy.

Tasks:

- Add migration tooling, preferably Alembic for the current FastAPI/SQLAlchemy stack.
- Create initial migrations for current schema.
- Move future schema changes into migrations.
- Add foreign keys and indexes where safe and appropriate.
- Document local development migration commands.

Done when:

- Schema changes are repeatable and reviewable.
- Production schema evolution does not depend on `create_all`.
- Tests can run against a predictable migrated schema.

### Action 7: Add Financial Ledger Foundation

**Status: partial** — v0.1 `ride_pricing` + `pricing_policy` on active path; settlement/payout/refund ledger not shipped.

Goal: separate money truth from earnings summaries.

Tasks:

- Store money as integer cents, not floating-point values. **Done** on `ride_pricing`.
- Add financial records for quote, final fare, platform fee, driver earning, adjustment, refund, and payout. **Partial** — quote/complete breakdown yes; payout/refund events no.
- Track rate-card ID and calculation basis. **Done** via `pricing_policy_id` / `pricing_version`.
- Keep `GET /drivers/earnings` as a projection over ledger records. **Partial** — still summary-oriented; not full settlement projection.
- Add tests for rounding, adjustment, refund, and payout projection behavior. **Partial** — `test_pricing_ledger_v01.py`, ride-flow proof; no payout batch tests.

Done when:

- Driver earnings are explainable down to the cent. **Met for completed trip pricing row.**
- Platform retained amounts are explainable. **Met in `ride_pricing` breakdown.**
- Adjustments and refunds append new records instead of overwriting history. **Not met** — no refund/payout append stream on active path.

**Do not claim:** payment processing, wallet, Stripe, or payout execution. Pricing ledger ≠ payment truth.

### Action 8: Add Route Snapshot Foundation

**Status: done (foundation slice)** — `route_snapshots` table (`0010`), `backend/services/route_snapshots.py`, quote + complete persistence, `GET /drivers/rides/{ride_id}/route-snapshots`. Runtime OSRM **NO_GO** per `SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md`.

Goal: prevent the UI from inventing distance, route, or ETA truth.

Tasks:

- Add a route snapshot model. **Done** — `backend/models/route_snapshot.py`.
- Add a routing service interface. **Done** — `backend/services/routing_service.py`.
- Store provider, distance, duration, hashes, fallback flag, pricing link. **Done** for quote/complete roles; geometry polyline optional/null.
- Link fare quotes to route snapshots when route data is used. **Done** — `POST /rides/` and simulate-ride create `snapshot_role=quote` with `pricing_id`.
- Update UI copy so missing route data is shown as unavailable, not guessed. **Done** — map shows backend `route_provider`; accepts `haversine_fallback` honestly.

Done when:

- Backend can prove which route estimate was recorded per quote/completion. **Met** for quote + complete snapshots.
- Missing route facts are not replaced by frontend guesses. **Met** when fallback provider is shown.

**Do not claim:** production OSRM until runtime proof GO; road-network truth when `haversine_fallback` is set. Snapshots record backend truth, not container health.

**Detail:** `docs/HALFAPP_ROUTE_SNAPSHOTS_FOUNDATION_01.md`.

### Action 9: Production Hardening

**Status: partial** — first guards pass shipped (`HALFAPP_PRODUCTION_GUARDS_SECRET_SIMULATION_CORS_01`); revocation/logging/Postgres races remain.

Goal: make the active MVP deployable without local-development shortcuts.

Tasks:

- Replace development `SECRET_KEY`. **Done for production boot** — `production_guards.validate_secret_for_environment`; dev default still allowed locally.
- Restrict CORS to authorized origins. **Done for production** — explicit `CORS_ORIGINS`, no wildcard, no localhost union.
- Gate simulation endpoint. **Done** — `HALFAPP_ENABLE_RIDE_SIMULATION=1` required; stable `403` + `SIMULATION_DISABLED`.
- Define token refresh and revocation policy. **Sketch only** — `docs/HALFAPP_TOKEN_POLICY_SKETCH_01.md`.
- Add structured JSON logging. **Not done**.
- Add request/correlation IDs. **Partial** — correlation on ledger events; not full ASGI middleware.
- Validate transaction behavior on the selected production database. **Partial** — SQLite tests; Postgres claim races recommended.
- Add CI checks for backend tests, driver-app build, and critical E2E tests. **Done** in `.github/workflows/halfapp-driver-ci.yml`.
- Ensure mock mode and auth bypass are blocked in production builds. **Done** — `assert-prod-truth.mjs`.

Done when:

- The MVP can deploy without depending on local shortcuts.
- Critical behavior is observable in logs.
- Production configuration cannot silently enable mock or bypass behavior.

**Recommended next slice:** `HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01` or `HALFAPP_FINANCIAL_SETTLEMENT_BOUNDARY_OR_LEDGER_01`.

## First Implementation Slice

Start here:

1. Add backend-owned driver presence.
2. Add backend-backed ride hide/dismissal.
3. Add visibility records.
4. Update the active cockpit to use those backend facts.
5. Add tests proving refresh/reload does not change marketplace truth.

This is the best first slice because it directly removes local UI truth from the driver cockpit without requiring the full financial ledger, route engine, or new marketplace surface.

## Agent Operating Rules

- Work only through active `backend` and `driver-app` unless explicitly instructed otherwise.
- Do not wire `driver-app` to dossier `/supply`, `/demand`, or `/trip` without reconciliation doc completion.
- Do not revive legacy `frontend` as part of this plan.
- Do not present localStorage as marketplace truth.
- Do not make UI claims that the backend cannot prove.
- Do not add complex infrastructure before the current backend contract needs it.
- Prefer incremental backend records and tests over large untested rewrites.
- Keep documentation aligned with implemented behavior after each phase.

## Success Definition

HalfApp is moving in the right direction when every important screen can answer:

- Which backend record proves this?
- Which endpoint changed it?
- Which test covers it?
- Which audit event explains it?
- What happens on refresh, retry, conflict, or disconnect?

If those questions cannot be answered, the feature is not complete.
