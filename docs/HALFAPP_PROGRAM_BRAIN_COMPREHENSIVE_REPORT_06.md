# HalfApp Driver — Program, System, and Brain: Comprehensive Expert Report (Report 06)

**Document ID:** `HALFAPP_PROGRAM_BRAIN_COMPREHENSIVE_REPORT_06`  
**Date:** 2026-05-25 (**NEW UPDATE — supersedes Report 05 for big-picture and next-phase decisions**)  
**Audience:** Program owner, senior engineers, external experts, investors with technical depth  
**Repository:** `halfapp-driver` (private)  
**Supersedes for big-picture:** `HALFAPP_PROGRAM_BRAIN_COMPREHENSIVE_REPORT_05.md` (2026-05-25) — use **this file** first.

**Live verification on this pass (run before you cite numbers in decks):**

```powershell
cd backend
py -3.11 -m pytest -q --tb=no
# Observed 2026-05-25 after backend drift closure: 383 passed, 9 skipped (177.35s, SQLite dev)
```

**Companion docs (operational — not duplicated in full):**

| Doc | Role |
|-----|------|
| `docs/SYSTEM_TRUTH.md` | Authoritative gap classification |
| `docs/CURRENT_TRUTH.md` | Short PR-review truth table + P0 gate matrix |
| `docs/HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md` | Phases 1–4 build order + DONE status |
| `docs/HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md` | Agent execution: P0 → P1 → P2 |
| `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md` | Owner delivery-loop E2E |
| `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md` | Closed lanes + historical execution order |
| `docs/PRODUCT_BOUNDARY_STAGE0.md` | Forbidden claims |
| `docs/BACKLOG.md` | Ticket classification |

---

# Part 0 — Read this first: product identity and the “next step” frame

## 0.1 What this repository actually is (2026-05-25)

**HalfApp is a delivery-style driver execution platform** with a growing but still thin two-sided loop:

| Layer | Plain English |
|-------|----------------|
| **Supply** | Courier goes online in `driver-app`, sees jobs (pickup + dropoff), claims or receives assignment, executes lifecycle, sees earnings/audit |
| **Demand** | Customer/requester uses `rider-app` to post a job, track status, see estimate and receipt |
| **Control** | Operator uses `ops-app` to list jobs, cancel, force-assign, view drivers |
| **Authority** | FastAPI `backend/` owns state, money **calculation records**, dispatch winner, audit |

The repo name and most identifiers still say **ride**, **rider**, **marketplace**. That is **legacy vocabulary**. The honest product class is closer to **“auditable courier job execution + minimal requester loop”** than to Lyft, DoorDash, or Uber Eats.

**One-line classification for experts:**

> **Backend-authoritative delivery-driver cockpit** (map-first job execution) with shipped requester and ops surfaces, simulated payment lifecycle, rule-based area intelligence, and optional advisory AI — **not** a production-scale last-mile logistics OS.

## 0.2 What changed since Report 05 (delta you must internalize)

Report 05 was written the same day as this report; the **working tree** and **governance pass** nonetheless advanced several lanes. Treat this subsection as the **fresh big picture**:

| Area | Report 05 state | Report 06 / workspace state |
|------|-----------------|------------------------------|
| Alembic head | Cited `0032_ride_payments` | **Head `0035_telemetry_retention_index`** — chain `0032` → `0034_sil_crl_snapshots` → `0035` |
| Area intelligence ops | “SIL/CRL on-read compute” risk | **Background worker** optional: `HALFAPP_SIL_CRL_WORKER_ENABLED` → `jobs/sil_crl_worker.py` (60s SIL / 5m CRL) |
| Telemetry | “Unbounded growth” risk | **Retention index** migration `0035` + `jobs/telemetry_retention.py` + tests |
| P0 infrastructure | Described | **`docker-compose.yml`** ships Postgres 16 + OSRM container definitions for local G1/G2 |
| Postgres / Alembic proof | PARTIAL | CI-oriented tests: `test_postgres_claim_race_proof_01.py`, `test_alembic_postgres_upgrade_head.py` |
| Ride AI | Advisory, demo tier | **Route grounding** (`ride_route_grounding.py`, `ride_ai_dispatch_route_context.py`), payment gate tests, Playwright proof config |
| Stable car / owner verify | Mentioned | **`scripts/owner_runbook_verify.py`**, `test_stable_car_p0_01.py` |
| Backend pytest | “350+” from prior gate doc | **Live run after drift closure: 383 passed, 9 skipped** — see `BACKEND_PYTEST_DRIFT_CLOSURE_01.md` |
| SYSTEM_TRUTH | Noted lag vs checklist | **Reconciled 2026-05-25** — rider-app + ops-app now **SHIPPED** in authoritative doc |
| P0 gates G1–G7 | Listed | **Overall PARTIAL_GO** per `CURRENT_TRUTH.md` — owner runtime still pending |

**Strategic implication for “next step”:** You are past **“build the two-sided demo.”** You are at **“prove staging + close honesty gaps + pick one delivery fork.”** Do not add surface area until G1–G3 are closed or explicitly waived with written risk acceptance.

## 0.3 Terminology map (code ↔ delivery language)

| In codebase | Delivery meaning | Notes |
|-------------|------------------|-------|
| `Ride` / `ride_id` | **Delivery job** | Single pickup → single dropoff |
| `rider` / `rider-app` | **Customer / requester** | Not passenger-hailing product |
| `driver` / `driver-app` | **Courier** | Only mature supply-side UX |
| `requested` | Job posted, awaiting courier | |
| `accepted` | Assigned / claimed | |
| `driver_arrived` | At **pickup** | `arrive-pickup` |
| `in_progress` | **En route to dropoff** | `start-ride` |
| `completed` | **Delivered** | Pricing lock + simulated capture |
| `ride_pricing` | **Fare calculation record** | Integer cents — not bank money |
| `ride_payments` | **Simulated charge lifecycle** | pending → authorized → captured |
| Open board | Courier **chooses** visible jobs | Default story |
| `HALFAPP_AUTO_ASSIGN=1` | Auto-dispatch nearest/first online | Phase 2 — flag-gated |
| SIL / CRL | **Area busy/slow + “why” overlays** | H3 cells — not order-level ML |

## 0.4 Four-surface marketplace model (required vs built)

| Surface | Role in full delivery marketplace | Status (2026-05-25) |
|---------|-----------------------------------|---------------------|
| **Requester** | Place order, track, pay, receipt | **`rider-app/` SHIPPED** — no merchant SKU, no real checkout |
| **Courier** | Execute jobs on map | **`driver-app/` Real, partial** — cockpit, lifecycle, earnings, Ride AI advisory |
| **Money loop UX** | Pay, tip, payout visibility | **Partial** — ledger + simulated `ride_payments`; Stripe behind flags |
| **Ops** | Support, cancel, assign, monitor | **`ops-app/` SHIPPED minimal** — list/cancel/assign/drivers |

