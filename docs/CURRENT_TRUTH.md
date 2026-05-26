# HalfApp Current Truth

Date: 2026-05-25
Orders: `HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01`, `HALFAPP_STAGE0_TRUTH_BOUNDARY_LOCK_01`
Status: operational review spec for engineers and reviewers.

**Authoritative classification:** `docs/SYSTEM_TRUTH.md` — **delivery-driver execution** + shipped requester/ops/simulated payments; **not** a production marketplace OS.

**Agent execution plan:** `docs/HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md` · **Delivery big picture:** `docs/HALFAPP_PROGRAM_BRAIN_COMPREHENSIVE_REPORT_06.md`

This document is the short source of current product truth. It should be used when reviewing pull requests so legacy, mock, dormant, or future behavior is not accidentally described as live HalfApp behavior.

**This repository is not a complete mobility, routing, or city-scale ride-hailing operating system.** The active product is a driver lifecycle spine plus minimal rider API on the **v0.1 foundation** — see `docs/PRODUCT_BOUNDARY_STAGE0.md` and `docs/RIDE_APP_FOUNDATION_V0_1.md`.

---

## Verified claim boundary (accepted by owner — 2026-05-25)

Locked in by `HALFAPP_INTERNAL_PRODUCT_COMPLETION_PASS_01`.

**Allowed claim:** HalfApp is **internally usable and coherent as a local product shell** with honest labels and tested app surfaces (driver + rider + ops + backend).

**Forbidden claims** — must not appear in any UI, marketing, report, partner email, or external statement:

- HalfApp is ready for **public release**
- HalfApp is ready for **real delivery operations**
- HalfApp is ready for **legal launch** in any jurisdiction
- HalfApp executes **real payouts** to driver bank accounts
- HalfApp has a public-launch-ready routing SLA
- HalfApp is **deployed to the App Store or Play Store**
- HalfApp is a **marketplace**

External-launch readiness (Phases B–F in `docs/HALFAPP_REALITY_REPORT_01.md`) remains **NO_GO** until each blocked gate is proven:

- G3 Owner courier day (human walkthrough)
- Live-stack E2E session recovery
- Legal entity / insurance / hosting / mobile stores / public launch

Verdict status as of 2026-05-25: **INTERNAL_PRODUCT_COMPLETION_GO** · **PUBLIC_LAUNCH_NO_GO**.

Authoritative program snapshot: `docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md`.  
Reconciled backlog: `docs/BACKLOG.md`.  
**What to email experts:** `docs/HALFAPP_PARTNER_COMPLETION_PACKAGE_01.md` (v6.0 — questions only, open-board context).  
**Internal checklist:** `docs/HALFAPP_COMPLETION_MASTER_CHECKLIST_01.md`.  
**Staging closure orchestration:** `docs/HALFAPP_STAGING_CLOSURE_ORCHESTRATION_01.md`.

---

## Current state table (v0.1 — 2026-05-22)

