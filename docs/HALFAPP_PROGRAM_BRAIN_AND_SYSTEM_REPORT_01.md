# HalfApp Driver Program — System Brain & Comprehensive Technical Report

**Document ID:** `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01`  
**Date:** 2026-05-23  
**Audience:** Program owner, senior engineers, architects, investors with technical depth, coding agents entering the repo cold  
**Workspace:** `c:\Users\him\Desktop\halfapp-driver`  
**Alembic head (at authoring):** `0031_crl_foundation`  
**Backend tests collected:** 342 (`py -3.11 -m pytest tests --collect-only`)  
**Driver-app unit tests:** 124+ (per last green `npm test` run) + Playwright E2E suites  

**How to use this document:** Read Sections 1–4 for the big picture, Section 5 for the “brain,” Sections 6–9 for implementation truth, Sections 10–12 for strengths/weaknesses/gaps, Section 13 for what to do next. Shorter operational truth lives in `docs/CURRENT_TRUTH.md`; launch blockers in `docs/HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01.md`.

> **Single completion checklist (what’s left to build):** `docs/HALFAPP_COMPLETION_MASTER_CHECKLIST_01.md`  
> **Expanded narrative edition (investors / partners):** `docs/HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_02_EXPANDED.md`

---

# SECTION 1 — Executive summary (one page)

HalfApp Driver is a **backend-authoritative driver ride-hailing MVP** built as a FastAPI + SQLAlchemy service and a React/Vite driver web application. It is **not** a full two-sided marketplace product, **not** a production payments platform, and **not** a municipal traffic or demand forecasting system — though it now contains **foundational “city intelligence” layers** that explain *patterns* in aggregated app data with strict honesty gates.

**What works credibly today:** A driver can register/login (JWT), pass an approval gate, go online with backend presence, see open-board ride offers, atomically claim a ride, progress through pickup/arrive/start/complete, view earnings and trip audit receipts backed by integer-cent pricing rows, filter/export trip history, receive in-app notifications on lifecycle events, and operate a map-first cockpit with experimental overlays for fleet-slow zones and cause-labeled city activity.

**What the “brain” is:** A stack of **truth layers** — not a single ML model — that moves from raw events → aggregates → honesty-gated outputs → driver-facing explanations:

1. **Marketplace spine** — lifecycle, dispatch, claim lock, pricing ledger, settlement obligation rows.  
2. **Transparency spine** — visibility, claim attempts, dispatch ordering metadata, 409 conflict proof.  
3. **Spatial spine** — route snapshots, OSRM adapter with haversine fallback, route truth UI.  
4. **Street Intelligence Layer (SIL)** — H3/grid aggregates, busy/slow scores, route quotes + proof receipts.  
5. **City Reality Layer (CRL)** — rule-based cause attribution (“why” demand/supply patterns, not just “where”).  
6. **Fleet telemetry** — keyless slow-zone heat from driver GPS speeds (not TomTom/Mapbox live traffic).

**Strategic verdict:** The program has crossed from “demo UI with mocks” to “narrow but **auditable** product spine.” The risk is **over-reading** map visuals, intelligence overlays, or payment-adjacent schema as production-ready marketplace capability. The next phase should **deepen proof and shrink ambiguity**, not add features that imply guarantees the backend cannot substantiate.

---

# SECTION 2 — What this repository is (and is not)

## 2.1 Active product surfaces (only these count)

| Surface | Path | Role |
|---------|------|------|
| **Backend API** | `backend/` | Authority for auth, rides, dispatch, pricing, presence, notifications, intelligence APIs |
| **Driver app** | `driver-app/` | Sole active driver UX (`driver-app/src/App.jsx`) |
| **Docs** | `docs/` | Governance, truth tables, E2E lock reports, playbooks |

**Active API mount** (`backend/main.py`): `/auth/*`, `/drivers/*`, `/rides/*` (rider), `/notifications/*`, `/v1/sil/*`, `/v1/crl/*`, `/admin/*` (subset), `/admin/crl/*`, payments/webhooks (flagged), engineering-assistant (local), internal ops routes.

**Not active product** (present but quarantined or dormant):

- `frontend/` — legacy, no current `package.json` product path  
- Dormant routers: `admin_access`, `users`, `test`, unmounted legacy `admin` modules — see `docs/DORMANT_ROUTERS_INVENTORY.md`  
- `video-gate/` — separate agent/orchestrator experiment, not driver marketplace  
- **Dossier spine** (`/supply`, `/demand`, `/trip`) — mounted only if `HALFAPP_DOSSIER_SPINE_ENABLED`; driver-app **must not** call it  

## 2.2 Classification for stakeholders