**Verdict:** Demonstrable **requester → courier → complete → receipt → ops** in dev; **not** production-hardened marketplace.

## 0.5 Comparison table (manage expert expectations)

| Dimension | DoorDash / Uber Eats class | Lyft passenger class | **HalfApp today** |
|-----------|----------------------------|----------------------|-------------------|
| Job unit | Order + merchant + items | Trip + passenger | **Pickup/dropoff job only** |
| Dispatch | Auto, batching, zones | Nearest driver ETA product | **Open board** or **optional auto-assign** |
| Proof of delivery | Photo, PIN, signature | N/A | **Not implemented** |
| Payments | Capture, tips, payouts | Same | **Simulated + schema for Stripe** |
| Routing | Road network + traffic products | Same | OSRM **code GO**, runtime **NO_GO** default |
| Ops | Refunds, merchants, SLAs | Fleet ops | **Minimal ops-app** |
| Intelligence | ML demand, ETAs | Surge, matching ML | **Rule-based SIL/CRL** + optional **advisory LLM** |

---

# Part I — Executive summary

## 1.1 Paragraph verdict

HalfApp has crossed a meaningful threshold: it is no longer only a driver-only MVP with API stubs. It is a **four-app monorepo** (`backend`, `driver-app`, `rider-app`, `ops-app`) sharing one lifecycle and pricing spine, with hundreds of automated tests and explicit **forbidden-claim** guards. The **governance brain** (docs + CI scripts + closed P0 lanes) is as architecturally important as dispatch code — without it, the repo’s breadth (Stripe tables, dossier spine, SIL/CRL, payment phases) would read as “finished marketplace.”

**Strengths:** backend authority, atomic claim lock, structured 409 transparency, integer-cent pricing honesty, two-sided loop shipped in code, growing proof culture (Playwright, acceptance reports, owner runbook).

**Weaknesses:** staging proofs incomplete (PostgreSQL claim-race on your machine, OSRM runtime, owner courier day), no push notifications, no proof-of-delivery, ride vocabulary confusion, advisory AI not production-tier.

## 1.2 What “the brain” means in this program (full taxonomy)

The word **brain** is overloaded. In HalfApp it means **seven distinct layers** — only one is ML:

| # | Brain layer | Function | Primary location | Mutates jobs? |
|---|-------------|----------|------------------|---------------|
| 1 | **Governance brain** | Truth boundaries, execution order, forbidden claims, phased acceptance | `docs/HALFAPP_*`, `CURRENT_TRUTH.md`, `PRODUCT_BOUNDARY_STAGE0.md`, `HALFAPP_AGENT_ACTION_DIRECTIVES.md` | No |
| 2 | **Dispatch brain** | Who gets the job: open board claim, cascade, auto-assign | `dispatch.py`, `ride_auto_assign.py`, `claim_eligibility.py`, `ride_dispatch_cascade.py` | **Yes** (assignment) |
| 3 | **Lifecycle brain** | Legal state transitions for execution | `lifecycle.py`, `RIDE_LIFECYCLE_CONTRACT.md` | **Yes** (status) |
| 4 | **Pricing brain** | Integer-cent quote/complete, financial lock | `ride_pricing.py`, `pricing_service.py` | **Yes** (pricing rows) |
| 5 | **Routing brain** | OSRM attempt + honest haversine fallback | `routing_service.py`, `ride_route_grounding.py`, `map_route_foundation.py` | Metadata only |
| 6 | **Area intelligence brain** | SIL busy/slow + CRL “why slow” | `sil_compute.py`, `crl_compute.py`, workers, map endpoints | No (overlays) |
| 7 | **Advisory AI brain** | Hints for courier — stream via engineering assistant | `useRideAiDispatch.js`, `rideAiDispatch/*`, `RideAiDispatchPanel.jsx` | **Never** |

**Explicitly not brains (common confusion):**

| System | Why it is not the product brain |
|--------|----------------------------------|
| `video-gate/` | Video QA tooling — isolated |
| `frontend/` | Archived multi-role UI |
| Dossier `/supply`, `/demand`, `/trip` | Parallel marketplace experiment — **not** wired to driver-app |
| Stripe modules | Execution infrastructure behind flags — not marketed wallet |
| Leaflet map | Presentation — route truth is backend metadata |

## 1.3 Strategic posture (fixed until rescope)

| Decision | Choice |
|----------|--------|
| Job model | Single pickup, single dropoff |
| Dispatch default | **Open board** — courier picks job |
| Auto-assign | Optional `HALFAPP_AUTO_ASSIGN=1` |
| Payments in two-sided loop | **Simulated** `ride_payments` for Phase 3; real PSP optional behind flags |
| Routing honesty | Fallback labeled; no fake OSRM claims |
| Active paths | `backend/`, `driver-app/`, `rider-app/`, `ops-app/` |
| Dossier | **Path A recommended** (keep parallel, do not wire to driver-app) per `DOSSIER_PATH_DECISION_01.md` |

## 1.4 Measured health (verify locally — do not trust stale counts)

| Gate | Status (2026-05-25) | Notes |
|------|---------------------|-------|
| Backend pytest (full) | **383 passed, 9 skipped** | SQLite dev gate green after drift closure; see `BACKEND_PYTEST_DRIFT_CLOSURE_01.md` |
| Prior gate doc | 345 passed (2026-05-24) | `BACKEND_TEST_GATE_PROOF_V0_1.md` — superseded by live run |
| Alembic head | **`0035_telemetry_retention_index`** | 35 revisions `0001`–`0035` |
| Driver ride-flow E2E | **GO** | `RIDE_FLOW_UI_PROOF_V0_2_STATUS.md` |
| Rider ride-flow E2E | **GO** | `rider-app` Playwright |
| Ride AI dispatch UI | **GO_DEMO_SAFE** | Not production GO — see production proof gates report |
| OSRM runtime | **NO_GO** | Until `scripts/prove_osrm_runtime.py` exit 0 on prepared extract |
| P0 overall | **PARTIAL_GO** | G1 PG local, G2 OSRM, G3 owner day, G7 PG proof pending |
| Two-sided Phases 1–4 | **SHIPPED (code)** | Owner sign-off via runbook recommended |

## 1.5 Recommended next phase (90-day delivery focus)

**Phase A — Proof (non-negotiable before feature forks)**

1. Keep backend pytest green (`383 passed, 9 skipped` on the 2026-05-25 SQLite dev run).  
2. G1: `docker compose up -d postgres` + claim-race green on PostgreSQL.  
3. G2: OSRM runtime proof on Portland extract.  
4. G3: Owner completes `OWNER_INTERNAL_TEST_RUNBOOK_01.md` once — fill `OWNER_COURIER_DAY_REPORT_01.md`.  
5. G5/G6: Keep surface-freeze + SYSTEM_TRUTH aligned when routes change.

**Phase B — Courier-complete (after P0 GO)**