| Area | Status | Proof |
|------|--------|-------|
| **Auth / role guards** | **GO** | JWT middleware + RBAC; `tests/test_auth_jwt_middleware.py`, `tests/test_rbac.py` |
| **Ride lifecycle** | **GO** | Structured transitions; `tests/test_ride_001_transition_guards.py`, `tests/test_ride_lifecycle.py` |
| **Open-board dispatch** | **GO** | First claim wins; `HALFAPP_OPEN_BOARD_DISPATCH=1`; `tests/test_ride_claim_lock_concurrency.py` |
| **Sequential dispatch cascade** | **GO** | RIDE-003; flag `0`; `tests/test_ride_003_dispatch_cascade.py` |
| **Driver approval** | **GO** | DRIVER-002; `tests/test_driver_approval.py` |
| **Pricing ledger** | **GO** | `ride_pricing` integer cents; `tests/test_pricing_ledger_v01.py` |
| **Settlement obligation rows** | **GO (boundary)** | `settlement_entries` — not payout execution; `tests/test_ride_settlement_ledger.py` |
| **Route snapshots** | **FOUNDATION** | Table + quote/complete rows; `tests/test_route_snapshots_foundation.py` |
| **OSRM code path** | **GO** | `tests/test_osrm_self_hosted_routing.py` (mocked HTTP) |
| **OSRM runtime** | **GO** | `scripts/prove_osrm_runtime.py` exit 0; real OSRM pytest passed — `docs/P0_G2_OSRM_RUNTIME_PROOF_01.md`, `docs/SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md` |
| **Payments / PSP** | **PARTIAL** | Phases 1–5: execution + reconciliation + Connect payout visibility (`PAYOUTS_ENABLED`); **no** bank deposit UI claims |
| **Token revocation / refresh** | **GO** | `0016_refresh_tokens_foundation`; `tests/test_auth_refresh_rotation.py` |
| **Production SECRET_KEY** | **GO** | `HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01`; `tests/test_production_guards.py` |
| **CORS** | **PARTIAL** | Production explicit origins; `tests/test_production_guards.py` |
| **Dossier spine** | **PARALLEL_NOT_WIRED** | Mounted `/supply`, `/demand`, `/trip`; not in `driver-app/src/utils/api.js` |
| **Engineering Intelligence Safe Shell** | **GO — LOCAL_CONTEXT_ONLY** | `#/engineering-intelligence`; `tests/test_engineering_intelligence_status.py` |
| **Ride product AI/LLM inference** | **NOT IMPLEMENTED** | No model inference on dispatch/pricing/lifecycle |
| **Backend test gate** | **GO** | `py -3.11 -m pytest -q --tb=no` — 383 passed, 9 skipped (SQLite dev, 2026-05-25); `docs/BACKEND_PYTEST_DRIFT_CLOSURE_01.md` |
| **Driver closed-beta readiness flow** | **GO** | DriverReadinessV1 + online gate + ride offer states + completion receipt; `docs/DRIVER_APP_REAL_APP_SHAPING_PASS_01.md`, `docs/DRIVER_READINESS_OPERATOR_DATA_PASS_01.md`; `npm test` 159 passed; `npm run build` passed; smoke loop Playwright passed |
| **Ride-flow UI proof** | **GO** | `docs/RIDE_FLOW_UI_PROOF_V0_2_STATUS.md` |
| **Two-sided loop (code)** | **SHIPPED** | `docs/HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md` Phases 1–4 |
| **Stable car API spine** | **GO** | `tests/test_stable_car_p0_01.py`, `scripts/owner_runbook_verify.py` |
| **Simulated ride_payments** | **GO** | migration `0032`, `tests/test_ride_payment_phase3.py` |
| **rider-app** | **SHIPPED** | Phase 1–3 — request, status, fare estimate, receipt, history |
| **ops-app** | **SHIPPED** | Phase 4 — `tests/test_ops_phase4.py` |

---

## P0 gates (HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01 — 2026-05-25)

| Gate | Status | Report |
|------|--------|--------|
| **G1** Postgres claim-race | **GO** | Fresh PostgreSQL 16 temporary cluster: `alembic upgrade head` + claim-race tests passed — `P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md` |
| **G2** OSRM runtime | **GO** | Portland OSRM runtime proof passed with `used_fallback=false`; backend real OSRM tests passed — `P0_G2_OSRM_RUNTIME_PROOF_01.md` |
| **G7** Alembic on PostgreSQL | **GO** | Fresh PostgreSQL 16 `alembic upgrade head` passed through `0036_driver_readiness_fields`; pytest PG proof passed — `P0_G7_ALEMBIC_POSTGRES_PROOF_01.md`, `ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md` |
| **G3** Owner courier day | **PENDING_OWNER** | `OWNER_COURIER_DAY_REPORT_01.md` |
| **G4** Dossier Path A/B | **GO (decision only)** | `DOSSIER_PATH_DECISION_01.md` — recommend Path A; no execution |
| **G5** Surface-freeze | **GO** | `P0_G5_SURFACE_FREEZE_REPORT_01.md` |
| **G6** SYSTEM_TRUTH sync | **GO** | `P0_G6_SYSTEM_TRUTH_RECONCILIATION_REPORT_01.md` |