| Claim | Accurate? |
|-------|-----------|
| “Driver MVP with real backend lifecycle” | **Yes** |
| “Open-board dispatch with atomic claims” | **Yes** (first-claim-wins; honest, not geo-fair) |
| “Production Uber-scale dispatch” | **No** |
| “Live municipal traffic on the map” | **No** — fleet-estimated slow areas only |
| “Explains why the city is busy” | **Partial** — CRL v0.1 rule engine, probabilistic copy |
| “Rider app” | **No** — rider API + tests only |
| “Drivers get paid to their bank” | **No** — ledger/settlement/Stripe foundations; execution gated |
| “Road-accurate routing in production” | **Not proved** — OSRM runtime NO_GO unless self-hosted proof completed |

---

# SECTION 3 — Repository topology

```
halfapp-driver/
├── backend/                 # FastAPI, SQLAlchemy, Alembic (31 migrations)
│   ├── main.py              # Router mount truth
│   ├── routes/              # HTTP surface (drivers, auth, sil, crl, payments, …)
│   ├── services/            # Business logic (~65 modules) — the “brain” implementation
│   ├── models/              # ORM tables
│   ├── schemas/             # Pydantic views
│   ├── alembic/versions/    # 0001 → 0031
│   └── tests/               # 342 pytest cases
├── driver-app/              # React 18 + Vite 7 + Leaflet
│   ├── src/components/      # Cockpit, trips, earnings, intelligence panels
│   ├── src/hooks/           # Auth, geolocation, telemetry ping
│   ├── src/utils/           # api.js (single HTTP boundary), truth copy guards
│   └── tests/               # Unit + Playwright E2E
├── docs/                    # ~80 markdown governance & lock reports
├── scripts/                 # run_dev, verify_all, osrm_healthcheck
├── docker/osrm-portland/    # Optional OSRM compose for Portland proof
└── frontend/                # Legacy — not product
```

**Dependency direction (simplified):**

```
driver-app (api.js)
    → backend/routes/*
        → services/* (lifecycle, dispatch, pricing, sil, crl, routing, …)
            → models/* + database
```

---

# SECTION 4 — The “brain”: layered intelligence architecture

The “brain” is **not** one neural network. It is a **governed pipeline** designed so every driver-visible claim can be traced to stored signals or explicitly labeled as approximate.

## 4.1 Layer 0 — Marketplace truth (the spine everything else hangs on)

**Purpose:** Decide who owns ride state, money fields, and dispatch outcomes.

| Component | Location | What it does |
|-----------|----------|--------------|
| Lifecycle state machine | `services/lifecycle.py`, `routes/drivers.py` | Canonical transitions: requested → offered → accepted → driver_arrived → in_progress → completed / cancelled |
| Open-board dispatch | `services/dispatch.py`, claim endpoints | Multiple drivers see pool; `RideClaimAttempt` + lock prevents double-accept |
| Pricing ledger | `services/ride_pricing.py`, `models/ride_pricing.py` | Integer cents; quote on accept path; **financial lock** on complete |
| Presence | `services/presence.py`, `models/presence.py` | Online/offline, heartbeat, stale detection |
| Visibility & hide | `services/metrics.py` | Which rides were shown, dismissed, hidden |
| Idempotency | `services/driver_idempotency.py`, migration 0026 | Safe retries on driver write endpoints |

**Strength:** Backend is authoritative; UI cache is display-only for marketplace facts.  
**Weakness:** Dispatch is **not** closest-driver; exclusion reasons for non-viewing drivers are incomplete.

## 4.2 Layer 1 — Transparency & conflict proof

**Purpose:** When two drivers collide on a claim, the product can show *backend* evidence, not UI excuses.

| Component | Location |
|-----------|----------|
| Ride transparency API | `GET /drivers/rides/{id}/transparency` |
| 409 conflict memory | `MapHome.jsx`, `rideTransparency.js` |
| Marketplace ledger events | `models/ledger.py`, `services/ledger.py` |
| Dispatch logs | `models/ride_dispatch_log.py` |

## 4.3 Layer 2 — Spatial & routing truth

**Purpose:** Separate “map drawing” from “routing proof.”

| Component | Location | Status |
|-----------|----------|--------|
| Routing adapter | `services/routing_service.py` | OSRM self-hosted try → **haversine fallback** |
| OSRM provider | `services/osrm_self_hosted_provider.py` | HTTP to local OSRM |
| Runtime truth flag | `services/osrm_runtime_truth.py` | `proved_portland_v0_1` vs `not_proved` |
| Route snapshots | `services/route_snapshots.py`, migration 0010 | Persist provider, distance, duration, `used_fallback` |
| Route truth UI | `RouteTruthDetails.jsx`, `TripAuditReceipt.jsx` | Shows provider + honest OSRM status |
| Navigation bundle | `services/navigation_service.py` | External Google Maps link; **no in-app turn-by-turn** |