1. Push notification design + assign alerts (P1.1).  
2. Session recovery hardening mid-job (P1.2).  
3. Delivery vocabulary UI pass (reduce “ride-hailing” copy).  
4. Enable `HALFAPP_SIL_CRL_WORKER_ENABLED` in staging; verify `SIL_CRL_WORKER_PROOF_01.md`.

**Phase C — One fork only (pick one)**

- Proof-of-delivery (photo/PIN) **OR**  
- Merchant/order payload on job **OR**  
- Real Stripe pilot with unchanged UI guards **OR**  
- External trusted-courier beta (explicitly deferred in roadmap)

---

# Part II — Architecture: end-to-end delivery job platform

## 2.1 Happy-path sequence (demonstrable today)

```mermaid
sequenceDiagram
  participant R as Requester (rider-app :3023)
  participant API as Backend (:8000)
  participant C as Courier (driver-app :3022)
  participant O as Ops (ops-app :3024)

  R->>API: POST /rides/ (pickup, dropoff coords)
  API->>API: Job requested + ride_pricing quote
  alt HALFAPP_AUTO_ASSIGN=1
    API->>API: ride_auto_assign → accepted + driver_id
  else Open board
    API->>C: Pool SSE / GET available-rides
    C->>API: POST accept-ride (atomic claim)
  end
  C->>API: arrive-pickup → start-ride → complete-ride
  API->>API: financial_locked + ride_payments captured
  R->>API: GET status / payment (receipt)
  O->>API: Optional cancel / assign (admin)
```

**Missing from real delivery ops:** merchant prep signal, ready-for-pickup, POD, refund desk, SLA per merchant, live courier map for customer, push to device.

## 2.2 Repository topology

```
halfapp-driver/
├── backend/                 # FastAPI — authority for all four apps
│   ├── alembic/versions/    # 0001–0035 schema evolution
│   ├── routes/              # auth, drivers, rider_rides, admin, sil, crl, payments*
│   ├── services/            # 78 service modules (dispatch, lifecycle, pricing, routing, SIL, CRL, …)
│   ├── jobs/                # sil_crl_worker, telemetry_retention (background)
│   ├── models/              # explicit ORM registration in main.py
│   └── tests/               # 82 test modules
├── driver-app/              # Courier cockpit (port 3022)
├── rider-app/               # Requester (port 3023)
├── ops-app/                 # Operator panel (port 3024)
├── docs/                    # Governance brain — 100+ markdown files
├── frontend/                # ARCHIVE — not production
├── rider-stub/              # DEMO API smoke only
├── video-gate/              # Isolated video tooling
├── docker/osrm-portland/    # OSRM extract prep
├── docker-compose.yml       # postgres + osrm for P0
└── scripts/                 # prove_osrm_runtime, owner_runbook_verify, print_active_routes
```

## 2.3 Active entry points (non-negotiable boundary)

| App | Entry | API boundary |
|-----|-------|--------------|
| Backend | `backend/main.py` | Routers registered in main — see §4.2 |
| Courier | `driver-app/src/App.jsx` | **`/drivers/*` + `/auth/*` only** in `api.js` |
| Requester | `rider-app/src/App.jsx` | `/auth/rider/*`, `/rides/*` |
| Ops | `ops-app/src/App.jsx` | `/auth/admin/*`, `/admin/rides`, `/admin/drivers` |

**Review rule:** Code not reachable from these entry points is **not** current product behavior unless a PR registers, tests, and documents it.

## 2.4 Inactive surfaces (expert hazard list)

| Surface | Classification | Risk if misread |
|---------|----------------|-----------------|
| `frontend/` | ARCHIVE | Looks like full marketplace UI |
| `rider-stub/` | DEMO ONLY | Mistaken for rider product |
| Dossier spine | PARALLEL_NOT_WIRED | `/supply`, `/demand`, `/trip` — flag `HALFAPP_DOSSIER_SPINE_ENABLED` |
| Dormant routers | Unmounted | `routes/admin.py` (legacy), `routes/rides.py`, etc. |
| Stripe stack | Schema + flags | “Flip switch = DoorDash payments” |
| Engineering Intelligence | LOCAL_CONTEXT_ONLY | Dev shell — not dispatch |
| `video-gate/` | Unrelated | “AI video brain” narrative |

---

# Part III — The brain in depth

## 3.1 Governance brain — the meta-system

HalfApp’s most unusual asset for an MVP-stage repo is **truth discipline as code + docs**.

### Mechanisms

| Mechanism | What it enforces |
|-----------|------------------|
| `PRODUCT_BOUNDARY_STAGE0.md` | Forbidden marketing and UI claims |
| `CURRENT_TRUTH.md` | PR review table — GO/NO_GO per area |
| `SYSTEM_TRUTH.md` | Authoritative “what we are / are not” |
| `HALFAPP_AGENT_ACTION_DIRECTIVES.md` | Closed lanes: AUTH-001, RIDE-001/002/003, DRIVER-002, … |
| `HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md` | P0→P1→P2 ordered tasks for agents |
| `HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md` | Phase 1–4 definitions of DONE |
| CI: `assert-no-money-claims.mjs` | Blocks bank payout language in driver UI |
| CI: `assert-no-ai-providers.mjs` | Blocks direct OpenAI keys in driver src |
| CI: `assert-prod-truth.mjs` | Blocks mock/guard bypass in production builds |
| Acceptance `*_REPORT.md` | Versioned proof artifacts per lane |

### Strengths

- Prevents demo deck language from outrunning courier-facing truth.  
- Makes “closed lane” explicit — reduces accidental rewrite of claim lock every sprint.  
- Gives external experts a **reading order** instead of raw repo spelunking.

### Weaknesses

- **~100+ markdown files** — high navigation cost; contradictions require reconciliation passes (`HALFAPP_TRUTH_SYNC_*`, P0 G6).  
- Some older docs still say “no rider product” — **trust SYSTEM_TRUTH + this report + checklist** for 2026-05-25.  
- Stage 0 header still says “not a two-sided marketplace” while Phases 1–4 shipped — semantic tension; Stage 0 means **not production marketplace**, not “no rider app.”

## 3.2 Dispatch brain — how jobs get to couriers

### Mode A: Open board (default product story)

1. Jobs sit in `requested` with no `driver_id`.  
2. Visible via `GET /drivers/available-rides` and ride pool SSE (`ride_pool_broadcast`).  
3. `POST /drivers/accept-ride/{ride_id}` uses row lock + conditional UPDATE.  
4. Losers receive **409** with transparency payload (`ClaimConflictNotice` in UI).

**Delivery fit:** Courier pool / “grab next job.”  
**Gap:** No SLA-based ranking in product UI, no distance-to-pickup sort as shipped UX guarantee.

### Mode B: Sequential cascade (RIDE-003)

- Enabled when `HALFAPP_OPEN_BOARD_DISPATCH=0`.  
- 30s timeout, 3 attempts, exhaustion → `cancelled` + `lifecycle_reason=no_drivers_available`.  
- `ride_dispatch_log` records sent/accepted/declined/timeout/skipped_ineligible.

