# Final Report: HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01

**Date:** 2026-05-23  
**Verdict:** **PRODUCT_COMPLETION_IN_PROGRESS** (strong MVP → standalone driver product)  
**Direction:** Complete HalfApp Driver as a serious **internal-only** driver app first. **External trusted-driver beta is deferred.**

---

## Direction reset (authoritative — 2026-05-23)

**Do not start trusted-driver beta work.** HalfApp Driver is being completed as a **standalone driver product** first. Testing stays **internal only** (owner’s car, controlled local runs).

| In scope now | Out of scope now |
|--------------|------------------|
| Finish driver app surfaces on `/drivers/*` | Inviting outside drivers (5–20 or any cohort) |
| Owner-car, controlled local test runs | Beta agreements, tester onboarding, waitlists |
| Internal test-ride labeling (`lifecycle_reason=simulation`, dev simulation dock) | Public/closed **beta** copy, beta truth sheets as a launch program |
| Hardening: session, Postgres races, OSRM runtime, CORS, observability | PSP, wallet, cashout, rider app, dossier wiring |
| Honest ledger/obligation language (no money movement) | Money pilot or payout execution |
| Product completion roadmap (this doc) | Beta operations roadmap |

**Spine:** `backend` + `driver-app` only. Active API boundary: **`/drivers/*`** + `/auth/*`. Dossier (`/supply`, `/demand`, `/trip`) remains **parallel, not wired** to the driver app.

---

## Current completed product surfaces

Evidence: closed P0 lanes in `docs/BACKLOG.md`, E2E lock reports, `docs/CURRENT_TRUTH.md`.

| Surface | Route / entry | Status | Proof / notes |
|---------|---------------|--------|----------------|
| **Auth** | `/`, `/login` → JWT | **GO** | `tests/test_auth_jwt_middleware.py`, `tests/test_rbac.py` |
| **Cockpit (map-first)** | `/driver` (`MapHome`) | **GO** | `docs/HALFAPP_DRIVER_COCKPIT_RIDE_FLOW_E2E_LOCK_01_REPORT.md` |
| **Online / offline** | Cockpit + `POST` presence/heartbeat | **GO** | Backend presence; 30s heartbeat in `MapHome.jsx` |
| **Open-board dispatch** | Incoming sheet + atomic claim | **GO** | `tests/test_ride_claim_lock_concurrency.py` |
| **Ride lifecycle** | Accept → arrive → start → complete | **GO** | `tests/test_ride_001_transition_guards.py`, ride-flow UI proof |
| **Trips list** | `/driver/trips` | **GO** | Backend completed rides; audit link on rows |
| **Trip audit / receipt** | `/driver/trips/:rideId/audit` | **GO** | `docs/HALFAPP_DRIVER_AUDIT_READ_UI_01_REPORT.md` |
| **Route truth (read)** | Cockpit `RouteTruthDetails` + audit section | **GO** | `docs/HALFAPP_ROUTE_SNAPSHOT_READ_UI_01_REPORT.md`, route E2E lock |
| **Earnings summary** | `/driver/earnings` | **GO** | `GET /drivers/earnings`; backend totals, recent trips |
| **Pricing ledger display** | `RidePayoutSummary`, trip truth | **GO** | Integer cents from `ride_pricing`; `financial_locked` on complete |
| **Profile (basic)** | `/driver/profile` | **PARTIAL** | `getProfile`, vehicle fields, stats tab — see gaps below |
| **Notifications (read)** | `/driver/notifications` | **PARTIAL** | API wired; UI legacy styling; messages tab demo-only |
| **Dev simulation** | `VITE_ENABLE_RIDE_SIMULATION`, diagnostics dock | **GO (dev)** | `lifecycle_reason=simulation`; not production |
| **Engineering intelligence** | `#/engineering-intelligence` (flag) | **GO (dev)** | Local context only; not ride product |

**Backend foundations (not “driver UI” but product truth):** `ride_pricing`, `settlement_entries` (obligation rows only), `marketplace_ledger_events`, `route_snapshots`, rider API create/cancel (no rider app).

---

## Missing or incomplete driver-app surfaces

Prioritized for **product completion**, not beta ops.

| Surface | Gap | Completion bar |
|---------|-----|----------------|
| **Cockpit** | Active-ride recovery after refresh; clearer stale-presence UX; optional settings shortcut | Driver can resume in-progress ride reliably; offline/stale states are explicit |
| **Trips** | List filters (date/status); consistent “calculation record” labels vs raw “payout” in row chrome | Trips screen matches audit/earnings language; deep links stable |
| **Earnings** | No charts wired (`EarningsChart.jsx` dormant); period breakdown thin | Owner can validate totals against audit for any trip |
| **Audit / receipt** | Primary narrative could surface top 3 lifecycle events above fold | One-screen “what happened on this trip” without opening technical proof |
| **Route truth** | OSRM runtime **GO** on this host — UI must still label fallback when OSRM is down | Hosted monitoring/SLA before public routing claims |
| **Profile / settings** | No dedicated **Settings** route; mixed tabs; no session/device panel | Vehicle + contact + **session info** + app preferences in one coherent shell (`AppShellLayout`) |
| **Notifications** | Light theme unlike cockpit; no mark-read if backend supports; messages are demo | Notifications match product chrome; backend-only or explicit empty |
| **Offline / online** | Background tab / network loss behavior not product-tested | Documented behavior: heartbeat failure, go-offline guards, “finish ride before offline” |
| **Internal test mode** | Simulation scattered across flags (`VITE_ENABLE_RIDE_SIMULATION`, mock, beta notices) | Single **owner internal test** framing — no beta onboarding artifacts in default path |
| **Navigation shell** | `BottomNavigation` on some screens only | Consistent nav across trips, earnings, profile, notifications |

