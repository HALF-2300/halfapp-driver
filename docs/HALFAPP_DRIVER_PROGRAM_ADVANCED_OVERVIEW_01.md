# HALFAPP_DRIVER_PROGRAM_ADVANCED_OVERVIEW_01

> **Combined edition — Book A:** This file is **Part A** of [`HALFAPP_DRIVER_PROGRAM_MASTER_REPORT_01.md`](HALFAPP_DRIVER_PROGRAM_MASTER_REPORT_01.md). It is published together with **Book B** (`HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03`) in one volume because the overview answers *where we stand and what to do next* after recent lanes, while the comprehensive report explains *how the brain and spine work* in depth — strategy first, architecture second, one artifact for experts and program owners.

**Document ID:** `HALFAPP_DRIVER_PROGRAM_ADVANCED_OVERVIEW_01`  
**Audience:** Advanced engineering reviewers, program owners, mobility-marketplace experts, and the program lead  
**Workspace:** `c:\Users\him\Desktop\halfapp-driver`  
**Report date:** 2026-05-22  
**Verification snapshot (this session):** `262 passed` backend pytest (~124s); `77 passed` driver-app unit tests; ride-flow UI proof **GO**; trip audit read UI **GO**; OSRM runtime proof **NO_GO** (frozen); payments/PSP **NOT IMPLEMENTED**

**Authority order when facts conflict:**

1. `backend/main.py` + OpenAPI + green tests  
2. `driver-app/src/App.jsx` + production build guards  
3. Status docs dated 2026-05-22 (`CURRENT_TRUTH.md`, lane reports, proof statuses)  
4. `docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md` (program brain companion)  
5. Older overview docs and investor materials (verify before external use)

**This document does not authorize implementation.** It is a planning and research bridge for the next program stage.

---

## Executive verdict

HalfApp Driver is a **backend-owned, driver-only ride-hailing MVP** with a **real lifecycle spine**, **open-board dispatch with concurrency and audit proofs**, a **v0.1 integer-cent pricing ledger**, **honest routing metadata with explicit fallback**, and a **new read-only trip audit / receipt surface** that explains obligations without pretending money moved. It is **not** a finished marketplace, payment processor, geo-dispatch platform, rider product, or city-scale mobility OS.

The program’s distinguishing asset is **dual but coupled**:

1. **Runtime spine** — `backend/` + `driver-app/` that survives refresh, records claims and visibility, completes priced trips in Playwright, and exposes audit APIs the UI actually calls.  
2. **Governance brain** — documentation, contracts, phased acceptance reports, and agent directives that forbid claiming capabilities the backend cannot prove.

**Overall maturity:** Strong **prototype with closed P0 gates and a credible driver cockpit**; **not** production marketplace or public launch candidate.

**Strongest product value today:** A driver can go online, see a real backend ride request, accept under atomic claim rules, execute the full lifecycle on a map-first cockpit, complete with **locked integer-cent pricing**, and later open a **trip audit** that ties lifecycle, pricing, settlement obligation rows, marketplace ledger events, and route truth together — with copy that does **not** claim PSP payout or production OSRM.

**Weakest strategic gaps:** No payment execution; no production OSRM runtime proof; parallel dossier spine; SQLite-only concurrency proof for claims; no rider app; token revocation absent; repository sprawl that confuses reviewers.

**Recommended strategic posture for the next stage:** Treat the next phase as **computational honesty and launch-gate closure**, not screen expansion. Evolve **`/drivers/*` active spine first**; force a **dossier Path A vs B decision** before any marketplace feature that touches money, dispatch identity, or ledger tables — but **do not wire dossier from UI without a reconciliation plan**.

---

## What is now strong

### 1. Backend lifecycle and dispatch integrity (closed P0 lanes)

The active path enforces a formal ride state machine with structured `409` responses on invalid transitions (RIDE-001 **GO**). Open-board dispatch uses atomic first-claim-wins semantics with concurrency tests (RIDE-002 **GO**). A sequential dispatch cascade exists behind a feature flag (RIDE-003 **GO**). Driver approval gates online/accept behavior (DRIVER-002 **GO**). Presence and busy-scope guards protect lifecycle transitions (DRIVER-001B **GO**). JWT role middleware enforces driver/rider/admin boundaries on mounted routes (AUTH-001 **GO**).

**Why this matters:** These are the hardest marketplace invariants to retrofit. Reopening them without rescope would invalidate E2E proofs, audit narratives, and expert trust.

**Evidence:** `tests/test_ride_001_transition_guards.py`, `tests/test_ride_claim_lock_concurrency.py`, `tests/test_ride_003_dispatch_cascade.py`, `tests/test_driver_approval.py`, `docs/RIDE_001_STATE_MACHINE_GUARDS_REPORT.md`.

### 2. Test discipline and isolation

Per-test database wipe and a single-command full backend suite are stable (TEST-ISOLATION-01 **GO**). This session: **262 backend tests passed** in one pytest invocation. Driver-app unit suite: **77 tests passed**, including forbidden-phrase guards (no AI providers in `src/`, no payment/dossier false claims in cockpit layout scans).

**Why this matters:** The brain’s claims are enforceable by CI and local proof lanes; agents cannot silently regress lifecycle without failing tests.

### 3. v0.1 pricing ledger (integer cents, lock on complete)

`ride_pricing` stores quote and completion breakdown in integer cents. Trip completion sets `financial_locked`. The cockpit and ride-flow E2E assert commission, service fee ($1.50 fixture), tips, tolls, and driver total payout fields after complete and after page reload.