**Delivery fit:** Dispatcher-style sequential offers — still single courier, not batching.

### Mode C: Auto-assign (Phase 2)

- `HALFAPP_AUTO_ASSIGN=1` on `POST /rides/`.  
- `ride_auto_assign.py`: `nearest` or `first_available` via `eligible_dispatch_driver_ids`.  
- Second courier manual accept → 409.

**Delivery fit:** Closer to assigned courier model — still one job, no merchant queue.

### What dispatch brain refuses

- LLM-chosen assignment.  
- Multi-stop route optimization.  
- Batching multiple orders per courier.  
- Frontend-side “I claimed it” without server winner.

## 3.3 Lifecycle brain — execution truth

**Canonical path:**

`requested → accepted → driver_arrived → in_progress → completed`

**Terminals:** `cancelled` (rider), decline release `accepted → requested` (not terminal rejection).

**Implementation:** `lifecycle.py` + structured `invalid_state_transition` 409s (RIDE-001 **closed lane**).

**Maps to delivery:** assigned → at pickup → delivering → delivered.

**Recent test drift note:** Two tests failed on `completed → cancelled` rejection — indicates either contract tightening or test/implementation mismatch; **resolve before claiming lifecycle gate frozen**.

## 3.4 Pricing brain — calculation, not settlement

| Concept | Implementation |
|---------|----------------|
| Storage | `ride_pricing` — all money in **integer cents** |
| Quote | Created at request/estimate flows |
| Complete | `financial_locked` on terminal complete |
| Display | `ridePricingDisplay.js` — separates driver shareable vs customer total |
| Settlement rows | `settlement_entries` — obligation boundary, not payout execution |

**Forbidden:** UI claiming “paid to your bank” — guarded by scripts and `BETA_*` copy keys.

## 3.5 Payments brain — three layers (experts must separate)

| Layer | Table / module | Product claim |
|-------|----------------|---------------|
| **Pricing ledger** | `ride_pricing` | Fare breakdown — **GO** |
| **Simulated loop** | `ride_payments` (0032) | pending → authorized → captured — **GO** in two-sided checklist |
| **Stripe execution** | `payment_execution`, webhooks, Connect | **PARTIAL** — behind `PAYMENTS_ENABLED` / `PAYOUTS_ENABLED` |

Phases 1–5 documented in `HALFAPP_PAYMENTS_EXECUTION_05_GO.md` — driver reconciliation visibility without deposit product claims.

## 3.6 Routing brain — honesty over fantasy maps

| Component | Role |
|-----------|------|
| `routing_service.py` | Provider selection |
| `osrm_self_hosted_provider.py` | HTTP to OSRM |
| Fallback | `haversine_fallback` when OSRM down + `ROUTING_FALLBACK_ENABLED` |
| `ride_route_grounding.py` | Advisory distance/duration for Ride AI |
| `route_snapshots` | Foundation table — quote/complete proof rows |
| `osrm_runtime_truth.py` | Runtime verdict helpers |

**Code path:** GO (mocked HTTP tests).  
**Runtime:** NO_GO until Portland OSRM up and proof script passes.

**Courier UX:** Leaflet + OSM in-app; **Google Maps external** for turn-by-turn — no embedded Maps API key on active path.

## 3.7 Area intelligence brain (SIL + CRL)

### SIL (Street Intelligence Layer)

- H3 cell aggregates: demand (open jobs) + supply (online drivers) + telemetry speeds.  
- Endpoints under `/sil/*` for map overlays.  
- Migration `0030_sil_foundation`.

### CRL (City Reality Layer)

- Rule-based “why is this area slow” — commute windows, events, demand imbalance.  
- `crl_attribution.py`, `crl_labels.py`, admin event injection.  
- Migration `0031_crl_foundation`, `0034_sil_crl_snapshots`.

### Operations upgrade (new since early v0.1)

- **`HALFAPP_SIL_CRL_WORKER_ENABLED`**: background recompute every 60s (SIL) / 5m (CRL).  
- Reduces reliance on on-read compute at scale.  
- Proof: `docs/SIL_CRL_WORKER_PROOF_01.md`, `tests/test_sil_crl_worker.py`.

### Fleet telemetry

- `driver_telemetry_point` — GPS samples from courier app.  
- `fleet_traffic_heatmap.py` — heatmap from own data, not commercial traffic APIs.  
- **`0035_telemetry_retention_index`** + retention job — addresses unbounded growth concern from Report 05.

### Limits

- Not order-level ETA to customer door.  
- Cold start: empty H3 at launch.  
- CRL rules miss unlisted causes (construction, weather without data).

## 3.8 Advisory AI brain (Ride AI dispatch)

**Purpose:** Stream hints to courier during match/route/decline/complete — **never** mutates backend.

| Property | Detail |
|----------|--------|
| Hook | `useRideAiDispatch.js` |
| Services | `driver-app/src/services/rideAiDispatch/*` — prompts, PII sanitizer, rate limiter, route context |
| UI | `RideAiDispatchPanel.jsx` in `MarketplaceBottomSheet` |
| Proxy | `engineering-assistant` routes — `ENGINEERING_ASSISTANT_ENABLED` + server key |
| Payment gate | `fetchRidePayment` — ledger-backed trip record when available |
| Tests | `test_ride_ai_dispatch_payment_gate.py`, `test_ride_ai_dispatch_route_context.py`, Playwright `ride-ai-dispatch-ui-proof.spec.ts` |
| Tier | **GO_DEMO_SAFE** — production tier requires OSRM runtime + quota proof |

**Explicit contract (from hook docstring):** “Advisory ride AI dispatch loop — never mutates backend dispatch.”

## 3.9 Transparency brain (anti-black-box UX)

| Pillar | Delivery meaning | Status |
|--------|------------------|--------|
| Dispatch transparency | Why courier saw/lost job | **GO** — 409 proof, `ConflictTransparencyMemory.jsx` |
| Financial transparency | Cents breakdown | **GO** — `ride_pricing` |
| Route transparency | Which engine used | **Partial** — honest labels; OSRM runtime NO_GO |
| Audit transparency | Trip list + CSV + audit endpoint | **GO** |
| Presence transparency | online/stale/busy | **GO** |

---

# Part IV — Backend platform reference

## 4.1 Stack and boot

- **FastAPI** + **SQLAlchemy** + **Alembic**  
- JWT auth + refresh rotation (`0016_refresh_tokens_foundation`)  
- `run_migrations(engine)` at import in `main.py`  
- **30+ model modules** explicitly imported before route registration  
- Production `SECRET_KEY` guard at boot (`production_guards.py`)  
- Auth rate limit middleware  
- Event bus loop wired at startup for SSE broadcast

## 4.2 Mounted routers (product-relevant)