**Dormant / do not count as product:** `frontend/`, `Dashboard.jsx`, `RideList.jsx`, `AdminDashboard.jsx`, dossier API calls from driver-app.

---

## Internal owner-car testing mode (target design)

**Purpose:** Owner tests lifecycle, pricing, audit, and routing honesty using their own vehicle and controlled local runs — **not** a driver cohort program.

| Mechanism | Today | Target |
|-----------|-------|--------|
| Create test ride | `VITE_ENABLE_RIDE_SIMULATION=true` + diagnostics / dev dock | Keep dev-only; label **Internal test ride** (not “beta ride”) |
| Rider API / Playwright | Harness creates `requested` rides | Documented owner runbook: one-command local E2E |
| Money framing | Ledger shows dollars; no PSP | UI: **Calculation record — no charge, no payout** (internal, not public beta copy) |
| Flags to **avoid** in owner builds | `VITE_BETA_NO_MONEY_TRUTH`, beta first-run ack | Deferred — not part of product completion path |
| Production build | `assert-prod-truth.mjs` blocks mock/guard bypass | Unchanged |

**Owner runbook (to add in slice 1):** env template, start backend + driver-app, go online, create simulation ride or POST `/rides/`, complete flow, open trip audit, verify route truth fallback label.

---

## Hardening gates

| Gate | Current | Required for standalone internal product | Blocks external beta | Blocks money pilot |
|------|---------|------------------------------------------|----------------------|-------------------|
| **Auth / RBAC** | GO | Maintain | — | — |
| **Lifecycle + claim lock (SQLite)** | GO | Maintain | — | — |
| **Postgres claim-race proof** | **GO** — fresh PostgreSQL 16 Alembic + claim-race proof passed | Keep CI proof green | Yes | Yes |
| **OSRM runtime** | **GO** on this host | Hosted process monitoring before public routing claims | Yes (honesty) | Yes (distance-priced trust) |
| **Token refresh / revocation** | NOT IMPLEMENTED | Design + MVP (logout all, rotation) | Yes | Yes |
| **CORS / production guards** | PARTIAL | Explicit origins documented per deploy | Yes | Yes |
| **SECRET_KEY guard** | GO | Ops sets real secret in deploy | Yes | Yes |
| **Observability** | Health endpoint; thin structured logging | Request ID, ride/driver correlation in logs | Recommended | Yes |
| **OpenAPI drift CI** | PARTIAL | Fail CI on contract drift | Recommended | Yes |
| **Payments / PSP** | NO_GO | Stay NO_GO until explicit order | — | Yes (by definition) |

---

## What remains before any external beta

**External trusted-driver beta is deferred.** Do not plan for 5–20 drivers, beta agreements, or beta-specific onboarding until all of the following are true:

1. **Product surfaces complete** — cockpit, trips, earnings, audit, route truth, profile/settings, notifications, offline/online behavior meet the completion bars above.
2. **Internal owner-car program** — repeatable runbook with simulation + rider API; no reliance on Playwright-only for day-to-day testing.
3. **Postgres claim-race** — proven on PostgreSQL and kept green in CI.
4. **OSRM runtime** — GO on this host; hosted deployment must preserve fallback honesty and monitoring.
5. **Session safety** — refresh/revocation MVP for lost devices.
6. **Deploy hardening** — CORS, secrets, logging, on-call basics.
7. **Support / legal** — out of engineering scope here; explicitly not started.
8. **No beta copy path** — remove or gate `VITE_BETA_NO_MONEY_TRUTH`, `BetaFirstRunAck`, and beta truth sheets from default product builds.

---

## What remains before any money pilot

Money pilot is **separate** and **later** than external beta. Requires everything above, plus:

1. **PSP design** — capture, settlement, reconciliation, refunds (not started).
2. **Payout execution** — beyond `settlement_entries` obligation rows.
3. **Rider billing truth** — rider app or contracted demand channel.
4. **Dossier decision** — Path A vs B documented; no dual-write from driver UI.
5. **Compliance** — tax, insurance, background checks (out of repo scope).
6. **Admin / ops tooling** — disputes, manual adjustments, fraud basics.