**Overall P0:** **PARTIAL_GO** — remaining gate: G3 owner courier day; then P1.1 (0036 push).

---

## Do not reopen without rescope

Closed P0 / guard lanes — see `docs/BACKLOG.md` for proof links:

- **AUTH-001**, **RIDE-001**, **RIDE-002**, **RIDE-003**, **DRIVER-001B**, **DRIVER-002**
- **TEST-ISOLATION-01**, **HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01**, **HALFAPP_ENGINEERING_INTELLIGENCE_SAFE_SHELL_01**

Do not modify claim-lock, lifecycle guards, approval gates, cascade logic, or production SECRET_KEY behavior unless a new order explicitly rescopes the lane.

---

## Next executable work queue

**P0 (close gates):** G3 owner fills `OWNER_COURIER_DAY_REPORT_01.md`

**P1 (blocked until P0 GO):** Push (web) · stale presence policy · session E2E re-run

**Driver App Real-App Shaping Pass:** **GO** — `docs/DRIVER_APP_REAL_APP_SHAPING_PASS_01.md`, `docs/DRIVER_READINESS_OPERATOR_DATA_PASS_01.md`; DriverReadinessV1 gates go-online for profile/vehicle/docs/insurance/backend/manual approval blockers; ops now owns vehicle readiness + insurance expiry via `/admin/drivers/{driver_id}/readiness`; ride offer states include expired/conflict; completion receipt states recorded obligation + payout not executed; `npm test` 159 passed; `npm run build` passed; `npx playwright test tests/smoke-mvp.spec.ts` passed

**P1.3 Delivery vocabulary pass (extended):** **GO** — `docs/P1_3_DELIVERY_VOCABULARY_PASS_01.md`; extended to MapHome, DriverSettings, TripAuditReceipt, cockpit components (MarketplaceBottomSheet, DiagnosticsDrawer, RideChatPanel, EarningsVisibilityPanel, StreetIntelligencePanel); 150 npm tests pass; guards clean

**Slice 9 — Trips & earnings polish:** **GO** — `docs/TRIPS_EARNINGS_POLISH_01.md`; delivery vocabulary complete across TripsList, Earnings, EarningsChart; EarningsChart already wired (not dormant); 150 npm tests pass; guards clean

**Slice 5 — Notifications product UI:** **GO** — `docs/NOTIFICATIONS_PRODUCT_UI_01.md`; backend-only list, empty state, demo tab DEV-gated, AppShellLayout chrome; stale E2E heading assertion fixed; 150 npm tests pass

**Slice 4 — Profile + settings shell:** **GO** — `docs/PROFILE_SETTINGS_SHELL_01.md`; vehicle/contact/session/preferences/app-profile all via `/drivers/*`; AppShellLayout; no mock data in prod; 150 npm tests pass

**Slice 1 — Internal owner test mode:** **GO** — `docs/INTERNAL_OWNER_TEST_MODE_01.md`; BetaFirstRunAck + BetaTruthNotice gated to flag; simulation labels correct; owner runbook complete; prod build clean

**Slice 8 — Deploy CORS/observability:** **GO** — `docs/DEPLOY_CORS_OBSERVABILITY_01.md`; CORS already hardened; new `RequestLoggingMiddleware` emits structured JSON with `request_id`/`driver_id`/`ride_id`; 7 new middleware tests pass

**Slice 6 — Cockpit session resilience:** **GO (code+backend)** / **TODO (E2E run)** — `docs/COCKPIT_SESSION_RESILIENCE_01.md`; `GET /drivers/me/active-ride`, `useActiveRide`, `CockpitSkeleton`, `cockpit-resume-notice`, stale-presence banner all shipped; E2E `session-recovery.spec.ts` exists, owner runs against live stack