**Critical honesty rule:** If `used_fallback` or `haversine_fallback`, UI must **not** imply road-network accuracy.

## 4.4 Layer 3 — Street Intelligence Layer (SIL) v0.1

**Purpose:** Aggregated **where** signals — busy and slow hex cells — without external traffic API keys.

| Piece | Path |
|-------|------|
| Labels & gates | `services/sil_labels.py`, `services/sil_gates.py` |
| H3 helpers | `services/sil_h3.py` (H3 lib + grid fallback) |
| Compute | `services/sil_compute.py` — demand from open rides, supply from online drivers, congestion from telemetry speeds |
| Map API | `GET /v1/sil/map`, `GET /v1/sil/suggest` — `routes/sil.py` |
| Route quote + proof | `POST /v1/sil/route/quote`, `GET /v1/sil/proof/receipt/{id}` — `services/route_quote_service.py` |
| Tables | `sil_cell_aggregate`, `route_quotes`, `proof_receipts` (migration 0030) |
| Driver UI | `SilMapLayer.jsx`, `StreetIntelligencePanel.jsx` — Layers toggles, CSV-era trip list separate |

**SIL outputs (driver-visible when gates pass):**

- `busy_score`, `congestion_score` per H3 cell  
- Exact disclaimer strings on busy/slow layers  
- Proof level **A** (OSRM) vs **B** (straight-line) on route quotes  

**SIL does NOT:** Use TomTom/Mapbox traffic tiles; claim official demand; show other drivers’ raw GPS traces.

## 4.5 Layer 4 — City Reality Layer (CRL) v0.1

**Purpose:** Aggregated **why** — cause attribution on top of the same signals SIL uses, plus zone catalog and optional operator events.

| Piece | Path |
|-------|------|
| Cause codes & copy | `services/crl_causes.py`, `services/crl_labels.py` |
| Zone seeds (Portland) | `services/crl_zones.py` — airport, union station, downtown, nightlife |
| Time baselines | `models/crl_time_pattern.py`, updated in `crl_compute.py` |
| Attribution engine | `services/crl_attribution.py` — parallel rule detectors (commute, hub flow, shortage, cancel friction, events, pickup/dropoff imbalance) |
| Snapshots | `models/crl_cell_snapshot.py` — demand, pickups, dropoffs, cancel rate, wait, supply ratio |
| Explanations | `models/crl_cell_explanation.py` — primary/secondary cause, `signals_used` JSON (admin/explain endpoint; **not** full dump on map list) |
| Driver API | `GET /v1/crl/map`, `GET /v1/crl/explain?h3=` — `routes/crl.py` |
| Admin API | `GET /admin/crl/overview`, `POST /admin/crl/events` — `routes/admin_crl.py` |
| Driver UI | `CityRealityPanel.jsx` — “Why?” in cockpit; tap cell for explain |

**CRL honesty rules (coded):**

- Wording uses **“likely”**, **“possible”**, **“based on patterns”** — never “confirmed due to X”  
- Gate G1: unqualified “live traffic” forbidden in SIL copy linter tests  
- Low activity → `NOT_ENOUGH_DATA_LABEL`  
- Map list omits raw `demand_count`, `driver_id`, per-driver counts  

**CRL does NOT (v0.1):** ML demand forecasting; weather API; encrypted PII ride_request_event table; segment-level OSRM match; rider app integration.

## 4.6 Layer 5 — Fleet telemetry (feeds SIL/CRL)

| Piece | Path |
|-------|------|
| Table | `driver_telemetry_points` (migration 0029) |
| Ingest | `POST /drivers/me/telemetry` |
| Client | `useTelemetryPing.js` — 5s while online, speed from GPS or movement-derived |
| Legacy heat | `GET /drivers/me/traffic-heatmap` — superseded for map by SIL/CRL in UI |

**Honest label:** “Fleet-estimated slow areas … **Not official live traffic.**”

---

# SECTION 5 — Backend: services map (the implementation brain)

Below is a functional grouping of `backend/services/` (~65 files). This is how an expert should navigate the codebase.

## 5.1 Core marketplace

| Service | Responsibility |
|---------|----------------|
| `lifecycle.py` | Status enum, transitions, guards |
| `dispatch.py` | Policies, ordering, offer exposure |
| `ride_dispatch_cascade.py` | Sequential offer timeout (RIDE-003) |
| `claim_eligibility.py` | Who may claim |
| `presence.py` | Heartbeat, stale, effective state |
| `driver_status_service.py` | Online/offline sync |
| `driver_approval.py` | Approval gate for going online |
| `metrics.py` | Visibility, claim attempts, insights |
| `transparency.py` | Conflict / transparency payloads |

## 5.2 Money & pricing (foundation, not full PSP product)