**Boundary (explicit):** This is **pricing truth**, not payment settlement, wallet balance, or payout execution.

**Evidence:** `tests/test_pricing_ledger_v01.py`, `docs/RIDE_FLOW_UI_PROOF_V0_2_STATUS.md`, `driver-app/src/utils/ridePricingDisplay.js`.

### 4. Map-first driver cockpit with E2E lock

`MapHome.jsx` is the operational center: Leaflet + OpenStreetMap tiles, bottom-sheet ride flow, backend-driven driver states, external Google Maps navigation links (no embed). Recent polish lane preserved full lifecycle; E2E re-locked after UI changes (HALFAPP_DRIVER_COCKPIT_RIDE_FLOW_E2E_LOCK_01 **GO**).

**Evidence:** `driver-app/tests/ride-flow-ui-proof.spec.ts` — 1 passed (~42s); `docs/HALFAPP_DRIVER_COCKPIT_RIDE_FLOW_E2E_LOCK_01_REPORT.md`.

### 5. Dispatch and marketplace audit trail

`ride_visibility`, `ride_claim_attempts`, `marketplace_ledger_events` (hash-chained append-only), and `GET /drivers/rides/{ride_id}/transparency` provide operational proof for open-board exposure, hide/dismiss, and claim conflicts. Drivers see friendly conflict messaging when another driver wins the claim.

**Evidence:** `tests/test_dispatch_auditability.py`, `tests/test_marketplace_ledger_events.py`, `driver-app/src/utils/rideTransparency.js`.

### 6. Production SECRET_KEY guard

Production-like environments fail fast on default/short/placeholder `SECRET_KEY` values without logging the secret (HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01 **GO**).

**Evidence:** `backend/production_guards.py`, `tests/test_production_guards.py`.

### 7. Engineering Intelligence Safe Shell (LOCAL_CONTEXT_ONLY)

A dev-flagged `#/engineering-intelligence` route surfaces **local** program context (proof lane statuses, forbidden claims, next gaps) — **not** ride-product AI. It helps agents and owners align with truth boundaries without calling external models from the driver product path.

**Evidence:** `tests/test_engineering_intelligence_status.py`, `driver-app/src/utils/engineeringIntelligenceContext.js`.

### 8. Backend engineering-assistant gate repair

The optional `/engineering-assistant/*` proxy is **disabled by default** (`ENGINEERING_ASSISTANT_ENABLED` unset/false). Enabling requires explicit configuration and server API key — **not wired** to the Safe Shell or driver ride product.

**Why this matters:** Prevents accidental “the app has AI” narratives or undeclared external calls from production-shaped deployments.

### 9. Truth Sync / Backlog Reconciliation

`docs/CURRENT_TRUTH.md`, `docs/BACKLOG.md`, and `docs/PRODUCT_BOUNDARY_STAGE0.md` are reconciled to v0.1 reality with explicit **do not reopen** lanes and forbidden claims. Stale tickets (e.g. parallel `fare_ledger_entries`) are marked superseded.

### 10. Driver Trip Audit / Receipt Details UI (read-only)

Completed trips expose **Trip audit / receipt details** from Trips list → `GET /drivers/rides/{ride_id}/audit`. The UI aggregates lifecycle events, integer-cent pricing, `financial_locked`, settlement obligation rows, filtered marketplace ledger events, and route truth with `osrm_runtime_claim: not_proved`. Obligation language is enforced in copy and unit tests; forbidden PSP phrases are guarded.

**Evidence:** `docs/HALFAPP_DRIVER_AUDIT_READ_UI_01_REPORT.md`, `backend/services/ride_audit.py`, `driver-app/src/components/TripAuditReceipt.jsx`, `tests/test_driver_ride_audit.py`, `driver-app/tests/unit/tripAuditReceipt.test.js`.

### 11. Route snapshot read surface (honest fallback)

`GET /drivers/rides/{ride_id}/route-snapshots` and `RouteTruthDetails` in cockpit and audit show provider metadata and explicitly state OSRM runtime is **not proved** when applicable.

**Evidence:** `tests/test_route_snapshot_read_ui.py`, `backend/services/route_snapshots_read.py`, `driver-app/tests/unit/routeTruthDetails.test.js`.

### 12. The governance brain (program intelligence layer)

**“The brain”** is not an deployed ML service. It is the **program intelligence layer**: `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md`, Stage 0 boundary lock, transparency architecture, proof-lane reports with GO/NO_GO verdicts, and operating rules that require every driver-visible fact to trace to backend records and tests.

**Critical property:** The brain does not auto-enforce — tests, prod build guards, and proof lanes do. The brain **prevents illusion-driven engineering** when followed.

---

## What is still weak

### 1. No payment processing or payout execution

There is **no** Stripe, PSP capture, wallet, payout batch, refund processing, or bank movement. `settlement_entries` are **obligation rows** — backend-computed amounts that may inform a future settlement product, not money movement. UI and audit copy state this; marketing must not blur the line.

### 2. No production OSRM runtime proof

The OSRM self-hosted **code path** is unit-tested with mocked HTTP. **Runtime** proof on Docker/VPS (live road-network geometry, `used_fallback=false` in real runs) remains **NO_GO** per `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md`. Until GO, distance/duration for quotes may honestly be `haversine_fallback` — not road-network truth.

### 3. Parallel dossier spine (architectural debt)

`POST /supply/heartbeat`, `POST /demand/request`, `POST /trip/complete` and dossier `ledger_*` tables implement an alternate marketplace model (geospatial auto-match, double-entry books). They are **mounted for foundation/tests** but **not** called from `driver-app/src/utils/api.js`. Two presence models, two lifecycle event stores, and two financial abstractions coexist.

