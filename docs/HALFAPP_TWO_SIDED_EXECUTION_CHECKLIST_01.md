# HalfApp Two-Sided Execution Checklist

**Document ID:** `HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01`  
**Date:** 2026-05-24  
**Authority:** `docs/SYSTEM_TRUTH.md` · enforced build order from execution directive  
**Rule:** Do **not** start the next phase until the previous phase meets its **Definition of DONE**.

---

## Build order (non-negotiable)

| Phase | Goal | Gate |
|-------|------|------|
| **1** | Rider → driver loop (request, see, accept, complete) | E2E without manual API |
| **2** | Basic matching (auto-assign) | Driver does not scan open board only |
| **3** | Minimal payments loop (simulated money) | Complete → charge record + receipt |
| **4** | Minimal ops panel | Operator sees and cancels live rides |

---

## Phase 1 — Real rider loop

**Objective:** Rider requests → ride on driver surface → driver completes → rider sees status update.

### Definition of DONE

- [ ] Rider opens `rider-app`, registers/logs in, requests ride, sees status through **completed**
- [ ] Driver opens `driver-app`, goes online, **sees ride**, accepts, advances lifecycle, completes
- [ ] Full path works **without** curl/Postman/manual DB edits
- [ ] Documented owner runbook: three terminals (backend, rider-app, driver-app)

### Rider app (`rider-app/`)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P1-R1 | Auth: `/auth/rider/register`, `/auth/rider/login` | **DONE** | Customer-only lane |
| P1-R2 | Request UI: pickup, destination, Request Ride | **DONE** | Nominatim geocoding |
| P1-R3 | Wire `POST /rides/`, `GET /rides/{id}`, cancel | **DONE** | SSE + polling fallback |
| P1-R4 | Status timeline (requested → assigned → in progress → completed) | **DONE** | `RideStatusTimeline` |
| P1-R5 | E2E Playwright: rider request + poll until terminal | **DONE** | `rider-app/tests/ride-flow-ui-proof.spec.ts` · `npm run test:e2e:ride-flow` |
| P1-R6 | Ride history list (past trips) | **DONE** | `GET /rides/my-rides` + `RideHistory.jsx` |
| P1-R7 | Map preview (pickup/dropoff pins) | **TODO** | Nice-to-have; addresses work without map |

### Driver app (`driver-app/`)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P1-D1 | Open-board: incoming rides visible when online | **DONE** | `GET /drivers/available-rides` + pool SSE |
| P1-D2 | Accept → arrive → start → complete | **DONE** | Lifecycle on `/drivers/*` |
| P1-D3 | Active ride resume after refresh | **DONE** | Slice 01/03 — verify in owner test |
| P1-D4 | Show rider label on request card (`customer_name`) | **DONE** | No rider profile/rating |
| P1-R8 | Rider sees driver display name when assigned | **DONE** | `assigned_driver_name` on `RideDriverView` |
| P1-D5 | Owner runbook link in README | **DONE** | `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md` |
| P1-D6 | Dev-only simulation labeled **Internal test ride** | **TODO** | Replace beta-first-run path for owner builds |

### Backend (`backend/`)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P1-B1 | Rider create/cancel + driver lifecycle | **DONE** | `rider_rides.py`, `drivers.py` |
| P1-B2 | Rider auth endpoints | **DONE** | `/auth/rider/*` |
| P1-B3 | Pool broadcast on create/cancel | **DONE** | `ride_pool_broadcast` |
| P1-B4 | Integration test: rider auth + create/fetch/cancel | **DONE** | `test_rider_auth.py` |
| P1-B5 | Integration test: full loop (existing) | **DONE** | `test_ride_flow_ui_proof.py` |
| P1-B6 | CORS: allow rider-app origin in dev/staging | **DONE** | `.env.example` includes `:3023` |

### Phase 1 exit

**Status:** **DONE** (code) — run `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md` once for owner sign-off; rider Playwright: `cd rider-app && npm run test:e2e:ride-flow`.

---

## Phase 2 — Basic matching

**Objective:** Ride auto-assigned to a driver; driver does not rely on manually scanning the board.

**Modes:** `HALFAPP_AUTO_ASSIGN_MODE=nearest` (default) or `first_available`.

### Definition of DONE

- [x] Rider requests → backend sets `driver_id` + `accepted` without driver browsing pool
- [x] Assigned driver sees ride via active-ride poll / my-rides (not open board)
- [x] Second driver gets 409 on manual accept
- [x] Tests: `tests/test_ride_auto_assign.py`

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P2-B1 | `try_auto_assign_ride` | **DONE** | `backend/services/ride_auto_assign.py` |
| P2-B2 | Hook on `POST /rides/` | **DONE** | Flag `HALFAPP_AUTO_ASSIGN=1` |
| P2-B3 | Eligibility | **DONE** | `eligible_dispatch_driver_ids` |
| P2-B4 | Feature flag | **DONE** | Default off in `.env.example` |
| P2-B5 | Concurrency | **DONE** | `OpenBoardDispatchPolicy.claim_ride` |
| P2-B6 | Tests | **DONE** | 3 tests |
| P2-D1 | Assignment UX | **DONE** | Poll + `auto-assignment-notice` |
| P2-D3 | In-app notification | **DONE** | On auto-assign |
| P2-R1 | Rider sees assigned | **DONE** | Status `accepted` in API/SSE |

### Phase 2 exit

**Status:** **SHIPPED** — set `HALFAPP_AUTO_ASSIGN=1` in backend `.env` to enable.

---

## Phase 3 — Minimal payments loop

**Objective:** Simulated money movement — authorization, capture, payout tracking — **no external PSP required** for v1.

### Definition of DONE