| Router | Prefix | Role |
|--------|--------|------|
| `auth` | `/auth` | Driver, rider, admin registration/login |
| `drivers` | `/drivers` | **Courier surface** (~40 endpoints) |
| `rider_rides` | `/rides` | Requester create, cancel, estimate, payment GET, SSE |
| `notifications` | `/notifications` | In-app notifications |
| `admin_driver_approval` | `/admin/drivers`, `/admin/rides` | Approval + ops |
| `sil` / `crl` | map overlays | Area intelligence |
| `admin_crl` | admin CRL events | Ops tuning |
| `engineering_assistant` | optional | Anthropic proxy for Ride AI |
| `payments_*` | webhooks, Stripe | Flag-gated |
| `dossier_marketplace` | `/supply`, `/demand`, `/trip` | Only if `HALFAPP_DOSSIER_SPINE_ENABLED=1` |

Verify:

```powershell
py -3.11 scripts/print_active_routes.py
```

## 4.3 Courier API groups (`/drivers`)

| Group | Examples |
|-------|----------|
| Presence | `GET/PUT /presence`, `POST /heartbeat` |
| Pool | `GET /available-rides`, pool SSE |
| Claim | `POST /accept-ride/{id}`, `decline-ride`, `hide` |
| Execution | `arrive-pickup`, `start-ride`, `complete-ride` |
| Truth | `.../transparency`, `.../audit`, route snapshots read |
| Money views | `/earnings`, `/me/ride-payments`, payment reconciliation (flagged) |
| Telemetry | `POST /me/telemetry`, traffic heatmap |
| Recovery | active ride recovery endpoints |

## 4.4 Schema domains (Alembic 0001–0035)

| Domain | Key revisions | Maturity |
|--------|---------------|----------|
| Core job | 0001–0003, 0014–0015 | **GO** |
| Ledger events | 0005 | **GO** |
| Dossier parallel | 0006 | Foundation — not driver-app |
| Pricing / map v0.1 | 0007–0008, 0010 | **GO** / foundation |
| Settlement | 0011 | Obligation rows |
| Driver approval | 0012–0013 | **GO** |
| Payments execution | 0017–0023 | Flag-gated |
| Profiles / settings | 0024–0025 | Shipped |
| Idempotency | 0026 | Write replay protection |
| Messages / support | 0028 | Foundation |
| Telemetry | 0029, **0035 retention** | **GO** with retention |
| SIL / CRL | 0030–0031, **0034 snapshots** | **GO** + worker |
| Simulated payments | **0032** | Phase 3 **GO** |

## 4.5 Feature flags (operator cheat sheet)

| Variable | Effect |
|----------|--------|
| `HALFAPP_OPEN_BOARD_DISPATCH=1` | Open board (default story) |
| `HALFAPP_OPEN_BOARD_DISPATCH=0` | RIDE-003 cascade |
| `HALFAPP_AUTO_ASSIGN=1` | Auto-dispatch on create |
| `HALFAPP_AUTO_ASSIGN_MODE` | `nearest` \| `first_available` |
| `HALFAPP_SIL_CRL_WORKER_ENABLED` | Background SIL/CRL recompute |
| `ROUTING_FALLBACK_ENABLED` | Haversine when OSRM down |
| `PAYMENTS_ENABLED` / `PAYOUTS_ENABLED` | Stripe paths |
| `ENGINEERING_ASSISTANT_ENABLED` | Ride AI proxy |
| `HALFAPP_DOSSIER_SPINE_ENABLED` | Mount dossier routes |
| `DATABASE_URL` | PostgreSQL for concurrency proofs |

---

# Part V — Courier application (`driver-app`)

## 5.1 Stack

React 18 · Vite 7 · HashRouter · Leaflet + OpenStreetMap · Playwright E2E suites: ride-flow, ride-ai-dispatch, session-recovery, audit, route-truth.

## 5.2 Routes and screens

| Route | Component | Delivery function |
|-------|-----------|-------------------|
| `/driver` | `MapHome` | Online toggle, job sheet, map, nav links |
| `/trips` | Trip history + audit | Past deliveries, CSV export |
| `/earnings` | `Earnings.jsx` | Calculation records — not bank statement |
| `/notifications` | In-app inbox | No FCM/APNs |
| `/profile`, `/settings` | Account | Push prefs stored locally — not sent |

## 5.3 Cockpit composition

| Component | Role |
|-----------|------|
| `MarketplaceBottomSheet` | Incoming jobs, actions, Ride AI panel |
| `RideRequestCard` | Active job lifecycle buttons |
| `RideNavigationPanel` | External Google Maps |
| `RouteTruthDetails` | Provider + fallback honesty |
| `StreetIntelligencePanel` / `CityRealityPanel` | SIL/CRL overlays |
| `ClaimConflictNotice` | 409 transparency |
| `RideAiDispatchPanel` | Advisory AI |
| `ConflictTransparencyMemory` | Backend conflict proof display |

## 5.4 Frontend discipline (why experts should trust the UI)

- API boundary: **`/drivers/*` + `/auth/*` only** — dossier paths forbidden.  
- Production build rejects mock bypass and guard bypass env vars.  
- Simulation rides labeled when `VITE_ENABLE_RIDE_SIMULATION=true` — still create real DB rows.  
- Money and AI claims enforced in CI scripts.

## 5.5 Courier-specific gaps

| Gap | Impact |
|-----|--------|
| No push on new job | Must keep app foreground |
| No proof-of-delivery | Disputes / merchant trust |
| No multi-stop | One pickup, one dropoff |
| Background GPS | Web limitations — native fork later |
| Session recovery | Improved — verify on mid-job refresh (P1.2) |

---

# Part VI — Requester and ops surfaces

## 6.1 `rider-app` (customer / job requester)

**Shipped:**

- Auth: `/auth/rider/register`, `/auth/rider/login`  
- Request UI with Nominatim geocoding  
- `POST /rides/`, status timeline, SSE + poll fallback  
- Fare estimate: `POST /rides/estimate`  
- Receipt: `GET /rides/{id}/payment` on complete  
- History: `GET /rides/my-rides`  
- Playwright: `ride-flow-ui-proof.spec.ts`

**Not shipped:**

- Merchant menu / cart / scheduled window  
- Real payment method / checkout  
- Live courier map (status strings primarily)  
- Rider-side chat (driver messages exist in backend; rider client N/A)

## 6.2 `ops-app` (internal control plane)

**Shipped:**

- Admin auth  
- Rides list/detail, cancel, force-assign  
- Drivers list + presence + active job  
- Port **3024**  
- Tests: `test_ops_phase4.py`

**Not shipped:**

- Merchant onboarding, zones, refund desk, SLA dashboards

---

# Part VII — Two-sided execution status

Per `HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md`:

| Phase | Goal | Status |
|-------|------|--------|
| **1** | Requester → courier → complete without manual API | **DONE (code)** — owner runbook sign-off recommended |
| **2** | Auto-assign | **SHIPPED** — `HALFAPP_AUTO_ASSIGN=1` |
| **3** | Simulated money loop | **SHIPPED** — `ride_payments` |
| **4** | Minimal ops | **SHIPPED** — `ops-app` |