**Risk:** Accidental UI wiring, dual-write, or expert confusion about “which ledger is truth.”

### 4. Postgres / production database proof gaps

Claim-race proofs run on SQLite in dev CI. Production concurrency, locking (`FOR NO KEY UPDATE SKIP LOCKED` on dossier path), and PostGIS behavior are **not** proven on a Postgres CI matrix for the **active** spine.

### 5. Token security incomplete

No refresh tokens, no revocation store, no structured session rotation. SECRET_KEY guard helps boot safety but does not solve stolen-token lifecycle.

### 6. CORS and observability partial

Production CORS requires explicit origins (partial hardening). Structured logging, request IDs, and operational telemetry are not first-class.

### 7. Repository sprawl and misread risk

Legacy `frontend/`, dormant routers (`admin`, `users`, legacy `rides`), dormant driver components, `video-gate/`, and dossier endpoints **look** like product. New reviewers or agents can mis-attribute behavior without reading Stage 0 docs.

### 8. Dispatch transparency gaps (vs production marketplace)

Open board is **honest** but not **complete**: no full candidate eligibility rounds, service-area membership proofs, or geo-fair exclusion reasons for drivers who never saw a ride.

### 9. Geocoding and ETA product gaps

Coordinates must be supplied; address labels are not proved locations. No marketed live ETA product; map visualization must not be read as routing proof.

### 10. Documentation drift on completed lanes

`docs/BACKLOG.md` P1 queue still lists “Driver audit read UI” and “Route snapshot read UI” as pending in places — **implementation has shipped** (audit UI GO, route read GO). Truth sync should update backlog classification to avoid duplicate work orders.

### 11. WebSocket / real-time presence

Presence is REST + heartbeat with stale/disconnected derivation — adequate for MVP, not a real-time gateway.

### 12. Rider side is API-only

`POST /rides/` and cancel exist; no rider app. Marketplace demand in demos is simulation or test harness — not organic rider demand.

---

## Driver UX assessment

### Map-first cockpit — current quality

**Architecture:** `/#/driver` → `MapHome` with `DriverCockpitShell`, `MapView`, `MarketplaceBottomSheet`, state-driven sheets (`sheet-online-idle`, `sheet-request-incoming`, through completed), and `RidePayoutSummary` / `TripTruthDetails` for pricing and expandable truth.

**What feels close to production quality:**

- Full ride loop with backend persistence across reload (E2E proven).  
- Clear driver state labels (Offline, Online, Incoming, To pickup, At pickup, In progress, Completed).  
- Pricing visible on incoming and completed with locked-state indicator.  
- Claim conflict surfaced with backend-derived transparency, not invented copy.  
- External navigation via Google Maps links — familiar driver pattern.  
- Production build rejects mock mode and guard bypass flags.  
- Lightweight Uber-like polish without claiming Uber parity (spacing, sheet behavior, trip details collapse).

**What still feels MVP / unfinished:**

- Hash-router web app, not native iOS/Android driver shell.  
- Geolocation permission UX varies by browser; location chip states need driver education.  
- Dev simulation dock and engineering intelligence route visible only in dev — but their **existence** in repo can confuse if flags leak.  
- Trips/Earnings/Notifications/Profile are functional but not at “daily driver OS” depth (filters, disputes, tax docs, etc.).  
- No turn-by-turn in-app navigation — by design (external Maps), but some drivers expect in-app voice nav.  
- Experimental traffic signal markers are optional and not commercial traffic — must stay labeled.

**What might confuse a real driver:**

| Confusion | Cause | Mitigation direction |
|-----------|--------|----------------------|
| “Why is my payout different from rider total?” | Integer-cent breakdown vs legacy `fare_amount` dollars | Audit page + Trip details; keep labels consistent |
| “Did I get paid?” | Obligation language vs bank deposit | Audit disclaimer is good; Earnings screen must never imply transfer |
| “Is this route accurate?” | Haversine fallback when OSRM down | Route truth section + `osrm_runtime_claim: not_proved` |
| “Another driver took it” | Open board 409 | Transparency endpoint messaging — adequate for beta |
| “Ride disappeared” | Hide/dismiss TTL | Needs clearer “hidden from your board” copy |
| “Simulation ride” | `lifecycle_reason=simulation` | Must stay visually distinct in demo/beta |
| Decline releases to pool | `accepted → requested` not terminal decline | Drivers used to Uber “decline” semantics — document behavior |

**Net UX verdict:** **Credible for internal demo and closed trusted-driver beta** on lifecycle + pricing honesty. **Not** yet credible for public launch or drivers who equate the app with instant bank payment.

---

## Trust / transparency assessment

### Trip Audit / Receipt Details flow

**Strengths:**

- Single read API aggregates lifecycle, pricing, settlements, ledger events, route truth — reduces frontend invention.  
- `AUDIT_COPY` in backend enforces `payment_execution: not_implemented` and obligation semantics.  
- Technical proof expander keeps hash/event IDs available without cluttering primary UX.  
- `tripAuditFormat.js` and unit tests guard forbidden phrases (PSP, “paid out”, production OSRM claims).  
- Route truth honestly shows fallback and `not_proved` OSRM runtime claim.  
- Link from completed trips in `TripsList` makes audit discoverable.

**Weaknesses / improvement targets for normal drivers:**