**Slice 7 — Token session safety:** **GO** — `docs/TOKEN_SESSION_SAFETY_01.md`; refresh rotation (migration 0016), logout-all-devices, password-change auto-revoke; `test_auth_refresh_rotation.py` passes; `settings-logout-all-btn` shipped

**Slice 10 — OpenAPI truth sync:** **GO** — `docs/OPENAPI_TRUTH_SYNC_01.md`; Ticket 1.3 fail-on-drift in CI (`truth-and-drift`); BACKLOG + CURRENT_TRUTH reconciled with all shipped slice reports; backend 390 passed, driver-app 150 passed

**Product completion:** `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_01.md` — **GO** (Settings + cockpit resume)  

**Deferred:** External trusted-courier beta — `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`.

**P2 (one fork):** POD · merchant payload · real Stripe pilot — pick one after P0+P1

Details: `docs/BACKLOG.md`.

---

## Active product surfaces (only these)

| Surface | Path |
|---------|------|
| Backend API | `backend/` — FastAPI courier + requester + ops |
| Driver app | `driver-app/` — courier cockpit (3022) |
| Rider app | `rider-app/` — requester (3023) |
| Ops console | `ops-app/` — operator panel (3024) |

Active entry points:

- `backend/main.py`
- `driver-app/src/App.jsx`
- `docs/RIDE_LIFECYCLE_CONTRACT.md`

### Driver-app API boundary (non-negotiable)

- The driver app uses the **`/drivers/*` active path only** (plus `/auth/*` for session).
- `driver-app/src/utils/api.js` must **not** call dossier foundation endpoints: `/supply/*`, `/demand/*`, `/trip/*`.
- Those dossier routes are mounted on the API for tests/foundation only — see `docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md`.

Active backend product surface:

- `backend`: FastAPI service for auth, driver profiles, backend-owned driver presence, ride lifecycle, **v0.1 integer-cent pricing ledger** (`ride_pricing`), routing provider metadata on rides, rider ride create/cancel (API only), notifications, and completed-trip earnings summaries.
- SQLAlchemy models loaded at startup include `User`, `Ride`, `Metric`, `RideVisibility`, `RideClaimAttempt`, `Event`, `MarketplaceLedgerEntry`, `DriverPresence`, `RidePricing`, `PricingPolicy`, dossier foundation models, and the route-owned `Notification` model.
- The backend is the authority for lifecycle state, timestamps, assigned driver, driver presence, heartbeat, **pricing quote/lock**, route provider fields, completed-trip earnings summaries, rider cancellation, dispatch visibility, hidden rides, claim attempts, and audit events.

Active frontend product surface:

- `driver-app`: React/Vite **driver-only** app.
- The active route tree is defined by `driver-app/src/App.jsx`.
- The driver cockpit, trips, earnings, notifications, and profile screens must render backend-provided facts or clearly labeled local-only/mock state.

---

## Inactive / not production surfaces

| Surface | Status |
|---------|--------|
| `frontend/` | **ARCHIVE · NOT WIRED · NOT PRODUCTION** — see `frontend/README.md` |
| `rider-stub/` | **DEMO ONLY** — not a rider product; see `rider-stub/README.md` |
| `video-gate/` | Unrelated video tooling — not ride-hailing product. |
| Dormant routers | `routes/admin`, `routes/admin_access`, `routes/rides` (legacy), `routes/users`, `routes/test` — **not** in `main.py`. See `docs/DORMANT_ROUTERS_INVENTORY.md`. |
| Dossier marketplace spine | `POST /supply/heartbeat`, `POST /demand/request`, `POST /trip/complete` — mounted for foundation/tests; **not** driver-app product truth. |
| Dormant `driver-app` components | Not imported by `App.jsx`. |
| Engineering Intelligence Safe Shell | `driver-app` route `#/engineering-intelligence` — **LOCAL_CONTEXT_ONLY**, no external AI; dev flag `VITE_ENABLE_ENGINEERING_INTELLIGENCE=1`. |
| Backend engineering-assistant proxy | `GET/POST /engineering-assistant/*` — **DISABLED BY DEFAULT** (`ENGINEERING_ASSISTANT_ENABLED` unset/false). Requires explicit enable + server `ANTHROPIC_API_KEY`; **not wired** to Engineering Intelligence shell. |
| Ride product LLM/ML inference | **NOT IMPLEMENTED** — no in-process model inference on dispatch, pricing, or lifecycle spine. |