| Service | Responsibility |
|---------|----------------|
| `ride_pricing.py` | Per-ride integer cent ledger |
| `pricing_service.py` / `pricing_policy_loader.py` | Policy versions |
| `ride_settlement.py` | Settlement obligation **rows** |
| `payment_execution.py` | Execution records (flagged) |
| `stripe_connect.py`, `stripe_*` | Connect/transfers/payout ingest |
| `payment_events.py`, `payment_reconciliation.py` | Webhook-side bookkeeping |

**Truth:** Earnings API summarizes completed rides; **bank payout UX is not product-complete.**

## 5.3 Spatial

| Service | Responsibility |
|---------|----------------|
| `routing_service.py` | Provider selection + fallback |
| `osrm_self_hosted_provider.py` | OSRM HTTP |
| `osrm_runtime_truth.py` | Proof artifact for Portland |
| `route_snapshots.py` / `route_snapshots_read.py` | Persist & read snapshots |
| `map_route_foundation.py` | Ride map metadata fields |
| `navigation_service.py` | External nav URL bundle |
| `traffic_signals_service.py` | Optional regional signals (not live traffic) |

## 5.4 Intelligence (SIL + CRL)

| Service | Responsibility |
|---------|----------------|
| `sil_compute.py`, `sil_map.py`, `sil_gates.py`, `sil_labels.py` | Street intelligence |
| `crl_compute.py`, `crl_map.py`, `crl_attribution.py`, `crl_zones.py` | City reality |
| `fleet_traffic_heatmap.py` | Legacy point heat (pre-H3) |
| `driver_trips.py` | Trip list filters + export |
| `route_quote_service.py` | Quotes + SHA-256 proof receipts |

## 5.5 Driver product & comms

| Service | Responsibility |
|---------|----------------|
| `driver_profile_service.py`, `driver_app_settings_service.py` | Profile & prefs |
| `driver_in_app_notifications.py` | Notification rows on lifecycle |
| `ride_messages_service.py` | Per-ride chat storage (driver UI; rider delivery N/A) |
| `password_reset.py` | Forgot/reset password |
| `driver_idempotency.py` | Replay protection |

## 5.6 Platform

| Service | Responsibility |
|---------|----------------|
| `auth.py`, `refresh_tokens.py`, `rbac.py` | JWT, roles, refresh rotation |
| `rate_limit.py` | Auth rate limits |
| `datetime_utils.py` | Naive UTC alignment |
| `engineering_assistant.py` | Local-only diagnostic shell |

---

# SECTION 6 — Backend: HTTP surface (driver-relevant)

`backend/routes/drivers.py` is the largest router (~46 route handlers). Grouped by product area:

## 6.1 Auth & session (`routes/auth.py`)

- Register, login, refresh, logout-all, forgot/reset password, change password  
- Migration 0027 `password_reset_tokens`; 0016 refresh tokens  

## 6.2 Presence & status

- `GET/PATCH /drivers/me/status`, `PATCH /drivers/me/location`  
- `POST /drivers/heartbeat`  
- Approval gate enforced before online  

## 6.3 Dispatch & lifecycle

- `GET /drivers/available-rides`  
- Accept, decline, dispatch-decline, arrive, start, complete  
- Hide/dismiss ride  
- Simulate ride (env-guarded)  

## 6.4 Trips & earnings

- `GET /drivers/my-rides` (legacy list)  
- `GET /drivers/me/trips` (paginated + filters)  
- `GET /drivers/me/trips/export.csv`, `/drivers/my-rides/export`  
- `GET /drivers/earnings`, insights, performance  

## 6.5 Audit & transparency

- `GET /drivers/rides/{id}/audit`  
- `GET /drivers/rides/{id}/transparency`  
- `GET /drivers/rides/{id}/route-snapshots`  
- `GET /drivers/rides/{id}/settlement`  
- `POST /drivers/rides/{id}/support-ticket`  

## 6.6 Comms

- `GET/POST /drivers/rides/{id}/messages`  
- Notifications via `routes/notifications.py`  

## 6.7 Intelligence & telemetry

- `POST /drivers/me/telemetry`  
- `GET /drivers/me/traffic-heatmap`  
- `GET /v1/sil/map`, `/v1/sil/suggest`, `POST /v1/sil/route/quote`, `GET /v1/sil/proof/receipt/{id}`  
- `GET /v1/crl/map`, `GET /v1/crl/explain`  

## 6.8 Admin (operator)

- `routes/admin_driver_approval.py` — driver approval, ride notes  
- `routes/admin_crl.py` — CRL overview, create `city_events`  

---

# SECTION 7 — Data model & migrations (schema brain)

**Alembic chain:** `0001` … `0031_crl_foundation` (31 revisions).