| Topic | Current state | Improvement |
|-------|---------------|-------------|
| **Pricing** | Integer-cent breakdown in audit | Plain-language “what rider paid vs what you earn” one-liner above cents table |
| **Settlement obligations** | “Recorded obligation, not paid out” | Short glossary: obligation vs payout vs charge |
| **Route truth** | Provider + fallback flags | Simple map icon: “straight-line estimate” vs “road network” when OSRM GO |
| **Ledger events** | Event types in technical section | Top 3 human events (accepted, completed, earning.calculated) in primary view |
| **Dispatch** | Transparency on conflict, not in audit | Optional “why you saw this ride” link from audit to transparency payload |
| **Refresh** | Reload fetches audit again | Stale indicator if ride still unlocking (edge: rare) |

**Obligation language clarity:** **Adequate for expert and careful beta drivers**; **not yet adequate for mass-market drivers** without a short onboarding tooltip or glossary.

**Is transparency a product advantage yet?** **Partially.** Experts and trust-oriented drivers can see more than typical gig apps show at accept time. Mass-market advantage requires **simpler primary narrative** and **same facts, less jargon** — without removing the technical expander.

---

## Architecture assessment

### Active spine (authoritative)

```
driver-app (React/Vite, HashRouter)
    → JWT /auth/*
    → /drivers/* only (api.js boundary)
backend/main.py
    → drivers, auth, rider_rides, notifications, internal
    → dossier_marketplace (mounted, not in driver-app)
SQLAlchemy + Alembic 0001–0015
    → rides, ride_pricing, driver_presence, visibility, claims, marketplace_ledger_events, settlement_entries, route_snapshots
```

### The brain’s role in architecture

The brain sets **execution order** (9 agent actions, P0 lanes), **forbidden claims**, and **per-feature success definition** (5 questions: record, endpoint, test, audit event, refresh/conflict behavior). It does not replace OpenAPI or tests.

**Strength:** Aligns multi-agent development with a single truth story.  
**Weakness:** Manual discipline required; stale docs (backlog P1) erode trust.

### Dossier parallel spine — practical risk

| Risk | Severity | Description |
|------|----------|-------------|
| Dual marketplace truth | **High** if wired carelessly | Two dispatch models, two presence stores, two ledger philosophies |
| Expert misread | **Medium** | Reviewers cite `/demand/request` as “the app” |
| Migration cost | **High** if Path B chosen late | Merging `rides` with dossier trip IDs and ledger tables |
| Feature delay | **Medium** if decision deferred | Every money/dispatch feature needs “which spine?” answer |
| Accidental UI call | **High** | One PR adding `/supply/heartbeat` to api.js breaks boundary |

**Recommendation:** **Keep evolving `/drivers/*` first.** Schedule a **time-boxed dossier decision** (Path A: active spine + borrow dossier patterns; Path B: merge) **before** payments slice or geo-dispatch — not necessarily before all polish. **Never** wire dossier from UI without `HALFAPP_DOSSIER_SPINE_RECONCILIATION_01` merge plan.

### Areas that must not be reopened (without explicit rescope)

- AUTH-001, RIDE-001, RIDE-002, RIDE-003, DRIVER-001B, DRIVER-002  
- TEST-ISOLATION-01, SECRET_KEY guard, Engineering Intelligence Safe Shell boundary  
- Claim-lock semantics, lifecycle guard matrix, approval gates  
- Driver-app dossier API boundary (`api.js` → `/drivers/*` only)  
- Forbidden claims list in `PRODUCT_BOUNDARY_STAGE0.md`

### Proof gaps that remain open

1. OSRM runtime on Docker/VPS  
2. Postgres claim-race suite for active spine  
3. OpenAPI contract drift CI (Ticket 1.3 partial)  
4. Token revocation/refresh design  
5. Full driver-facing dispatch round narrative (eligibility)  
6. Geocoding proof lane (if addresses become inputs)

---

## Launch readiness assessment

### Ready for internal demo

| Capability | Status |
|------------|--------|
| Driver login/register | Yes |
| Go online / presence | Yes |
| Simulated or test-harness rider request | Yes (simulation flag / Playwright rider API) |
| Accept → complete lifecycle | Yes (E2E) |
| Locked pricing display | Yes |
| Trip audit read-only | Yes |
| Claim conflict demo | Yes |
| Engineering intelligence status | Yes (dev flag) |

**Caveat:** Present with Stage 0 framing — no payments, no production OSRM, open board only.

### Ready for closed trusted-driver beta

| Requirement | Status |
|-------------|--------|
| Lifecycle correctness | **Ready** |
| Honest pricing copy | **Ready** with glossary improvements |
| Audit/receipt for disputes | **Ready** (read-only) |
| Production SECRET_KEY | **Ready** (guard shipped; ops must set real secret) |
| Real demand (rider app) | **Not ready** — API/test harness only |
| Real money movement | **Not ready** — by design |
| Road-network routing truth | **Not ready** — fallback honest |
| Mobile-native app | **Web MVP** — acceptable for tiny beta if expectations set |
| Support/runbooks | **Partial** — docs exist, ops tooling thin |
| Legal/compliance (payments, insurance) | **Out of scope** until PSP design |

**Beta verdict:** **Possible** for 5–20 trusted drivers in one city **if** ops seeds rides via API/simulation, drivers understand **no real payouts**, and routing claims stay honest.

### Blocks limited live pilot

1. No organic rider demand channel (rider UI).  
2. No payment capture — cannot close commercial loop.  
3. OSRM runtime NO_GO — distance-based pricing may be challenged.  
4. SQLite-proven concurrency only — pilot with money-adjacent obligations needs Postgres proof.  
5. No token revocation — session risk for lost devices.  
6. No ops admin on active API — manual DB/API support burden.  
7. Dossier decision unset — risk if pilot scope creeps into “use dossier ledger.”

