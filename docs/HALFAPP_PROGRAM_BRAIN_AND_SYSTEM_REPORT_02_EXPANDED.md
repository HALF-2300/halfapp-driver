# HalfApp Driver Program — System Brain & Comprehensive Technical Report (Expanded Edition)

**Document ID:** `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_02_EXPANDED`  
**Date:** 2026-05-23  
**Audience:** Program owner, senior engineers, architects, investors, external partners  
**Supersedes narrative depth:** `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01.md` (concise edition — still valid for quick reference)  
**Workspace:** `c:\Users\him\Desktop\halfapp-driver`  
**Alembic head:** `0031_crl_foundation` · **Backend tests:** 342 collected · **Driver unit tests:** 124+  

---

## Which document to open

| Your goal | Open this file |
|-----------|----------------|
| **What is left to build (daily checklist)** | `HALFAPP_COMPLETION_MASTER_CHECKLIST_01.md` |
| **Quick scannable architecture** | `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01.md` |
| **Deep narrative + investor/partner depth (this file)** | `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_02_EXPANDED.md` |
| **Vendor questions & ROM** | `HALFAPP_EXTERNAL_PARTNER_COMPLETION_DISCOVERY_01.md` |
| **GO/NO-GO proof table** | `CURRENT_TRUTH.md` |

> **Important:** Section 15 below includes **recommended** production techniques (PostgreSQL `SKIP LOCKED`, `pg_partman`, `arq` workers, OSRM Match, admin map drawing). These are **not all implemented in the repo today** — they are the engineering target for Phase A/B. Shipped code is described in Sections 1–12; recommendations are labeled explicitly.

---

# SECTION 1 — Executive summary

HalfApp Driver is a **backend-authoritative driver ride-hailing MVP**: FastAPI + SQLAlchemy backend, React + Vite driver web app. It is **not** a full two-sided marketplace, **not** a production payments platform, and **not** municipal traffic or demand forecasting — though it includes **foundational city intelligence** (SIL + CRL) with strict honesty gates.

**What works today:** Register/login (JWT), approval gate, go online, open-board offers, atomic claim, full lifecycle (accept → complete), earnings and trip audit (integer-cent pricing), trip filters + CSV export, in-app notifications, map cockpit with fleet slow zones and cause-labeled activity explanations.

**The “brain”** is a **stack of truth layers**, not one ML model:

| Layer | Name | Role |
|-------|------|------|
| 0 | Marketplace spine | Lifecycle, dispatch, claim lock, pricing ledger |
| 1 | Transparency | Visibility, claim attempts, 409 conflict proof |
| 2 | Spatial truth | OSRM adapter + haversine fallback, route snapshots |
| 3 | SIL | H3 busy/slow aggregates, route quotes, proof receipts |
| 4 | CRL | Rule-based “why” attribution (commute, hub, shortage, events) |
| 5 | Fleet telemetry | GPS speed samples → slow-zone heat (no TomTom/Mapbox) |

**Strategic verdict:** The program crossed from demo UI to a **narrow, auditable product spine**. The main risk is **over-reading** maps, intelligence overlays, or payment schema as production-ready marketplace capability. Next phase: **deepen proof, reduce ambiguity** — not add features that imply guarantees the backend cannot substantiate.

---

# SECTION 2 — What this repository is (and is not)

## Active surfaces only

| Surface | Path |
|---------|------|
| Backend API | `backend/` |
| Driver app | `driver-app/` |
| Docs | `docs/` |

**Mounted APIs:** `/auth/*`, `/drivers/*`, `/rides/*` (rider API), `/notifications/*`, `/v1/sil/*`, `/v1/crl/*`, `/admin/*`, `/admin/crl/*`, payments/webhooks (flagged).

**Not product:** `frontend/` (legacy), dormant routers, `video-gate/`, dossier `/supply|/demand|/trip` unless `HALFAPP_DOSSIER_SPINE_ENABLED` (driver app must not call dossier).

## Stakeholder claims

| Claim | Accurate? |
|-------|-----------|
| Driver MVP with real backend lifecycle | **Yes** |
| Open-board dispatch + atomic claims | **Yes** (honest, not geo-fair) |
| Production Uber-scale dispatch | **No** |
| Live municipal traffic on map | **No** (fleet-estimated only) |
| Explains why city is busy | **Partial** (CRL v0.1 rules + probabilistic copy) |
| Rider app | **No** |
| Drivers paid to bank | **No** (ledger/Stripe foundations; execution gated) |
| Road-accurate routing in production | **Not proved** (OSRM runtime NO_GO) |

---

# SECTION 3 — Repository topology

```
halfapp-driver/
├── backend/          # FastAPI, ~65 services, 31 Alembic migrations
├── driver-app/       # React 18, Vite 7, Leaflet
├── docs/             # Governance (~80 files)
├── scripts/          # run_dev, verify_all, osrm_healthcheck
├── docker/osrm-portland/
└── frontend/         # Legacy — not product
```