**This is the major architectural milestone since early 2026 reports** that listed “no rider product.” The loop is **demonstrable**; it is **not production-hardened**.

---

# Part VIII — Testing and proof culture

## 8.1 Backend test inventory (categories)

| Category | Example tests |
|----------|----------------|
| Claim concurrency | `test_ride_claim_lock_concurrency.py`, `test_postgres_claim_race_proof_01.py` |
| Lifecycle | `test_ride_001_transition_guards.py`, `test_ride_lifecycle.py` |
| Dispatch cascade | `test_ride_003_dispatch_cascade.py` |
| Auto-assign | `test_ride_auto_assign.py` |
| Pricing | `test_pricing_ledger_v01.py` |
| Simulated payments | `test_ride_payment_phase3.py` |
| Rider / ops | `test_rider_auth.py`, `test_ops_phase4.py` |
| SIL / CRL / worker | `test_sil_v01.py`, `test_crl_v01.py`, `test_sil_crl_worker.py` |
| Telemetry retention | `test_telemetry_retention.py` |
| Routing | `test_osrm_self_hosted_routing.py`, `test_routing_service_real_osrm.py` |
| Ride AI | `test_ride_ai_dispatch_payment_gate.py`, `test_ride_ai_dispatch_route_context.py` |
| Production guards | `test_production_guards.py` |
| Stable car P0 | `test_stable_car_p0_01.py` |
| Alembic PG | `test_alembic_postgres_upgrade_head.py` |
| Surface freeze | `test_active_route_surface.py`, `test_openapi_surface_does_not_drift.py` |

## 8.2 Current pytest gate

**Live 2026-05-25 run after drift closure:** 383 passed, 9 skipped.

| Former failing area | Closure |
|-------------|----------------|
| `test_openapi_surface_does_not_drift` | Snapshot updated for intentional `/rides/my-rides` path |
| `test_crl_v01::test_admin_create_event_and_overview` | Fixture now uses deterministic future end time |
| Completed ride cancellation rejection tests | Rider cancel imports existing structured 409 helpers |

**Rule:** Cite backend “all green” only with the command and date; rerun before decks.

## 8.3 Frontend E2E

| Suite | App | Status doc |
|-------|-----|------------|
| `test:e2e:ride-flow` | driver-app | `RIDE_FLOW_UI_PROOF_V0_2_STATUS.md` |
| `test:e2e:ride-flow` | rider-app | checklist Phase 1 |
| ride-ai-dispatch | driver-app | `RIDE_AI_DISPATCH_PRODUCTION_PROOF_GATES_01_REPORT.md` |

## 8.4 Proof culture strengths and costs

**Strengths:** Acceptance reports version truth like code; owner runbook; scripts `owner_runbook_verify.py`, `prove_osrm_runtime.py`.

**Costs:** Doc pass counts drift (254 → 345 → 379); experts must re-run commands; reconciliation orders (`HALFAPP_TRUTH_SYNC_*`) required periodically.

---

# Part IX — Strengths (detailed, evidence-backed)

## 9.1 Product and architecture

1. **Courier-first thesis** — map cockpit for execution, not admin-first dashboard.  
2. **Backend authority** — rare discipline; UI cannot silently invent dispatch winners.  
3. **Pickup → dropoff lifecycle** — maps to standard delivery run.  
4. **Atomic claim lock** — correct for contested pool jobs; concurrency tests exist.  
5. **Structured 409 transparency** — losing courier sees proof, not opaque failure.  
6. **Integer-cent pricing** — safe monetary display; financial lock on complete.  
7. **Honest routing fallback** — `haversine_fallback` labeled — critical for delivery distance honesty.  
8. **Two-sided loop shipped in code** — four apps, one spine.  
9. **Auto-assign optional** — can demo dispatcher-style without removing open board.  
10. **Simulated payments** — receipt + earnings without bank lies.  
11. **Ops minimal console** — cancel/assign for internal trials.  
12. **Session recovery API** — `test_active_ride_recovery.py`.  
13. **Stable car spine** — P0 owner verification script + tests.

## 9.2 Engineering process (“governance as engineering”)

14. **Stage 0 + SYSTEM_TRUTH** — explicit forbidden claims.  
15. **Closed P0 lanes** — dispatch/lifecycle/approval stable.  
16. **35 Alembic migrations** — schema evolution tracked.  
17. **Per-test DB isolation** — `conftest.py` wipe between tests.  
18. **E2E locks** — browser proof of courier and requester paths.  
19. **CI truth scripts** — money/AI/prod guards.  
20. **docker-compose for P0** — Postgres + OSRM path defined.  
21. **Owner runbook** — three-terminal delivery loop documented.

## 9.3 Intelligence (explainable, not black-box ML)

22. **SIL/CRL rule-based** — explainable area context for couriers.  
23. **Background worker option** — operational path for scale.  
24. **Telemetry retention** — addresses growth risk.  
25. **Ride AI advisory** — optional hints without dispatch mutation; PII sanitizer + rate limits.  
26. **Route grounding for AI** — ties hints to backend route context when available.

## 9.4 Extensibility (if you choose a fork)

27. **Dispatch policy abstraction** — zone-based assign conceivable.  
28. **Route snapshots** — proof of route at quote/complete.  
29. **Payment phases 1–5** — Stripe without UI lies.  
30. **Ride messages table** — courier ↔ customer chat foundation.  
31. **Idempotency replays** — safer mobile writes.

---

# Part X — Weaknesses and risks (detailed)

## 10.1 Production blockers (P0)

| Risk | Severity | Detail |
|------|----------|--------|
| PostgreSQL not default dev | **Critical** | Claim lock proven heavily on SQLite; G1 PARTIAL_GO |
| OSRM runtime NO_GO | **High** | Road distance for pricing may be haversine-labeled fallback |
| Owner courier day pending | **High** | G3 PENDING_OWNER — human sign-off |
| Backend pytest regression | **Medium** | Currently green on SQLite dev; rerun before release claims |
| No push notifications | **High** for delivery | Couriers miss assigns without foreground app |
| CORS/deploy partial | **Medium** | Multi-origin 3022–3024 matrix |

## 10.2 Architectural debt

| Debt | Consequence |
|------|-------------|
| **Ride vocabulary** | Experts assume passenger Uber; use §0.3 glossary in all new docs |
| **Dual marketplace spine** | `/drivers/*` vs dossier — onboarding hazard |
| **Schema breadth > product depth** | Decks overclaim vs Stage 0 |
| **Doc volume** | Navigation cost; needs reading order (this report) |
| **OpenAPI snapshot discipline** | Keep snapshot updated when routes intentionally change |
| **Single-drop job model** | No batching or route optimization |
| **WebSocket limited** | SSE pool exists; not device push |

## 10.3 Delivery product gaps (courier + requester expectations)