| Migration era | Themes |
|---------------|--------|
| 0001–0004 | Hardened schema, lifecycle contract, presence, indexes |
| 0005–0006 | Marketplace ledger events, dossier foundation (parallel) |
| 0007–0011 | v0.1 pricing, map fields, route snapshots, settlement |
| 0012–0016 | Driver approval, status, dispatch cascade, refresh tokens |
| 0017–0023 | Payment execution, Stripe accounts, transfers, payouts |
| 0024–0028 | Driver profile, settings, idempotency, password reset, ride messages, support tickets |
| 0029–0031 | Telemetry, SIL, CRL |

**Core ride table (`models/ride.py`):** Customer, driver, status, pickup/destination labels, lat/lng, `distance` (km), `duration` (minutes), `fare_amount`, lifecycle timestamps, dispatch fields, map provider metadata.

**Intelligence tables:**

| Table | Role |
|-------|------|
| `driver_telemetry_points` | Raw fleet GPS samples (restricted; aggregated for heat) |
| `sil_cell_aggregate` | Busy/slow scores per H3 per bucket |
| `route_quotes` / `proof_receipts` | Route method + tamper-evident hash |
| `crl_cell_snapshot` | Demand/supply/wait/cancel aggregates |
| `crl_cell_explanation` | Cause attribution output |
| `crl_time_pattern` | Hour/dow baselines |
| `zone_catalog` | Airport, office, nightlife seeds |
| `city_events` | Operator-defined events |

**Privacy model (coded intent):**

- Raw telemetry stored for aggregation; **driver map APIs do not return other drivers’ points**  
- CRL map cells return scores + human labels, not underlying counts (tests enforce no `demand_count` in driver JSON)  

---

# SECTION 8 — Frontend driver app

## 8.1 Route tree (`App.jsx`)

| Route | Component | Role |
|-------|-----------|------|
| `/` | `HalfAppDriverPortalFrontPage` | Login/register/forgot password |
| `/driver` | `MapHome` | **Primary cockpit** — map, offers, lifecycle |
| `/driver/trips` | `TripsList` | Paginated trips, filters, CSV export |
| `/driver/trips/:id/audit` | `TripAuditReceipt` | Receipt + pricing + route truth |
| `/driver/earnings` | `Earnings` | Summary + chart component |
| `/driver/notifications` | `Notifications` | In-app inbox |
| `/driver/profile` | `Profile` | Driver profile |
| `/driver/settings` | `DriverSettings` | Theme, units, quiet hours, locale, logout-all |

## 8.2 Cockpit architecture (`MapHome.jsx`)

**State sources:**

- `useAuth` — JWT  
- `useDriverGeolocation` — device GPS (**map/experimental**; telemetry uses it when online)  
- `useTelemetryPing` — posts `/drivers/me/telemetry` every 5s while online  
- `refreshBackendTruth` — polls me status, available rides, my rides, earnings  
- `DriverPreferencesContext` — theme, units, unread badge  

**Map stack:**

- `MapView.jsx` — Leaflet + OSM tiles (`mapProvider.js`)  
- `SilMapLayer.jsx` — busy/slow heat from `/v1/sil/map`  
- `StreetIntelligencePanel` — layer toggles, route preview quote  
- `CityRealityPanel` — CRL explanations (“Why?”)  
- `MarketplaceBottomSheet` — offer card, lifecycle actions, chat, navigation panel  

**Truth UX:**

- `BetaTruthNotice`, `betaTruthCopy.js` guards — CI `assert-no-money-claims`  
- Approval gate, stale presence banner, network degraded banner  
- Conflict transparency on 409 claim collision  

## 8.3 API boundary (`driver-app/src/utils/api.js`)

**Single choke point** for HTTP. Must use `/drivers/*` + `/auth/*` only (not dossier).

Notable methods added in product completion / intelligence work:

- `getDriverTrips`, `exportMyRidesCsv`  
- `postDriverTelemetry`, `getFleetTrafficHeatmap`  
- `getSilMap`, `createSilRouteQuote`, `getSilProofReceipt`  
- `getCrlMap`, `getCrlExplain`  

**Mock mode:** `ALLOW_OFFLINE_MOCK` — dev only; production builds use `assert-prod-truth.mjs`.

---

# SECTION 9 — Testing & quality gates

## 9.1 Backend (342 tests)

Representative lanes:

| Area | Example tests |
|------|----------------|
| Lifecycle | `test_ride_lifecycle.py`, `test_ride_001_transition_guards.py` |
| Claim lock | `test_ride_claim_lock_concurrency.py` |
| Pricing | `test_pricing_ledger_v01.py` |
| Auth/RBAC | `test_auth_jwt_middleware.py`, `test_rbac.py` |
| OSRM | `test_osrm_self_hosted_routing.py` (mocked), `test_osrm_runtime_proof_portland.py` (live skip) |
| SIL/CRL | `test_sil_v01.py`, `test_crl_v01.py`, `test_fleet_traffic_telemetry.py` |
| Gap-fill | `test_driver_gap_fill_slice06.py`, `test_driver_gap_fill_extended.py` |
| Route surface freeze | `test_active_route_surface.py` |

## 9.2 Driver app

- **Unit:** 124+ tests (`node --test tests/unit/**/*.test.js`)  
- **Guards:** `assert-no-ai-providers.mjs`, `assert-no-money-claims.mjs`  
- **E2E:** `playwright.ride-flow.config.js`, `playwright.audit-flow.config.js`, `playwright.route-truth-flow.config.js`, cockpit smoke specs  

## 9.3 What tests prove vs do not prove

| Proved in CI | Not proved in default CI |
|--------------|---------------------------|
| Lifecycle & claim correctness (SQLite) | Postgres claim race at scale |
| Pricing lock semantics | Real money movement |
| Honesty copy guards | OSRM live runtime (optional env flag) |
| SIL/CRL label & privacy gates | Multi-city zone catalog accuracy |
| Ride-flow UI harness | Native mobile drivers |

---

# SECTION 10 — Strengths (detailed)

## 10.1 Architectural strengths

1. **Backend authority** — Ride state and pricing lock are server-side; the app does not “complete” trips locally.  
2. **Honest dispatch story** — Open board + claim lock + transparency; no false “nearest driver” narrative unless copy violates guards.  
3. **Integer-cent pricing** — `ride_pricing` reduces float drift; audit UI can show locked financial snapshot.  
4. **Alembic discipline** — 31 migrations; models registered in `main.py`; v0.1 foundation is real.  
5. **Intelligence with gates** — SIL/CRL implement k-thresholds, confidence floors, and fixed disclaimer strings — rare in MVPs.  
6. **Proof receipts** — Route quotes carry SHA-256 payloads — foundation for audit/disputes.  
7. **Test depth** — 342 backend + unit guards + multiple E2E locks document product truth.  
8. **Documentation culture** — `CURRENT_TRUTH.md`, playbooks, per-slice GO reports reduce agent/human drift.  
9. **Provider abstraction** — `routing_service.py` allows OSRM without rewriting cockpit.  
10. **Separation of map vs truth** — Geolocation hook labeled experimental; routing proof separate from tiles.

## 10.2 Product strengths (driver-facing)

- Map-first cockpit with real offer → complete loop  
- Trip audit receipt as trust anchor  
- Trips filters + CSV export for operator review  
- Settings: theme, units, quiet hours, sign-out-all-devices  
- Password reset flow  
- In-app notifications on key lifecycle transitions  
- Street Intelligence + City Reality panels educate without claiming official traffic  

---

# SECTION 11 — Weaknesses & risks (detailed)

## 11.1 Product & positioning risks

1. **Visual intelligence ≠ verified city knowledge** — Heatmaps can look like Waze; disclaimers help but UX literacy varies.  
2. **CRL v0.1 is rule-based** — Causes can be wrong; “uncertain_pattern” must appear often in sparse data.  
3. **Single-region zone seeds** — Portland-centric `zone_catalog`; other cities need ops work.  
4. **No rider product** — Half marketplace; demand signals only from test/API rides.  
5. **Web-only driver** — No native background location, push, or App Store lifecycle.

## 11.2 Technical weaknesses

1. **SQLite vs Postgres** — Claim tests on SQLite; production locking differs (`test_postgres_claim_race_proof` not default CI).  
2. **OSRM runtime NO_GO** — Default path often haversine; road distance claims must stay gated.  
3. **Compute-on-read** — SIL/CRL recompute on map fetch — fine for dev, needs cron/worker at scale.  
4. **No WebSocket presence** — 30s heartbeat + polling; stale states possible.  
5. **Dossier parallel spine** — Confusion risk for new engineers/agents.  
6. **Repository sprawl** — Legacy folders look like product.  
7. **Telemetry volume** — Unbounded `driver_telemetry_points` without retention policy.  
8. **H3 optional fallback** — Grid fallback if `h3` import fails — cells won’t match Uber H3 tooling.  

## 11.3 Security & compliance gaps

- Refresh tokens exist; full revocation story depends on config  
- CORS production partial — explicit origins required  
- No structured audit log export for SOC2-style review  
- PII in rides (`customer_name`) — no encryption layer described for CRL raw-event design  
- Payment webhooks — powerful; must stay flag-guarded  

## 11.4 Organizational / process weaknesses