Until then: **no wallet, no cashout, no “paid out” UI**, no PSP integration.

---

## Next 10 implementation slices (ordered)

Product completion and internal testing only. **No beta operations work.**

### 1. `INTERNAL_OWNER_TEST_MODE_01` — Internal test labeling & runbook

- Consolidate copy: **Internal test ride** / **Owner test run** (replace beta-first-run and `VITE_BETA_NO_MONEY_TRUTH` as default path).
- Document owner-car runbook (`docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md`).
- Keep `VITE_ENABLE_RIDE_SIMULATION` dev-only; production build unchanged.
- **Done when:** Owner can run a full trip locally without beta flags or external onboarding artifacts.

### 2. `OSRM_RUNTIME_PROOF_01` — Docker/VPS runtime GO

- **DONE 2026-05-25:** `docs/P0_G2_OSRM_RUNTIME_PROOF_01.md`; proof script shows `osrm_self_hosted`, `used_fallback=false`.

### 3. `POSTGRES_CLAIM_RACE_CI_01` — Postgres migrations + CI matrix

- **DONE 2026-05-25:** `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md`, `docs/P0_G7_ALEMBIC_POSTGRES_PROOF_01.md`; `CURRENT_TRUTH` Postgres rows **GO**.

### 4. `PROFILE_SETTINGS_SHELL_01` — Profile + settings product surface

- Unified settings: vehicle, contact, availability, **session** (token issued, logout), app preferences.
- Match `AppShellLayout` / cockpit visual system.
- **Done when:** All profile edits go through `/drivers/*`; no mock profile data in production build.

### 5. `NOTIFICATIONS_PRODUCT_UI_01` — Notifications inbox completion

- Align notifications page with driver app chrome (`ha-*` / dark shell).
- Backend-only list; honest empty state; remove or gate demo messages tab.
- **Done when:** `GET /drivers/notifications` (or equivalent) is the only source; UI matches trips/earnings quality bar.

### 6. `COCKPIT_SESSION_RESILIENCE_01` — Offline/online & ride recovery

- Refresh/resume active ride; stale presence messaging; block offline during active ride (existing hint → full behavior).
- Network error recovery on accept/advance.
- **Done when:** Owner test: refresh mid-ride does not lose state; heartbeat stale → visible status.

### 7. `TOKEN_SESSION_SAFETY_01` — Refresh / revocation MVP

- Design doc + minimal implementation (refresh token or rotation + revocation list).
- Driver UI: “Sign out everywhere” on profile/settings.
- **Done when:** Lost-device scenario covered by tests; no infinite-lived JWT without ops story.

### 8. `DEPLOY_CORS_OBSERVABILITY_01` — Production deploy hardening

- CORS allowlist per environment; structured request logging with `ride_id` / `driver_id` where applicable.
- **Done when:** Deploy checklist + `GET /internal/system-health` used in ops doc.

### 9. `TRIPS_EARNINGS_POLISH_01` — Trips & earnings consistency

- Align row labels with audit language (calculation record, not payout sent).
- Optional: wire or remove dormant `EarningsChart.jsx`.
- **Done when:** Trips → audit → earnings tells one consistent story in UI tests.

### 10. `OPENAPI_TRUTH_SYNC_01` — Contract CI + doc reconciliation

- OpenAPI snapshot fail-on-drift (Ticket 1.3).
- Update `BACKLOG.md` / `CURRENT_TRUTH.md`: audit UI, route read UI **GO**; remove deferred beta from P0 queue.
- **Done when:** Agent brain docs match code; CI blocks silent API drift.

---

## Explicit deferrals

- **External trusted-driver beta** — **DEFERRED.** No invitations, cohorts, beta agreements, or beta onboarding flows until slices 1–10 and hardening gates are met and leadership re-opens the lane.
- **Public marketing / waitlist** — **DEFERRED.**
- **PSP / wallet / cashout / rider app / dossier wiring** — **OUT OF SCOPE** for this roadmap.

---

## Related docs

| Doc | Use |
|-----|-----|
| `docs/CURRENT_TRUTH.md` | Short operational truth table |
| `docs/BACKLOG.md` | Ticket classification |
| `docs/PRODUCT_BOUNDARY_STAGE0.md` | Forbidden claims |
| `docs/HALFAPP_DRIVER_PROGRAM_MASTER_REPORT_01.md` | Deep program context (beta sections superseded by this roadmap for planning) |
| `docs/RIDE_FLOW_UI_PROOF_V0_2_STATUS.md` | Cockpit E2E |
| `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` | OSRM runtime blocker |

---

## Verdict

**PRODUCT_COMPLETION_IN_PROGRESS** — The driver app is a **strong MVP** with a proven `/drivers/*` lifecycle, audit, route truth, and earnings surfaces. The next engineering tranche should **complete the standalone driver product** and **owner-only internal testing**, while hardening Postgres, OSRM, session, and deploy paths. **Do not execute trusted-driver beta work** until this roadmap’s gates and slices are satisfied and explicitly re-scoped.