Review rule: code not reachable from active entry points is **not** current product behavior unless a PR explicitly registers, tests, and documents it.

---

## v0.1 map foundation (current truth)

The driver app uses **Leaflet + OpenStreetMap tiles** for the in-app map foundation (`driver-app/src/components/MapView.jsx`, `mapProvider.js`).

- The map is a **visual marketplace/navigation surface**, not full route-truth proof by itself.
- **Route provider truth** comes from **backend route metadata** on the ride (`route_provider`, `traffic_provider`, `used_fallback`, etc.) — stamped by `routing_service` / `map_route_foundation` — not from frontend drawing alone.
- External navigation uses **Google Maps links** (`Open in Google Maps`) — no embed, no Maps API key in the active path.

Do **not** describe the in-app map as a stylized SVG, fake map, or placeholder map.

---

## v0.1 pricing ledger (current truth)

**`ride_pricing`** is real v0.1 pricing truth on the active path:

- All money fields use **integer cents**.
- Quote/completion flows persist breakdown rows (`driver_shareable_fare_cents`, commission, service fee, tips, pass-through fees, `customer_total_cents`, etc.).
- Trip completion sets **`financial_locked`** on the pricing row.

**This is not:**

- Payment settlement, wallet balance, payout execution, Stripe capture, or refund processing.
- The dossier double-entry `ledger_*` tables (parallel foundation spine — not driver-app financial truth).

Legacy `fare_amount` on `rides` may still appear for display compatibility when pricing exists; UI labels must not confuse driver payout with customer total. See `driver-app/src/utils/ridePricingDisplay.js`.

---

## v0.1 routing (current truth)

A **routing abstraction** exists (`backend/services/routing_service.py`):

- **OSRM self-hosted** code path exists and is **unit-tested** (mocked HTTP).
- **Runtime OSRM proof** is **GO** on this host per `docs/P0_G2_OSRM_RUNTIME_PROOF_01.md`: `scripts/prove_osrm_runtime.py` exited 0 with `route_provider=osrm_self_hosted` and `used_fallback=false` across three Portland routes.
- When OSRM is unavailable and `ROUTING_FALLBACK_ENABLED` is true, the honest provider is **`haversine_fallback`** — not road-network route truth.
- Optional experimental **traffic signal** buffering is not commercial paid-traffic APIs.

A **`route_snapshots`** table exists (foundation — migration `0010`). Driver UI still uses ride route fields and provider metadata; snapshot read UI is **not** shipped. Distance/duration for pricing tie to ride fields + snapshots at quote/complete when written.

---

## Explicitly not shipped (forbidden to claim as live)

- **No payout-to-bank product claims in driver UI** — Phase 4 shows execution reconciliation only (`available_cents` is derived, not “paid”). Full payout/deposit language waits for Phase 5 provider payout proof.
- **Payments execution is flag-gated** — charge intents, Stripe webhooks, refunds/disputes, and `/drivers/me/payment-*` visibility exist when `PAYMENTS_ENABLED`; not a marketed wallet or instant-pay product.
- **No routing SLA / public launch claim** — OSRM runtime proof is GO on this host, but public launch still requires operational hosting, monitoring, and owner acceptance.
- **No live ETA product** — do not market turn-by-turn ETA as shipped truth.
- **No commercial traffic APIs** — experimental regional traffic signals only; not Google/Mapbox traffic.
- **No production-grade requester product** — Phase 1–3 `rider-app` covers request, status, fare estimate, receipt on complete, and history; no merchant/order payload or real payment method UX yet.
- **Simulated payments (Phase 3)** — `ride_payments` table tracks pending → authorized → captured per ride; no Stripe/PSP in the two-sided loop.
- **No nearest-driver matching by default** — open-board pool by default; optional **`HALFAPP_AUTO_ASSIGN=1`** assigns nearest/first-available online driver on rider create (Phase 2).
- **No city-scale mobility OS** — no multi-city ops, zones, airport rules, or fleet command center.
- **No geocoding proof** — coordinates must be supplied; address labels are not proved locations.
- **No dossier auto-match as driver-app dispatch** — open board on `/drivers/*` only.