- **Doc drift** — Multiple “comprehensive” reports; `CURRENT_TRUTH` must stay synced after each slice  
- **No CI lint for marketing superlatives** — `assert-no-money-claims` covers driver-app src only  
- **M365 / external knowledge** — No internal Street Intelligence spec in tenant; architecture lives in repo docs only  

---

# SECTION 12 — Inventory: what exists vs what does not

## 12.1 Marketplace & operations

| Capability | Status | Notes |
|------------|--------|-------|
| Driver JWT auth | **GO** | |
| Refresh token rotation | **GO** | migration 0016 |
| Driver approval gate | **GO** | |
| Open-board dispatch | **GO** | |
| Atomic claim lock | **GO** | SQLite-proved |
| Sequential dispatch cascade | **GO** | flag-gated |
| Rider create/cancel API | **GO** | no rider UI |
| Rider app | **NO** | |
| WebSocket dispatch | **NO** | |
| Closest-driver dispatch | **NO** | honest omission |
| Full admin OS | **PARTIAL** | approval + CRL events |
| Native driver app | **NO** | |

## 12.2 Money

| Capability | Status | Notes |
|------------|--------|-------|
| Integer-cent `ride_pricing` | **GO** | |
| Financial lock on complete | **GO** | |
| Settlement obligation rows | **GO** | not payout execution |
| Stripe schema + webhooks | **PARTIAL** | flagged |
| Driver bank payout UX | **NO** | honest boundary |
| Tax/tolls/adjustments | **NO** | |

## 12.3 Spatial

| Capability | Status | Notes |
|------------|--------|-------|
| Store pickup/dropoff coords | **GO** | |
| Route snapshots | **FOUNDATION** | |
| OSRM code path | **GO** | mocked tests |
| OSRM production runtime | **NO_GO** | see `SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` |
| In-app turn-by-turn | **NO** | external URL only |
| Geocoding service | **NO** | coords supplied |
| Municipal live traffic | **NO** | fleet heat only |

## 12.4 Intelligence “brain”

| Capability | Status | Notes |
|------------|--------|-------|
| Fleet telemetry ingest | **GO** | |
| SIL map (busy/slow) | **GO** | v0.1 |
| SIL route quote + proof | **GO** | |
| CRL cause attribution | **GO** | rules v0.1 |
| CRL explain API | **GO** | |
| Operator city events | **GO** | admin POST |
| ML demand forecast | **NO** | |
| Weather integration | **NO** | |
| `ride_request_event` encrypted raw | **NO** | uses `rides` table |
| Segment-level congestion | **NO** | H3 only |
| Baseline learning by season | **PARTIAL** | hour/dow table only |

## 12.5 Driver product surfaces

| Surface | Status |
|---------|--------|
| Cockpit map + lifecycle | **GO** |
| Trip audit | **GO** |
| Trips paginated + CSV | **GO** |
| Earnings + chart | **GO** |
| Notifications + badge | **GO** |
| Settings (theme/units/quiet hours) | **GO** |
| Profile | **PARTIAL** |
| Ride chat UI | **GO** storage only |
| Web push | **NO** |
| Stripe Connect onboarding in app | **NO** |

---

# SECTION 13 — Environment & feature flags (operational brain)

| Variable | Effect |
|----------|--------|
| `ROUTING_PROVIDER` | `osrm_self_hosted` vs `haversine_fallback` |
| `ROUTING_FALLBACK_ENABLED` | Allow haversine when OSRM down |
| `HALFAPP_OSRM_RUNTIME_PROOF` | Live Portland OSRM proof tests |
| `HALFAPP_DOSSIER_SPINE_ENABLED` | Mount dossier routes |
| `HALFAPP_OPEN_BOARD_DISPATCH` | Open board mode |
| `VITE_ENABLE_RIDE_SIMULATION` | Dev simulation ride |
| `ALLOW_OFFLINE_MOCK` / mock banners | Offline dev only |
| `SIL_MIN_*` / `SIL_MIN_CONF` | Intelligence gate thresholds |
| `PAYOUTS_ENABLED` | Payments visibility |
| `SECRET_KEY` | Production guard in `production_guards.py` |

**Local run:** `docs/RUN_LOCAL.md`, `scripts/run_dev.ps1` — backend **8000**, driver-app **3022**.

---

# SECTION 14 — Documentation corpus (governance brain)

The repo carries **~80** docs. Tier them mentally:

| Tier | Examples | Use when |
|------|----------|----------|
| **Truth** | `CURRENT_TRUTH.md`, `PRODUCT_BOUNDARY_STAGE0.md`, `RIDE_LIFECYCLE_CONTRACT.md` | Daily engineering |
| **Playbooks** | `HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01.md` | Prioritization |
| **Lock reports** | `*_E2E_LOCK_*`, `*_GO.md` | Proof a slice shipped |
| **Comprehensive** | `HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md`, `HALFAPP_DRIVER_PROGRAM_MASTER_REPORT_01.md` | Deep dives |
| **This report** | `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01.md` | Next-step planning |