### Blocks public launch

Everything in limited pilot, plus:

- PSP integration, payout execution, reconciliation, refunds, tax reporting  
- Production OSRM or contractual honesty about estimates  
- Postgres + HA + monitoring + on-call  
- Rider app and demand generation  
- Legal, insurance, background checks, city compliance  
- Native driver apps or PWA parity drivers expect  
- Geo-fair dispatch or explicit “open board” product positioning  
- Admin console, fraud, support tooling  
- Security audit (CORS, rate limits, penetration test)  
- Removal/quarantine of legacy surfaces from reviewer path

---

## Top 10 next slices

Ordered for **maximum honesty per engineering week** before surface expansion. Tags: **[P]** product polish, **[T]** trust/audit, **[R]** routing/OSRM, **[S]** security, **[$]** payments, **[A]** architecture.

### 1. OSRM runtime proof (Docker/VPS) — [R]

**Why first:** Routing truth underpins fare distance/duration, route snapshots, and audit credibility. Code path GO without runtime GO is the largest **honesty gap** visible to experts and drivers.

**Done when:** `SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS` runtime verdict **GO**; live `route_provider=osrm_self_hosted`, `used_fallback=false` in proof script output; UI still honest when OSRM down.

**Do not:** Claim production OSRM in marketing until this lane is GO.

---

### 2. Postgres claim-race proof on active spine — [S][A]

**Why second:** SQLite locks ≠ production. Before pilot with real obligations or higher concurrency, prove `POST /drivers/accept-ride` under Postgres with parallel clients.

**Done when:** CI matrix (or documented manual proof) extends `test_ride_claim_lock_concurrency.py` against Postgres `DATABASE_URL`.

---

### 3. Dossier Path A vs Path B decision (document only, no UI wire) — [A]

**Why third:** Unblocks payments and dispatch evolution without dual-write surprises. Path A: evolve `/drivers/*`, borrow dossier patterns; Path B: merge spines with migration plan.

**Done when:** Signed decision doc + updated `HALFAPP_DOSSIER_SPINE_RECONCILIATION_01` with chosen path and **explicit non-goals**.

**Do not:** Wire dossier endpoints to `driver-app` in the same slice.

---

### 4. Truth sync backlog + transparency doc refresh — [T]

**Why fourth:** Audit UI and route read UI shipped; backlog still lists them pending. Stale brain docs cause duplicate work and agent thrash.

**Done when:** `BACKLOG.md`, `HALFAPP_TRANSPARENCY_ARCHITECTURE.md` “Do not claim yet” sections updated; P1 queue reflects audit GO.

---

### 5. Driver trust copy pass (glossary + primary audit narrative) — [T][P]

**Why fifth:** Transparency advantage requires **comprehension**, not more fields. Short obligation glossary; top-3 events on audit primary surface; Earnings screen alignment with audit language.

**Done when:** User-tested copy with 2–3 non-engineer drivers; unit tests still forbid PSP phrases.

---

### 6. OpenAPI contract drift CI — [S]

**Why sixth:** Prevents silent API/contract divergence as slices land. Ticket 1.3 partial → closed.

**Done when:** CI fails on OpenAPI diff vs `docs/RIDE_LIFECYCLE_CONTRACT.md` baseline.

---

### 7. Token revocation / refresh design (design + minimal implementation) — [S]

**Why seventh:** SECRET_KEY guard is necessary not sufficient for pilot device loss.

**Done when:** ADR + optional refresh token store or denylist; tests for revoked token 401.

---

### 8. CORS + rate limit production checklist — [S]

**Why eighth:** Low-cost hardening before any pilot URL is shared.

**Done when:** Deploy checklist documented; `test_production_guards.py` scenarios covered in staging.

---

### 9. PSP / settlement design OR hard no-payout product lock — [$][A]

**Why ninth:** Depends on dossier decision (slice 3). Integer-cent pricing exists; **execution** does not. Either design Stripe Connect (or equivalent) with settlement_entries mapping, or formally lock “no payout” in product boundary for next quarter.

**Do not:** Ship payment UI without execution backend and reconciliation tests.

---

### 10. Rider demand minimum (API hardening + harness, not full rider app) — [P]

**Why tenth (not earlier):** User constraint — **no rider app before driver truth gates stable.** Driver gates are now stable enough for **demand harness** improvement (scheduled rides API, ops scripts), not consumer rider UI.

**Done when:** Repeatable rider trip creation for beta without Playwright-only; still no rider mobile app.

**Explicitly deferred after 10:** Full rider app, nearest-driver dispatch, admin console, ride-product AI/LLM, dossier UI wiring.

---

## Better-than-Uber angle

### What HalfApp Driver can do better **at this stage**

| Advantage | How |
|-----------|-----|
| **Honest open board** | Does not fake closest-driver matching; claim attempts and visibility are recorded |
| **Structured conflict proof** | 409 + transparency payload vs opaque “ride unavailable” |
| **Integer-cent pricing ledger** | Locked breakdown at complete; auditable fields |
| **Post-trip audit surface** | Lifecycle + pricing + obligations + ledger events + route truth in one read API |
| **Explicit non-claims** | OSRM not proved, no payment execution — reduces legal/brand risk if communicated well |
| **Backend-owned presence** | Online/offline/stale from server, not pure UI fiction |
| **Governance brain** | Program can move fast without claiming unbuilt features — if docs stay synced |

### What not to copy from Uber/Lyft