---

## Mounted routes

Registered only via `backend/main.py`. Full inventory: `docs/DORMANT_ROUTERS_INVENTORY.md`.

Route groups:

- `GET /health`
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `GET /drivers/` … `GET /drivers/statistics` (see inventory for full list)
- `GET /internal/system-health`
- `POST /rides/`, `POST /rides/{ride_id}/cancel`, `POST /rides/{ride_id}/action`
- `GET /notifications/` … `POST /notifications/driver/ride-alert`
- `POST /supply/heartbeat`, `POST /demand/request`, `POST /trip/complete` — **dossier foundation only**; mounted for tests, **not** used by `driver-app`. See `docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md`.

How to verify:

```powershell
cd c:\Users\him\Desktop\halfapp-driver
py -3.11 scripts/print_active_routes.py
```

```powershell
cd backend
py -3.11 -c "from main import app; print(sorted({getattr(r,'path','') for r in app.routes}))"
```

---

## Supported lifecycle statuses

Implemented storage statuses:

- `requested`: open pool ride, unassigned (may have `ride_pricing` → v0.1 display `priced`).
- `accepted`: ride claimed by a driver.
- `driver_arrived`: driver marked pickup arrival.
- `in_progress`: trip has started.
- `completed`: terminal completed ride; pricing locked when v0.1 path applies.
- `cancelled`: terminal rider cancellation from `requested` or `accepted`.

Implemented driver path:

`requested -> accepted -> driver_arrived -> in_progress -> completed`

Implemented rider cancel path:

`requested|accepted -> cancelled`

Current driver decline behavior:

`accepted -> requested`

Driver decline is not a terminal rejection in the MVP. It releases the ride back to the open pool, clears the assigned driver, clears active-leg timestamps, and may store a reason in `lifecycle_reason`.

Legacy storage aliases normalized by the API and not emitted by active flows:

- `en_route_to_pickup`
- `arrived_at_pickup`
- `waiting_for_rider`

Reserved but not emitted by active flows:

- `declined`
- `expired`

How to verify:

```powershell
cd backend
py -3.11 scripts/print_openapi_driver_rides.py
py -3.11 -m pytest tests/test_ride_lifecycle.py tests/test_ride_flow_ui_proof.py -q
```

---

## Strict no-invention UI rules

The driver app must not present a field as real product behavior unless it is provided by the backend contract or clearly labeled as local/mock-only.

The UI must not invent:

- Live ETA as a product guarantee.
- Road-network route truth when backend reports `haversine_fallback`.
- Commercial traffic state.
- Nearest-driver matching.
- Dispatch metadata not returned by the backend.
- Settled payouts, wallet balances, or PSP capture/refund status.
- Hardcoded city map coordinates as real ride coordinates.

Allowed current claims:

- Backend-backed driver auth.
- Backend-backed driver presence: `available`, `offline`, `paused`, `stale`, and `disconnected`.
- Backend-backed heartbeat timestamps for driver liveness.
- Backend-backed ride lifecycle transitions.
- Backend-backed rider create/cancel for the minimal rider-side lifecycle (API).
- **Integer-cent pricing ledger** on rides (`pricing` / `RidePricingView`) including locked completion breakdown.
- Backend-recorded operational metrics for available ride counts, claim conflicts, and lifecycle timing.
- Backend-recorded ride visibility and claim attempt rows for the open-board dispatch flow.
- Backend-returned dispatch rank, policy version, and generated timestamp on available ride views.
- Backend-backed driver ride dismissal through `POST /drivers/rides/{ride_id}/hide` and legacy alias `POST /drivers/dismiss-ride/{ride_id}`.
- Append-only `events` and `marketplace_ledger_events` for key ride, claim, and earning actions.
- **Leaflet/OSM in-app map** with backend route provider metadata on the ride.
- **External Google Maps navigation** links (no embed).
- Explicit backend simulation rides when `VITE_ENABLE_RIDE_SIMULATION=true`.
- Explicit mock fallback only when `VITE_ALLOW_OFFLINE_MOCK=true`.

How to verify:

```powershell
cd driver-app
npm run build
npm test
npm run test:e2e:trust
npm run test:e2e:ride-flow
```

---

## Mock and simulation policy

Backend simulation:

- Enabled through `VITE_ENABLE_RIDE_SIMULATION=true`.
- Calls `POST /drivers/simulate-ride`.
- Creates a real backend `Ride` row in `requested` status.
- Marks the row with `lifecycle_reason="simulation"`.
- Uses the normal backend lifecycle after creation.

Offline mock mode:

- Enabled only through `VITE_ALLOW_OFFLINE_MOCK=true`.
- Uses localStorage-backed mock drivers and mock rides.
- Exists for development and E2E fallback scenarios.
- Must never be presented as production behavior.

Test-only guard bypass:

- `disable_guard` only works when `VITE_ENABLE_GUARD_BYPASS=true` and the Vite mode is not production.
- `npm run build` fails if `VITE_ALLOW_OFFLINE_MOCK=true` or `VITE_ENABLE_GUARD_BYPASS=true`.
- It is not a security model and must not be enabled in production builds.

Review rule: any PR touching mock, simulation, or guard-bypass behavior must prove production builds cannot silently enter those paths.

---

## Production security (2026-05-22)

| Control | Status |
|---------|--------|
| **Production `SECRET_KEY` boot guard** | **GO** (`HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01`) — `assert_safe_secret_key_for_runtime()` in `backend/production_guards.py`; wired at `config` import and `backend/main.py` boot. Production-like mode (`HALFAPP_ENV`, `ENV`, `APP_ENV`, or `FASTAPI_ENV` = production) fails fast with `Unsafe SECRET_KEY for production` when the key is missing, empty, `change_me`, other known placeholders, or shorter than 32 characters. The error never logs the secret value. See `docs/HALFAPP_PRODUCTION_GUARDS_SECRET_SIMULATION_CORS_01.md`. |
| **Token revocation / refresh** | **GO** — refresh rotation + `logout-all`; `tests/test_auth_refresh_rotation.py` |
| **CORS hardening** | **PARTIAL** — wildcard forbidden; production requires explicit `CORS_ORIGINS`; localhost union only in dev/test |
| **Payments / PSP** | **PARTIAL** — execution + driver reconciliation visibility (Phases 1–4); payout/deposit claims **NO_GO** until Phase 5 |
| **OSRM runtime proof** | **GO** on this host; keep fallback honesty when OSRM is down |

---

## Current system limits

The current MVP does not yet provide:

- Bank payout / deposit visibility (Phase 5) or marketed instant-pay / wallet product.
- Driver-facing route snapshot browser / audit UI (table exists; UI does not).
- **Runtime-proved** self-hosted OSRM in all environments (see routing status doc).
- Geocoding from address strings with audit proof.
- Production-grade requester mobile app, full admin ops console, or nearest-driver dispatch by default.
- Driver-facing audit UI projections over ledger events (events exist; UI does not).
- Structured observability (metrics/logging product) beyond existing health endpoints.
- WebSocket real-time presence gateway.