**Dependency flow:** `driver-app` → `api.js` → `backend/routes/*` → `services/*` → `models/*` → database.

---

# SECTION 4 — The “brain”: layered intelligence

*(Full layer descriptions match `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01.md` Sections 4.1–4.6.)*

**Honesty rules (non-negotiable):**

- No “live traffic” without fleet-estimated qualifier  
- No road-accurate claims when `used_fallback` / haversine  
- No map shading without k-anonymity / confidence gates  
- CRL copy uses “likely”, “possible”, “based on patterns” — never “confirmed due to X”  

**Key code paths:**

| Layer | Primary modules |
|-------|-----------------|
| Marketplace | `lifecycle.py`, `dispatch.py`, `ride_pricing.py`, `presence.py` |
| Transparency | `transparency.py`, `ledger.py`, `ride_dispatch_log.py` |
| Spatial | `routing_service.py`, `route_snapshots.py`, `osrm_runtime_truth.py` |
| SIL | `sil_compute.py`, `sil_map.py`, `sil_gates.py`, `route_quote_service.py` |
| CRL | `crl_compute.py`, `crl_attribution.py`, `crl_zones.py`, `crl_map.py` |
| Telemetry | `driver_telemetry_point` model, `useTelemetryPing.js`, `fleet_traffic_heatmap.py` |

---

# SECTIONS 5–12 — Implementation inventory

For **services map**, **HTTP surface**, **schema/migrations**, **frontend routes**, **testing**, **strengths**, **weaknesses**, and **exists vs not** tables, see:

- **Concise tables:** `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01.md` Sections 5–12  
- **Completion gaps:** `HALFAPP_COMPLETION_MASTER_CHECKLIST_01.md` Sections 2–6  

This expanded edition adds **technical depth in Section 15** below rather than duplicating every table.

---

# SECTION 13 — Environment & feature flags

| Variable | Effect |
|----------|--------|
| `ROUTING_PROVIDER` | `osrm_self_hosted` vs `haversine_fallback` |
| `ROUTING_FALLBACK_ENABLED` | Allow haversine when OSRM down |
| `HALFAPP_OSRM_RUNTIME_PROOF` | Live Portland OSRM tests |
| `HALFAPP_DOSSIER_SPINE_ENABLED` | Mount dossier routes |
| `HALFAPP_OPEN_BOARD_DISPATCH` | Open board mode |
| `VITE_ENABLE_RIDE_SIMULATION` | Dev simulation ride |
| `SIL_MIN_*` / `SIL_MIN_CONF` | Intelligence gate thresholds |
| `PAYOUTS_ENABLED` | Payments visibility |
| `SECRET_KEY` | Production crypto guard |

**Local run:** `docs/RUN_LOCAL.md` — backend **8000**, driver-app **3022**.

---

# SECTION 14 — Documentation corpus

| Tier | Examples |
|------|----------|
| **Daily** | `HALFAPP_COMPLETION_MASTER_CHECKLIST_01.md`, `CURRENT_TRUTH.md` |
| **Architecture** | `_01` concise, `_02` this file |
| **Vendor** | `HALFAPP_EXTERNAL_PARTNER_COMPLETION_DISCOVERY_01.md` |
| **Playbooks** | `HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01.md` |

**Anti-pattern:** Treating every markdown file as current — check date + `CURRENT_TRUTH.md`.

---

# SECTION 15 — Recommended next steps (phased, with engineering detail)

> **Status:** Recommendations for Phase A/B. **Not all implemented in repo.**

## Phase A — Prove production spine (2–4 weeks)

### A1. OSRM runtime GO