**Anti-pattern:** Treating every markdown file as current — check date + `CURRENT_TRUTH` first.

---

# SECTION 15 — Recommended next steps (phased)

## Phase A — Prove production spine (2–4 weeks)

1. **OSRM runtime GO** — Portland Docker proof → flip `osrm_runtime_claim` → update route truth copy.  
2. **Postgres CI** — Run claim-race + migration tests on PostgreSQL in CI.  
3. **Telemetry retention** — Partition or purge `driver_telemetry_points` > N days.  
4. **SIL/CRL worker** — `POST /internal/sil/compute_bucket` + cron; stop full recompute on every map pan.

## Phase B — Deepen the brain without ML (3–6 weeks)

1. **CRL v0.2** — Segment aggregates after OSRM **match** on telemetry traces.  
2. **Zone catalog ops UI** — Admin draw/import zones per city.  
3. **Suggested positioning** — Wire `GET /v1/sil/suggest` + CRL targets in cockpit (honest “consider driving toward…” copy).  
4. **Baseline refinement** — Rolling 14-day `crl_time_pattern` recompute job.  
5. **Map ↔ explain linking** — Tap hex on map → `GET /v1/crl/explain` (today: list panel only).

## Phase C — Product completion before external drivers (parallel)

1. Profile/settings consolidation  
2. Notifications product polish (mark-read, chrome)  
3. Rider message delivery contract (if rider app planned)  
4. Vehicle docs self-service (if compliance needed)  

## Phase D — Strategic forks (decision required)

| Fork | Question |
|------|----------|
| **Dossier** | Wire `/supply`/`/demand` or delete from `main.py` |
| **Payments** | Hard NO-GO lock vs Stripe pilot with legal review |
| **Rider app** | Build vs partner API-only |
| **Native driver** | Capacitor/React Native vs stay PWA |

---

# SECTION 16 — Appendix A: intelligence request/response shapes

## A.1 `GET /v1/sil/map`

Returns: `bucket_start_ts`, `disclaimer`, `labels.busy`, `labels.slow`, `cells[]` with `busy_score` / `congestion_score`, `not_enough_data_areas[]`.

## A.2 `GET /v1/crl/map`

Returns: `cells[]` with `primary_cause`, `label` (full honest sentence), `confidence`, `demand_score`, `wait_score` — **no raw counts**.

## A.3 `GET /v1/crl/explain?h3=`

Returns: `signals_used` object, `primary_cause`, `label` — for drill-down.

## A.4 `POST /v1/sil/route/quote`

Body: `{ from_lat, from_lng, to_lat, to_lng }`  
Returns: `route_method`, `proof_level`, `label`, `eta_honesty`, `proof_receipt_id`.

---

# SECTION 17 — Appendix B: key files quick reference

| Concern | File |
|---------|------|
| App entry | `backend/main.py`, `driver-app/src/App.jsx` |
| Lifecycle | `backend/services/lifecycle.py` |
| Dispatch | `backend/services/dispatch.py` |
| Pricing | `backend/services/ride_pricing.py` |
| Routing | `backend/services/routing_service.py` |
| SIL compute | `backend/services/sil_compute.py` |
| CRL attribution | `backend/services/crl_attribution.py` |
| Driver routes | `backend/routes/drivers.py` |
| HTTP client | `driver-app/src/utils/api.js` |
| Cockpit | `driver-app/src/components/MapHome.jsx` |
| Truth copy guards | `driver-app/src/utils/betaTruthCopy.js` |
| Migrations | `backend/alembic/versions/` |

---

# SECTION 18 — Closing assessment for advanced readers

HalfApp Driver has evolved from a **lifecycle MVP** into a **small but real marketplace kernel** with an emerging **explainable intelligence stack**. The “brain” is deliberately **modular and honest**: each layer admits what it does not know (fallback routing, fleet-not-municipal traffic, rule-based causes, k-gated aggregates).

**The program’s greatest asset** is not the map — it is the **discipline of backend-owned truth** plus tests and copy guards that resist demo drift.

**The program’s greatest liability** is **interpretation risk**: stakeholders seeing heatmaps, earnings dollars, and Stripe tables may assume production completeness. This report and `CURRENT_TRUTH.md` exist to prevent that leap.

**The right next step** is not “more features.” It is **(1)** prove OSRM + Postgres production paths, **(2)** operationalize intelligence compute, **(3)** decide dossier/payments/rider forks, then **(4)** expand CRL from rules to road-matched segments while keeping probabilistic language immutable.

---

*End of report. For updates after new slices, append a changelog section or bump document ID to `_02`.*