Alembic drift must stay clean before schema-heavy work (`alembic revision --autogenerate` after `upgrade head`). Current head includes v0.1 revisions through `0026` (refresh tokens, payment execution, Stripe accounts, payment events, payout tables, driver profile/settings, ride-write idempotency replays).

---

### HALFAPP_PAYMENTS_EXECUTION_04 — GO (Phase 4: driver earnings visibility)

**Backend (GO):**

- `backend/services/payment_reconciliation.py` — Phase 4 UI aliases + `list_driver_payment_executions` (driver-scoped via `Ride.driver_id`)
- `GET /drivers/me/payment-reconciliation`
- `GET /drivers/me/payment-executions`

**Frontend (GO):**

- `driver-app/src/components/EarningsVisibilityPanel.jsx` → `Earnings.jsx` + `MarketplaceBottomSheet` (compact)
- `driverAPI.getPaymentReconciliation()` / `getPaymentExecutions()`
- `betaTruthCopy` keys `BETA_PAYMENT_*` — no payout/deposit marketing claims
- CI guard: `driver-app/scripts/assert-no-money-claims.mjs` (runs in `npm test`)

**Tests (GO):**

- `backend/tests/test_payment_reconciliation_phase4.py`
- `driver-app/tests/unit/earningsVisibilityPanel.test.js`

**Truth / semantics (unchanged):**

- Trip audit copy: `payment_execution: not_implemented`
- `pricing_earned_cents` = obligation truth; `available_cents` = derived execution net — **not** payout complete
- Reconciliation is execution visibility; provider payout buckets are Phase 5 (`docs/HALFAPP_PAYMENTS_EXECUTION_05_GO.md`)

**Not in scope:**

- MapHome mount
- `earnings.py` split module
- Ledger / payout / transfer tracking (Phase 5)

**Risk boundary:**

- Driver UI must not claim bank deposit / “sent to your bank” even when provider payout status is shown.

---

### HALFAPP_PAYMENTS_EXECUTION_05 — GO (Phase 5: transfer/payout ingestion + provider payout visibility)

**Full GO ritual, PR body, staging checklist:** `docs/HALFAPP_PAYMENTS_EXECUTION_05_GO.md`

**Summary:**

- Schema: migrations `0020`–`0023`; `payment_execution.external_charge_id`
- Backend (`PAYOUTS_ENABLED`): dual webhook secrets; `transfer.*` / `payout.*` ingestion; `GET /drivers/me/payouts`; reconciliation `payout_paid_cents`, `payout_pending_cents`, `provider_payout_visible` (true when Connect account exists + flag on)
- Frontend: `EarningsVisibilityPanel` + `BETA_PAYOUT_*`; `driverAPI.getPayouts()`
- Tests: `test_payout_ingestion_phase5.py`; `npm test` + money-claim guard
- Phase 5.1: `payout_failed_cents`, `payout_last_status`, `payout_last_at` on reconciliation + UI rows

**Semantics:** `payout_paid_cents` = Stripe payout status `paid` on connected account — **not** bank deposit confirmation.

---

## Truth boundary checklist

Before approving behavior claims, confirm:

- Product behavior is reachable from `backend/main.py` and/or `driver-app/src/App.jsx`.
- Driver-app does not call dossier `/supply`, `/demand`, or `/trip` endpoints.
- Lifecycle and payload claims match `docs/RIDE_LIFECYCLE_CONTRACT.md`.
- OpenAPI exposes the claimed path and schema.
- `py -3.11 scripts/print_active_routes.py` includes the claimed path.
- Backend tests cover lifecycle, dispatch race behavior, cancellation, pricing, and routing when those areas change.
- Driver-app tests cover mock-off/trust and ride-flow when UI claims backend truth.
- Mock mode is labeled mock-only.
- Simulation is labeled simulation and creates backend rows.
- Dormant code is not described as current behavior.
- No forbidden claim from `docs/PRODUCT_BOUNDARY_STAGE0.md` appears in UI or marketing copy.
- Pricing claims cite `ride_pricing`; payment/settlement claims do not appear unless explicitly shipped.