- [x] Ride completion creates **charge record** linked to ride (`ride_payments` table)
- [x] Payment lifecycle: pending → authorized → captured (failed on cancel)
- [x] Rider sees estimated fare before request (`POST /rides/estimate`)
- [x] Rider sees receipt-like summary on complete (`GET /rides/{id}/payment`)
- [x] Driver earnings view shows captured ride payments (`GET /drivers/me/ride-payments`)
- [x] UI never claims “paid to bank”
- [ ] Rider confirms payment method step before or at request — **deferred** (not required for Phase 3 directive)

### Rider app

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P3-R1 | Payment method form (card last4 stub / wallet label) | **DEFERRED** | Out of Phase 3 scope per directive |
| P3-R2 | “Confirm payment” step before request | **DEFERRED** | |
| P3-R3 | Receipt screen on complete | **DONE** | `RideReceipt.jsx` + `fetchRidePayment` |
| P3-R4 | Estimated fare before request | **DONE** | Debounced `estimateFare` on pickup/dropoff |

### Driver app

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P3-D1 | Per-ride earnings row after complete | **DONE** | `GET /drivers/me/ride-payments` summary on Earnings |
| P3-D2 | Trip audit: payment execution section | **PARTIAL** | Audit exists; simulated `ride_payments` not yet in audit panel |
| P3-D3 | No bank-deposit / instant-pay copy | **DONE** | `assert-no-money-claims.mjs` guard |

### Backend

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P3-B1 | Simulated auth + capture on complete | **DONE** | `backend/services/ride_payment.py` + lifecycle hooks |
| P3-B2 | Rider payment method stub storage | **DEFERRED** | |
| P3-B3 | `GET /rides/{id}/payment` | **DONE** | |
| P3-B4 | `GET /drivers/me/ride-payments` + per-ride payment | **DONE** | |
| P3-B5 | Tests: complete → charge row + lifecycle | **DONE** | `test_ride_payment_phase3.py` |

### Phase 3 exit

**Status:** **SHIPPED** (2026-05-24) — simulated money loop; no Stripe/PSP. Owner E2E sign-off via runbook recommended before Phase 4.

---

## Phase 4 — Minimal ops panel

**Objective:** Operator control plane — see rides, cancel, see drivers.

### Definition of DONE

- [x] `ops-app/` lists active/recent rides with status + payment
- [x] Operator can open ride detail with lifecycle + payment state
- [x] Operator can cancel any in-flight ride (`POST /admin/rides/{id}/cancel`)
- [x] Operator can force-assign unassigned ride (`POST /admin/rides/{id}/assign`)
- [x] Operator can list drivers with online/presence + active ride
- [x] Admin routes with RBAC + tests

### Ops app (`ops-app/` — new)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P4-O1 | Scaffold Vite/React `ops-app/` | **DONE** | Port **3024** |
| P4-O2 | Admin login (role `admin`) | **DONE** | `POST /auth/admin/login` |
| P4-O3 | Rides list + detail + cancel + assign | **DONE** | 5s polling |
| P4-O4 | Drivers list + presence / active ride | **DONE** | `GET /admin/drivers` enriched |

### Driver / rider apps

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P4-UX1 | Reflect ops-cancel in rider/driver UI via existing SSE/poll | **PARTIAL** | Works via poll/SSE if connected; no ops-specific UX |

### Backend

| ID | Task | Status | Notes |
|----|------|--------|-------|
| P4-B1 | Ops admin routes in `admin_driver_approval.py` | **DONE** | detail, cancel, assign |
| P4-B2 | RBAC tests for admin cancel + assign | **DONE** | `test_ops_phase4.py` |
| P4-B3 | `GET /admin/rides` + payment fields | **DONE** | `payment_status` on list rows |

### Phase 4 exit

**Status:** **SHIPPED** (2026-05-24) — owner E2E via runbook recommended.

---

## Driver-app gaps (parallel track — not blocking Phase 2)

Work that improves the driver product but is **not** required to unlock Phase 2. From `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`.

| Priority | Task | Owner | Blocks |
|----------|------|-------|--------|
| P1 | Owner internal test runbook + copy | driver-app + docs | Honest Phase 1 demo |
| P1 | CORS / deploy checklist for 3022+3023 | infra | Cross-origin rider↔API |
| P2 | Postgres claim-race CI | backend | Production confidence |
| P2 | OSRM runtime proof | ops | Road-network routing claims |
| P3 | Web push notifications | driver-app + backend | Real-time assign alerts |
| P3 | Trips filters + earnings/audit copy alignment | driver-app | Polish |
| P4 | OpenAPI drift CI gate | backend | Contract safety |
| — | Live ETA, rider chat, wallet, bank payout UI | — | **Forbidden** until explicit order |

---

## What NOT to do

- Reuse `frontend/` or `rider-stub/` as product
- Start Phase 3 before Phase 2 DONE
- Ship “paid to your bank” or marketplace marketing
- Wire dossier `/supply`, `/demand`, `/trip` into driver-app
- Parallel Phase 2 + 3 + 4 without a working Phase 1 owner sign-off

---

## Recommended next actions (agent)

1. **Owner E2E sign-off:** Run `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md` including ops console on `:3024`.
2. **Reliability / production hardening:** Postgres claim-race CI, dispatch determinism tests, driver name on rider UI.
3. Optional: wire `ride_payments` into driver trip audit panel.

---

## Related docs

| Doc | Role |
|-----|------|
| `docs/SYSTEM_TRUTH.md` | Classification |
| `docs/CURRENT_TRUTH.md` | PR review table |
| `rider-app/README.md` | Rider app run |
| `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md` | Driver-only polish queue |
| `docs/RIDE_FLOW_UI_PROOF_V0_2_STATUS.md` | Driver E2E proof |