| Uber pattern | Why avoid now |
|--------------|----------------|
| Opaque surge/explanation | Without full pricing policy audit UI |
| Fake precision ETA | No geocoding/ETA proof |
| Instant “paid” messaging | No PSP |
| Nearest-driver fiction | Open board is the honest model |
| In-app everything (nav, wallet, support AI) | Scope explosion |
| Decline = gone forever | HalfApp releases to pool — different contract |
| Heavy map animation as truth | Map is visualization; backend metadata is truth |

### Transparency as product advantage (not clutter)

**Principle:** **One primary sentence per screen**, technical proof behind expanders.

- **Accept sheet:** “You earn $X if you complete; rider pays $Y; route estimate is [straight-line / road network].”  
- **Complete sheet:** “Earnings locked on server; not yet sent to your bank.”  
- **Audit:** “This is what we recorded” — not “this is what you were paid.”  
- **Conflict:** “Another driver claimed first at [time]” — link to transparency IDs for support.

**Anti-pattern:** Showing ledger event hashes, policy versions, and provider strings on the main accept card — that is **expert mode**, belongs in Trip audit technical section (already started).

---

## Critical questions for expert research

Use these in the next-stage research session with marketplace, payments, and mobility experts.

### Marketplace and dispatch

1. Is **open-board first-claim** defensible for a driver-first brand, or must we commit to geo-fair rounds before public positioning?  
2. What **minimum dispatch audit** do regulators or driver associations expect in a pilot city?  
3. When a driver **declines** by releasing to pool (`accepted → requested`), what UX and liability patterns do peers use?

### Financial and legal

4. What is the **smallest PSP integration** that supports “obligation rows → actual payout” without building a full wallet?  
5. How should **integer-cent `ride_pricing`** relate to **double-entry dossier `ledger_*`** if Path B is chosen?  
6. What driver-facing language satisfies **“not paid yet”** without sounding like the platform is withholding fraudulently?

### Routing and pricing

7. What is acceptable **pricing on haversine_fallback** for beta — cap, disclaimer, or block?  
8. What **runtime proof bar** matches industry “self-hosted OSRM in production” claims?  
9. Do we need **geocoding proof** before any address-typed pickup, or coordinates-only for pilot?

### Architecture and scale

10. **Path A vs B** for dossier: borrow patterns only, or merge before payments?  
11. What **Postgres migration** risks exist in `ride_claim_attempts` and visibility TTL at 100 concurrent drivers?  
12. Is SQLite acceptable for **any** paid pilot, or hard gate on Postgres?

### Security and operations

13. What **token model** (refresh + revocation) is minimum for driver devices in beta?  
14. What **CORS and rate-limit** profile matches a single-city web driver app?  
15. What **observability** (metrics, ride funnel, claim latency) is required before pilot?

### Product strategy

16. Can **transparency** be a marketed pillar with **no rider app** yet, or does it require rider-side receipts too?  
17. What **trusted-driver beta** size and duration validates lifecycle before payments?  
18. What should we **not build for 12 months** to avoid Uber parity trap?

---

## Final recommendation

**Verdict:** HalfApp Driver has crossed from “prototype with docs” to **“prototype with provable spine and a map-first cockpit that completes priced trips honestly.”** Recent lanes (SECRET_KEY guard, Safe Shell, engineering-assistant gate, truth sync, cockpit polish, ride-flow E2E lock, trip audit UI) **close critical trust and engineering gates** without expanding into payments or production routing.

**Do next:**

1. Run **expert research** using the critical questions above — especially dossier Path A/B, OSRM runtime bar, and PSP-minimum for obligations → payouts.  
2. Execute slices **1–3** (OSRM runtime proof, Postgres races, dossier decision) before marketing, pilot money, or dossier wiring.  
3. Execute slices **4–5** (doc sync, driver trust copy) in parallel — low risk, high comprehension payoff.  
4. Keep **all product evolution on `/drivers/*`** until dossier reconciliation explicitly merges contracts.  
5. Do **not** build rider app, ride-product AI, or payment UI until slices 1–3 and 9 are resolved with explicit GO/NO_GO documents.

**Do not:**

- Claim payments, production OSRM, or dossier dispatch as live driver truth.  
- Reopen P0 lanes without rescope.  
- Revive legacy `frontend` or wire dossier from UI without a merge plan.  
- Chase Uber UI parity at the expense of backend proof.

**Success at the next stage** is not more screens — it is **a single spine story** that survives expert scrutiny: every driver-visible dollar and mile traces to a **named backend record**, a **test**, and an **honest label** when execution does not exist yet.

---

## Appendix A — Recent completed lanes (context)

| Lane | Verdict | Role |
|------|---------|------|
| Production SECRET_KEY guard | **GO** | Fail fast on unsafe production secrets |
| Engineering Intelligence Safe Shell | **GO**, LOCAL_CONTEXT_ONLY | Dev program context, no ride AI |
| Backend engineering-assistant gate repair | **GO**, disabled by default | No accidental external assistant in prod |
| Truth Sync / Backlog Reconciliation | **GO** | Docs aligned to v0.1 |
| Driver cockpit lightweight Uber polish | **GO** | UX polish without scope creep |
| Driver cockpit ride-flow E2E lock | **GO** | Full lifecycle preserved after polish |
| Driver Trip Audit / Receipt Details UI | **GO** | Read-only audit end-to-end |

---

## Appendix B — Verification commands

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
py -3.11 -m pytest tests -q

cd c:\Users\him\Desktop\halfapp-driver\driver-app
npm test
npm run build
npm run test:e2e:ride-flow