- Deploy self-hosted OSRM for Portland (see `docker/osrm-portland/`).
- Pipeline: `osrm-extract` → `osrm-partition` → `osrm-customize` on regional `.osm.pbf` (Geofabrik).
- **Ops note:** Full-region graphs can require very large RAM; size container/host accordingly.
- Pass `HALFAPP_OSRM_RUNTIME_PROOF=1` tests; flip `osrm_runtime_claim` when honest.
- **References:** [OSRM Docker deployment guides](https://github.com/Project-OSRM/osrm-backend), project docs `SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md`.

### A2. PostgreSQL + claim concurrency

- Move production and CI claim-race tests to **PostgreSQL** (not SQLite-only).
- **Today:** Active dispatch uses `SELECT … FOR UPDATE` in `services/dispatch.py`; dossier spine uses `SKIP LOCKED` in `services/dossier_dispatch.py` only.
- **Recommended evaluate:** `SELECT … FOR UPDATE SKIP LOCKED` for open-board claim under high concurrency so losing threads get fast 409s instead of blocking (PostgreSQL MVCC behavior differs from SQLite file locking).
- Run and document `test_postgres_claim_race_proof` in CI matrix.

### A3. Telemetry retention

- **Today:** `driver_telemetry_points` grows unbounded.
- **Recommended:** Daily partitions + retention (e.g. 14–30 days) via `pg_partman` or equivalent purge job.
- **References:** [pg_partman](https://github.com/pgpartman/pg_partman), [Crunchy Data retention guide](https://www.crunchydata.com/blog/auto-archiving-and-data-retention-management-in-postgres-with-pg_partman).

### A4. SIL/CRL background workers

- **Today:** Aggregates often recompute on map API read.
- **Recommended:** Redis-backed worker queue (e.g. **arq**) or cron hitting `POST /internal/sil/compute_bucket` every 5 minutes.
- Avoid relying on FastAPI `BackgroundTasks` alone for heavy grid jobs at scale.
- **References:** [FastAPI background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/), [arq](https://arq-docs.helpmanual.io/).

### A5. Production deploy + observability

- Staging + prod: API, PG, static driver-app CDN, OSRM, secrets, CORS lock.
- Logs, request IDs, error tracking, 5–10 alerts (claim failures, OSRM down, heartbeat stale rate).

---

## Phase B — Deepen the brain without ML (3–6 weeks)

### B1. CRL v0.2 — road segments via OSRM Match

- Use OSRM **Match** API (`/match/v1/car/`) to snap telemetry traces to road geometry.
- Payload: `{longitude},{latitude}` + timestamps; consider `gaps=split`, `tidy=true` for fragmented GPS.
- Enables segment-level slow areas, not only H3 cells.
- **References:** [OSRM Match API](http://project-osrm.org/docs/v5.24.0/api/), [match service usage](https://stackoverflow.com/questions/50698754/how-to-use-osrms-match-service).

### B2. Zone catalog ops UI

- **Today:** Portland seeds in `crl_zones.py`.
- **Recommended:** Admin UI to draw/import zones (e.g. Leaflet + GeoJSON export → `zone_catalog`).
- Options: `react-leaflet-geoman`, Leaflet.draw, or CSV import of H3 lists.

### B3. Product wiring (honest copy)

- Wire `GET /v1/sil/suggest` + CRL targets in cockpit (“consider driving toward…”).
- Map tap → `GET /v1/crl/explain` (today: list panel in `CityRealityPanel.jsx`).
- Nightly `crl_time_pattern` rollup via worker.

---

## Phase C — Driver product completion (parallel)

See **`HALFAPP_COMPLETION_MASTER_CHECKLIST_01.md` Section 3** (P1-7 through P1-23): session recovery, notifications polish, geocoding, admin minimum, etc.

---

## Phase D — Strategic forks (decision required)

| Fork | Question |
|------|----------|
| Dossier | Wire `/supply`/`/demand` or delete from `main.py` |
| Payments | Calculation-only vs Stripe pilot vs hard NO-GO |
| Rider app | Build vs partner API-only |
| Native driver | PWA vs Capacitor/React Native |

---

# SECTION 16 — Appendix: intelligence API shapes

Same as `_01` Section 16: `/v1/sil/map`, `/v1/crl/map`, `/v1/crl/explain?h3=`, `POST /v1/sil/route/quote`.

---

# SECTION 17 — Appendix: key files

Same as `_01` Section 17: `main.py`, `lifecycle.py`, `dispatch.py`, `routing_service.py`, `sil_compute.py`, `crl_attribution.py`, `drivers.py`, `api.js`, `MapHome.jsx`, `betaTruthCopy.js`, `alembic/versions/`.

---

# SECTION 18 — Closing assessment

HalfApp Driver is a **functional marketplace kernel** with an **explainable, honesty-gated intelligence stack**. Greatest asset: **backend-owned truth** + tests + copy guards. Greatest liability: **interpretation risk** (heatmaps, earnings, Stripe tables read as “done”).

**Next imperative:** Prove **PostgreSQL + OSRM runtime + deploy + workers/retention** (Phase A). Then deepen CRL toward road-matched segments (Phase B). Decide forks (Phase D) before rider/payments/native.

Do **not** add features that imply guarantees the backend cannot prove.

---

# Appendix — References & further reading

External references cited in expanded planning discussions (verify before implementation):

| Topic | Link |
|-------|------|
| OSRM API (route, match) | https://project-osrm.org/docs/v5.24.0/api/ |
| OSRM backend (GitHub) | https://github.com/Project-OSRM/osrm-backend |
| PostgreSQL SKIP LOCKED patterns | https://stackoverflow.com/questions/36760618/postgresql-for-update-skip-locked-still-selects-duplicated-rows |
| pg_partman | https://github.com/pgpartman/pg_partman |
| FastAPI background tasks | https://fastapi.tiangolo.com/tutorial/background-tasks/ |
| arq (async Redis workers) | https://arq-docs.helpmanual.io/ |
| OSM tile usage policy | https://operations.osmfoundation.org/policies/tiles/ |

---

*End of expanded report. For actionable checklist items with IDs (P0-1, P1-7, …), use `HALFAPP_COMPLETION_MASTER_CHECKLIST_01.md`.*