| Gap | User impact |
|-----|-------------|
| No proof of delivery | Disputes, merchant trust |
| No merchant / order line items | Cannot verify contents |
| No prep-ready / wait timer | Food SLA |
| No batching | Efficiency vs incumbents |
| No customer live courier map | Requester sees status strings |
| Geocoding not audit-proved | Wrong-building risk |
| Rider payment method step | Deferred in Phase 3 |
| Chat to requester incomplete | Driver-side storage only |

## 10.4 Intelligence limitations

| Limitation | Why it matters |
|------------|----------------|
| Cold-start H3 | Empty overlays at launch |
| Rule-based CRL | Misses unmodeled disruptions |
| Advisory AI not production GO | Do not market “AI dispatch” |
| LLM cost/quota | `ai_assistant_quota.py` — ops tuning needed |

## 10.5 Organizational / narrative risks

| Risk | Mitigation |
|------|------------|
| Repo size intimidates | Start: CURRENT_TRUTH → this file → checklist |
| “Almost DoorDash” pitch | Use §0.5 comparison table |
| Flip Stripe switch marketing | assert-no-money-claims + Stage 0 |
| Agents rewrite closed lanes | HALFAPP_AGENT_ACTION_DIRECTIVES closed list |

---

# Part XI — Inventory: exists / partial / does not exist

## 11.1 EXISTS (may claim with tests)

- [x] Courier JWT auth + refresh rotation  
- [x] Courier approval gate (DRIVER-002)  
- [x] Backend presence + heartbeat + stale/disconnected  
- [x] Open-board dispatch + atomic claim + 409 transparency  
- [x] Sequential dispatch cascade (flag)  
- [x] Auto-assign (flag)  
- [x] Lifecycle through completed (delivered)  
- [x] Hide/dismiss from pool  
- [x] Marketplace ledger events (append-only)  
- [x] `ride_pricing` integer cents + financial lock  
- [x] `ride_payments` simulated lifecycle  
- [x] Requester app: request, track, estimate, receipt, history  
- [x] Ops app: list, cancel, assign, drivers  
- [x] Trip audit + CSV export  
- [x] Earnings from completed jobs + ride payments summary  
- [x] In-app notifications (no push transport)  
- [x] Route provider metadata + route snapshots foundation  
- [x] OSRM code path (mocked tests)  
- [x] SIL/CRL + fleet heatmap + optional background worker  
- [x] Telemetry retention index + job  
- [x] Leaflet/OSM courier map  
- [x] Google Maps external navigation  
- [x] Ride AI advisory (demo tier) + route grounding tests  
- [x] Playwright E2E (driver, rider, ride-ai)  
- [x] Stripe code behind flags (phases 1–5)  
- [x] docker-compose postgres + osrm services  
- [x] Owner runbook + verify script  

## 11.2 PARTIAL (label honestly)

- [~] OSRM production routing (runtime proof)  
- [~] PostgreSQL claim-race on owner machine  
- [~] Alembic upgrade head on fresh PostgreSQL (G7)  
- [~] Full backend pytest green on SQLite dev — current GO; must be re-run before release claims  
- [~] Route snapshot read UI in cockpit  
- [~] CORS production matrix for all four origins  
- [~] Courier session resilience mid-job  
- [~] Real PSP product (flags + schema, not default loop)  
- [~] Ops changes reflected instantly on all clients (poll/SSE latency)  
- [~] Ride AI production tier  

## 11.3 DOES NOT EXIST (forbidden to claim)

- [ ] Full DoorDash / Uber Eats marketplace  
- [ ] Merchant portal, menus, inventory  
- [ ] Proof of delivery (photo / signature / PIN)  
- [ ] Multi-stop routes / batching  
- [ ] Production geocoding proof from address alone  
- [ ] Marketed live ETA guarantee to customer  
- [ ] Driver paid-to-bank product proof in default UX  
- [ ] Wallet / instant pay product  
- [ ] Push notification delivery to device  
- [ ] ML demand forecast or LLM job assignment  
- [ ] City-scale logistics OS  
- [ ] Commercial paid-traffic APIs as shipped product  
- [ ] External trusted-courier beta (deferred per policy)  
- [ ] In-process LLM changing dispatch/pricing/lifecycle  

---

# Part XII — Parallel systems confusion matrix

| System | vs delivery product | Recommended action |
|--------|---------------------|-------------------|
| `frontend/` | None — archive | Keep `frontend/README.md` visible |
| Dossier spine | Parallel experiment | **Path A:** keep off driver-app; document only |
| `video-gate/` | Unrelated | Exclude from delivery narrative |
| Stripe schema | Future execution | Demo with flags off + honest copy |
| “Ride” naming | Vocabulary debt | New docs use §0.3; code rename is large fork |
| Engineering Intelligence | Dev-only shell | Do not conflate with Ride AI |
| `rider-stub/` | Smoke demo | Never cite as rider product |

---

# Part XIII — P0 gate detail (what blocks “next step”)

From `CURRENT_TRUTH.md` and `HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md`:

| Gate | Goal | Status | Report |
|------|------|--------|--------|
| **G1** | PostgreSQL + claim-race | **PARTIAL_GO** | `P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md` |
| **G2** | OSRM runtime proof | **PARTIAL_GO** | `P0_G2_OSRM_RUNTIME_PROOF_01.md`, `SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md` |
| **G3** | Owner courier day | **PENDING_OWNER** | `OWNER_COURIER_DAY_REPORT_01.md` |
| **G4** | Dossier decision | **GO (decision)** | `DOSSIER_PATH_DECISION_01.md` — Path A recommended |
| **G5** | Surface-freeze tests | **GO** | `P0_G5_SURFACE_FREEZE_REPORT_01.md` |
| **G6** | SYSTEM_TRUTH sync | **GO** | `P0_G6_SYSTEM_TRUTH_RECONCILIATION_REPORT_01.md` |
| **G7** | Alembic on PostgreSQL | **PARTIAL_GO** | `P0_G7_ALEMBIC_POSTGRES_PROOF_01.md` |

**Overall P0: PARTIAL_GO** — next step is **proof**, not **features**.

### G1 acceptance commands

```powershell
docker compose up -d postgres
# DATABASE_URL=postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp
cd backend
py -3.11 -m pytest tests/test_postgres_claim_race_proof_01.py -q
```

### G2 acceptance commands

```powershell
docker compose up -d osrm   # after extract prepared
py -3.11 scripts/prove_osrm_runtime.py
py -3.11 -m pytest tests/test_routing_service_real_osrm.py -q
```

### G3 acceptance

Human-only: run `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md`, fill `OWNER_COURIER_DAY_REPORT_01.md`. **Agents must not mark G3 GO.**

---

# Part XIV — Next step playbook (decision-grade)

## 14.1 If you are the program owner (recommended decision tree)