cd c:\Users\him\Desktop\halfapp-driver
py -3.11 scripts\print_active_routes.py
```

---

## Appendix C — Key file index

| Concern | Path |
|---------|------|
| Active API mount | `backend/main.py` |
| Driver routes | `backend/routes/drivers.py` |
| Ride audit service | `backend/services/ride_audit.py` |
| Production guards | `backend/production_guards.py` |
| Driver app routes | `driver-app/src/App.jsx` |
| API boundary | `driver-app/src/utils/api.js` |
| Map cockpit | `driver-app/src/components/MapHome.jsx` |
| Trip audit UI | `driver-app/src/components/TripAuditReceipt.jsx` |
| Current truth | `docs/CURRENT_TRUTH.md` |
| Stage 0 boundary | `docs/PRODUCT_BOUNDARY_STAGE0.md` |
| Dossier reconciliation | `docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md` |
| Agent directives (brain) | `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md` |
| Program report (brain detail) | `docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md` |

---

## Appendix D — Product state deep dive

### What HalfApp Driver now truly does (end-to-end)

**Authentication and identity**

- Drivers register and log in via JWT (`POST /auth/register`, `POST /auth/login`).  
- `GET /auth/me` returns profile; driver role enforced on mounted routes.  
- Driver approval workflow gates going online and accepting rides when `driver_approval_status` is not approved.

**Presence and availability**

- Backend-owned presence: `GET/PUT /drivers/presence`, `POST /drivers/heartbeat`.  
- States include available, offline, paused, stale, disconnected (derived from heartbeat).  
- Going online may require coordinates and approval; busy drivers are scoped from accepting new rides while on active trip.

**Dispatch (open board)**

- Unassigned rides in `requested` appear on `GET /drivers/available-rides` with deterministic ordering metadata (policy version, rank).  
- `POST /drivers/accept-ride/{ride_id}` atomically assigns first successful claim; others receive structured `409` with transparency detail.  
- `POST /drivers/rides/{ride_id}/hide` dismisses a ride from the driver’s board with TTL visibility records.  
- Optional sequential cascade (RIDE-003) exists behind env flag — not the default open-board path.

**Lifecycle execution**

- Driver path: `requested → accepted → driver_arrived → in_progress → completed`.  
- Rider cancel: `requested|accepted → cancelled` via rider API.  
- Decline/release: `accepted → requested` (ride returns to pool — not terminal decline).  
- Each transition validated by backend guards; invalid transitions return structured errors.

**Pricing at quote and complete**

- `ride_pricing` row with integer cents: shareable fare, commission, service fee, tips, pass-through fees, customer total, driver payout components.  
- Quote on ride creation path; lock on complete (`financial_locked`).  
- UI shows payout summary on incoming and completed sheets; E2E asserts math including tip/toll fixtures.

**Routing metadata (not production OSRM claim)**

- `routing_service` selects provider; may stamp `osrm_self_hosted` in tests or `haversine_fallback` when OSRM unreachable.  
- `route_snapshots` rows written at quote/complete foundation points.  
- Ride row carries `route_provider`, `traffic_provider`, `used_fallback`, distance/duration used for pricing.

**Earnings and history**

- `GET /drivers/earnings` summarizes completed trips from backend records.  
- `GET /drivers/my-rides` lists trip history.  
- Trips list links completed rows to trip audit.

**Notifications**

- Notification routes exist for driver alerts; not a full push gateway product.

**Internal / test support**

- `GET /internal/system-health`, test user seeding for E2E (approval status, etc.).  
- Simulation: `POST /drivers/simulate-ride` when enabled — creates real `rides` row with `lifecycle_reason=simulation`.

**Rider side (API only)**

- `POST /rides/` creates demand; cancel endpoint exists.  
- No rider mobile/web UI in active product.

### What it still does not do

| Capability | Status |
|------------|--------|
| Payment capture / charge rider | NOT IMPLEMENTED |
| Driver payout to bank / wallet | NOT IMPLEMENTED |
| Refunds / adjustments product | NOT IMPLEMENTED |
| Production OSRM runtime | NOT PROVED |
| Live ETA product guarantee | NOT SHIPPED |
| Geocoding from address text | NOT PROVED |
| Nearest-driver geo dispatch | NOT SHIPPED (open board only) |
| Dossier auto-match in driver app | NOT WIRED |
| Rider app | NOT SHIPPED |
| Admin ops console on active API | NOT SHIPPED |
| Token refresh / revocation | NOT IMPLEMENTED |
| WebSocket real-time gateway | NOT IMPLEMENTED |
| Ride-product LLM / AI inference | NOT IMPLEMENTED |
| City-scale ops (zones, airports, fleet) | NOT SHIPPED |
| Full candidate eligibility audit UI | NOT SHIPPED |

### Strongest product value right now (one sentence for decks)

**“A driver can complete a backend-proven ride on a map-first cockpit, see integer-cent locked pricing, and audit exactly what the server recorded — without the platform pretending money moved or roads were routed when they were not.”**

---

## Appendix E — The brain: expanded reference for experts

### Brain inventory (what to read first)

| Priority | Document | Purpose |
|----------|----------|---------|
| 1 | `docs/CURRENT_TRUTH.md` | Short operational truth table |
| 2 | `docs/PRODUCT_BOUNDARY_STAGE0.md` | Forbidden claims + active surfaces |
| 3 | `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md` | Execution order, P0 lanes, operating rules |
| 4 | `docs/HALFAPP_TRANSPARENCY_ARCHITECTURE.md` | Five pillars: current vs target |
| 5 | `docs/RIDE_LIFECYCLE_CONTRACT.md` | API lifecycle contract |
| 6 | `docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md` | Parallel spine map |
| 7 | `docs/BACKLOG.md` | Ticket classification (verify dates) |
| 8 | `docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md` | Full program + brain mechanics (~750 lines) |

### Nine agent actions — condensed status

| # | Action | Status |
|---|--------|--------|
| 1 | Lock active product boundary | Largely done |
| 2 | Backend-owned driver presence | Done |
| 3 | Backend ride hide/dismiss | Done |
| 4 | Dispatch auditability | Done |
| 5 | Marketplace ledger events | Done |
| 6 | Migration discipline (Alembic) | Done |
| 7 | Financial ledger foundation | Done (pricing + obligation rows; no PSP) |
| 8 | Route snapshot foundation | Done (foundation + read UI) |
| 9 | Production hardening | Partial (rate limit, SECRET_KEY; revocation/logging remain) |

### Per-feature success definition (apply to every new slice)

1. Which **backend record** proves this?  
2. Which **endpoint** changed it?  
3. Which **test** covers it?  
4. Which **audit event** explains it?  
5. What happens on **refresh, retry, conflict, or disconnect**?

### Brain failure modes (when the brain is ignored)

| Failure mode | Symptom | Example |
|--------------|---------|---------|
| Illusion shipping | UI shows feature backend lacks | “Paid to your bank” without PSP |
| Spine drift | Two truths for same concern | Dossier + active both in api.js |
| Stale docs | Agents rebuild closed lanes | Re-implement claim lock “fix” |
| Mock in prod | Build flags leak | `VITE_ALLOW_OFFLINE_MOCK` in prod |
| Map as truth | Pretty polyline without provider | Draw route while `haversine_fallback` |
| Legacy revival | frontend/admin mounted | Breaks Stage 0 boundary |

### Relationship: brain vs runtime vs verification

```
Governance brain (docs)
    ↓ constrains
Human / Cursor agents
    ↓ implement
backend + driver-app + Alembic
    ↓ verified by
pytest (262) + driver unit (77) + Playwright ride-flow + prod build guards
    ↓ feeds back to
Proof lane reports (GO/NO_GO) + CURRENT_TRUTH updates
```

---

## Appendix F — Engineering truth matrix

| Foundation | Protected? | Proof | Do not reopen |
|------------|------------|-------|----------------|
| JWT + RBAC | Yes | AUTH-001 tests | Role bypass without rescope |
| Lifecycle FSM | Yes | RIDE-001 tests | Ad-hoc status writes |
| Atomic claim | Yes | RIDE-002 tests | Non-atomic accept |
| Cascade | Yes | RIDE-003 tests | Change timeout semantics silently |
| Driver approval | Yes | DRIVER-002 tests | Online without approval |
| Presence busy guard | Yes | DRIVER-001B tests | Accept while busy |
| Test isolation | Yes | conftest wipe | Shared DB between tests |
| SECRET_KEY prod guard | Yes | test_production_guards | Allow change_me in prod |
| Safe Shell boundary | Yes | engineering intelligence tests | External AI on ride path |
| Pricing integer cents | Yes | test_pricing_ledger_v01 | Float money fields |
| financial_locked | Yes | ride-flow E2E | Unlock after complete |
| Audit read API | Yes | test_driver_ride_audit | Write via audit endpoint |
| Obligation copy | Yes | tripAuditReceipt tests | PSP language in UI |
| api.js /drivers only | Yes | route surface / reviews | Dossier in driver-app |
| Prod build mock guard | Yes | assert-prod-truth.mjs | Mock in production build |

| Gap | Severity | Notes |
|-----|----------|-------|
| OSRM runtime | High for routing claims | Code GO, runtime NO_GO |
| Postgres races | High before paid pilot | SQLite only today |
| Dossier decision | High before payments | Parallel tables |
| OpenAPI drift CI | Medium | Manual scripts exist |
| Token revocation | Medium | JWT only until designed |
| Eligibility rounds | Low for MVP | Open board honest |
| Geocoding | Medium if addresses used | Coords-only today |

---

## Appendix G — Mounted API surface (driver-relevant)

**Auth:** `/auth/register`, `/auth/login`, `/auth/me`

**Drivers (primary):** presence, heartbeat, available-rides, accept-ride, hide, lifecycle transitions, my-rides, earnings, statistics, ride audit, route-snapshots, transparency, simulate-ride (when allowed), profile/location updates

**Rider:** `/rides/` create, cancel, action

**Notifications:** driver ride alerts, list/mark read

**Internal:** system-health, test-users (non-prod patterns)

**Dossier (foundation only — not driver-app):** `/supply/heartbeat`, `/demand/request`, `/trip/complete`

Verify live list: `py -3.11 scripts/print_active_routes.py`

---

## Appendix H — Lifecycle and data stores (quick reference)

**Ride statuses (storage):** `requested`, `accepted`, `driver_arrived`, `in_progress`, `completed`, `cancelled`

**Key tables (active path):** `users`, `rides`, `ride_pricing`, `driver_presence`, `ride_visibility`, `ride_claim_attempts`, `marketplace_ledger_events`, `settlement_entries`, `route_snapshots`, `events`, `notifications`

**Dossier tables (parallel):** `active_drivers`, `trip_lifecycle_events`, `ledger_accounts`, `ledger_transactions`, `ledger_entries`

**Do not conflate:** `marketplace_ledger_events` (audit) ≠ `ledger_entries` (dossier double-entry) ≠ `settlement_entries` (obligations) ≠ PSP money movement.

---

*End of HALFAPP_DRIVER_PROGRAM_ADVANCED_OVERVIEW_01*