```
START
  │
  ├─ Is backend pytest green on this checkout?
  │    NO → Fix drift FIRST
  │    YES → continue
  │
  ├─ Can you run docker compose postgres + claim-race green?
  │    NO → G1 blocks staging claim
  │    YES → G1 local GO
  │
  ├─ Can you run OSRM proof script exit 0?
  │    NO → pricing/route claims stay “fallback honest” only
  │    YES → G2 GO — update SELF_HOSTED_ROUTING proof doc
  │
  ├─ Did you personally complete owner runbook once?
  │    NO → G3 open — you lack human sign-off on two-sided loop
  │    YES → G3 GO — proceed to P1
  │
  P1: Pick ONE of: push · session hardening · delivery copy · SIL worker in staging
  P2: Pick ONE fork: POD · merchant payload · Stripe pilot · (NOT external beta without order)
END
```

## 14.2 If you are an external expert reviewer

**Read in order (2–3 hours):**

1. This report — Part 0 + Part I + Part XI  
2. `docs/SYSTEM_TRUTH.md`  
3. `docs/CURRENT_TRUTH.md` — P0 table  
4. `docs/HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md`  
5. `docs/PRODUCT_BOUNDARY_STAGE0.md` — forbidden claims  
6. One proof doc for your concern: claim race, OSRM, or ride-flow E2E  

**Do not read first:** `HALFAPP_DRIVER_PROGRAM_MASTER_REPORT_01.md` (2000+ lines — historical), raw `frontend/`, or Stripe modules without Stage 0 context.

## 14.3 If you are an AI coding agent

1. Read `HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md` — work P0 only until GO.  
2. Never modify closed lanes in `HALFAPP_AGENT_ACTION_DIRECTIVES.md`.  
3. After each task: update `CURRENT_TRUTH.md` + short `*_REPORT.md`.  
4. Run `assert-no-money-claims` / `assert-no-ai-providers` when touching driver UI.

## 14.4 What NOT to do next (anti-patterns)

- Rebrand entire codebase ride→job in one PR without program plan.  
- Market as DoorDash/Lyft competitor.  
- Add LLM auto-dispatch without governance layer.  
- Wire dossier endpoints into `driver-app/src/utils/api.js`.  
- Enable Stripe in demos without updating truth docs and UI guards.  
- Add merchant portal + POD + push + Stripe simultaneously (“illusion breadth”).  

---

# Part XV — Scoring rubric (expert self-assessment)

Rate 1–5 (1 = prototype, 5 = production delivery marketplace):

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Truth discipline / governance brain | **5** | Unusual at MVP stage; explicit forbidden claims |
| Dispatch correctness | **4** | Strong claim lock; PG proof partial |
| Lifecycle integrity | **4** | Guarded + tested; completed→cancel returns structured 409 |
| Delivery-appropriate courier UX | **3** | Map cockpit good; no POD, no push |
| Financial honesty | **4** | Ledger + simulated; UI guarded |
| Routing honesty | **3** | Fallback labeled; OSRM runtime missing |
| Requester loop | **3** | Shipped minimal; not consumer polish |
| Area intelligence (SIL/CRL) | **3–4** | v0.1 + worker path |
| Ops console | **2** | Minimal ops-app |
| Test coverage breadth | **4** | 383 passed, 9 skipped on SQLite dev; runtime gates remain |
| Production readiness | **2** | P0 PARTIAL_GO |
| **Composite** | **~3.2** | Strong spine, not production marketplace |

**Overall sentence:** **Strong delivery-driver execution spine and governance brain** inside a repo that **looks like a full marketplace** — next step is **proof + honesty + one fork**, not more surface illusion.

---

# Part XVI — Documentation map (the “brain” filesystem)

| Tier | Files | When to use |
|------|-------|-------------|
| **Tier 0 — Big picture** | This report, `SYSTEM_TRUTH.md` | Strategy, investor, next-phase |
| **Tier 1 — Daily engineering** | `CURRENT_TRUTH.md`, `BACKLOG.md`, `RIDE_LIFECYCLE_CONTRACT.md` | PR review, agents |
| **Tier 2 — Execution** | `HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md`, `HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md` | What to build next |
| **Tier 3 — Lane proofs** | `RIDE_002_*`, `P0_G1_*`, `RIDE_FLOW_UI_PROOF_*`, etc. | Audit single concern |
| **Tier 4 — Historical** | `HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_01–03`, `HALFAPP_DRIVER_PROGRAM_MASTER_REPORT_01` | Archaeology only |

**Approximate doc count:** 100+ markdown files under `docs/` — the governance brain is **large by design**.

---

# Part XVII — Glossary (delivery-first)

| Term | Meaning |
|------|---------|
| **Delivery job** | `Ride` row — one pickup, one dropoff |
| **Courier** | Approved driver using `driver-app` |
| **Requester** | Customer using `rider-app` |
| **Governance brain** | Docs + directives + CI guards constraining truth |
| **Dispatch brain** | Rule-based assignment (open board / cascade / auto-assign) |
| **Advisory AI brain** | Ride AI panel — never mutates dispatch |
| **Calculation record** | `ride_pricing` — not bank payment |
| **Simulated capture** | `ride_payments.status=captured` on complete |
| **GO / NO_GO / PARTIAL_GO** | Proof lane verdict |
| **Closed lane** | Must not rewrite without rescope order |
| **Owner courier day** | Human E2E per `OWNER_INTERNAL_TEST_RUNBOOK_01.md` |
| **Stable car P0** | API spine verification for owner vehicle test mode |

---

# Part XVIII — Closing statement

HalfApp is best understood as **two intertwined systems**:

1. **A delivery-driver execution application** — four apps, one backend authority, job lifecycle from request through delivered, earnings and audit, growing area intelligence, optional advisory AI.  
2. **A governance brain** — prevents the repository’s size, Stripe depth, dossier spine, and “ride” vocabulary from convincing you that production last-mile delivery is already done.

**The next step is not “add every marketplace feature.”** It is:

1. **Keep backend pytest green** — latest SQLite dev run is 383 passed, 9 skipped.  
2. **Close P0 gates** — PostgreSQL claim-race, OSRM runtime, owner courier day.  
3. **Align language** with delivery (§0.3) when speaking to experts and yourself.  
4. **Pick one delivery fork** — proof-of-delivery, merchant payload, real Stripe pilot, or staging hardening only — after gates pass.

When this report conflicts with older docs that deny a rider or ops product, trust **`HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md`**, **`SYSTEM_TRUTH.md` (2026-05-25)**, and **`OWNER_INTERNAL_TEST_RUNBOOK_01.md`**.

When this report conflicts with `CURRENT_TRUTH.md` on test counts or Alembic head, **run pytest and `alembic heads` locally** and update `CURRENT_TRUTH.md` after verification.

---

**Version:** 6.0  
**Lines:** ~720  
**Author:** Program documentation pass — codebase + docs + live pytest reconciliation (2026-05-25)  
**Next review trigger:** P0 gate closure · Alembic head change · pytest regression · owner G3 sign-off · external investor review
