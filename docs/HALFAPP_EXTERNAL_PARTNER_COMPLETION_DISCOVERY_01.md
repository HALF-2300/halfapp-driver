# HalfApp Driver — External Partner Discovery Brief  
## What We Have, What We Need, and Questions for Your Team

**Document ID:** `HALFAPP_EXTERNAL_PARTNER_COMPLETION_DISCOVERY_01`  
**Date:** 2026-05-23  
**From:** HalfApp program owner  
**Purpose:** Share with an external engineering / product company so you can scope what is **missing** to complete the driver application, propose approach, effort, cost, and timeline.  

> **Email vendors this one file only:** `docs/HALFAPP_PARTNER_COMPLETION_PACKAGE_01.md`  
> **This discovery brief is superseded by that package** (same content, question format). Keep this file for reference if needed.  
**Repository (on request):** `halfapp-driver` — FastAPI backend + React driver web app  

**How to respond:** Answer the numbered questions in each section. Where we ask for numbers, give ranges (low / likely / high). Where we ask for technique, name the stack and integration pattern. Attach sample code or architecture diagrams if helpful.

---

# PART 1 — Project snapshot (for your team)

## 1.1 What HalfApp Driver is today

HalfApp Driver is a **driver-side ride marketplace MVP** — not a finished Uber competitor. A driver can:

- Register, log in, pass an approval check, go **online**
- See **open-board** ride offers (first driver to claim wins)
- Run the full lifecycle: accept → arrive → start → complete
- View **trips**, **earnings**, **trip audit/receipt** (integer-cent pricing from backend)
- Use a **map-first cockpit** with experimental **city intelligence** overlays (aggregated busy/slow zones and “why activity might be high” explanations — **not** official municipal traffic)

**Stack today:**

| Layer | Technology |
|-------|------------|
| Backend API | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Database (dev) | SQLite; production target **PostgreSQL** |
| Driver UI | React 18, Vite, Leaflet + OpenStreetMap tiles |
| Auth | JWT + refresh token rotation |
| Tests | ~342 backend pytest cases; 124+ frontend unit tests; Playwright E2E |
| Migrations | Alembic head `0031_crl_foundation` (31 revisions) |

**What we explicitly do NOT claim today:**

- Full rider mobile app (rider API exists; no rider UI)
- Production bank payouts to drivers (Stripe schema exists; execution gated)
- Live official traffic (we use **fleet GPS** aggregation only)
- Guaranteed road-accurate routing in production (OSRM **code** exists; **runtime proof** incomplete)
- Native iOS/Android driver app (web app only)

## 1.2 Strategic direction (next 6–12 months)

1. **Complete the driver product** for internal / owner-car testing first — not public driver beta yet.  
2. **Prove production spine:** PostgreSQL, self-hosted OSRM, observability, deployment.  
3. **Decide forks:** rider app, payments pilot, native driver shell, admin operations platform.  
4. **Deepen city intelligence** honestly (rules + aggregates first; ML only if justified).

---

# PART 2 — Gap summary: what is missing to “complete” the application

Use this as the master checklist. Items marked **P0** block credible production or external pilot; **P1** needed for polished product; **P2** strategic / market-dependent.

| # | Gap area | Priority | Current state | Completion bar |
|---|----------|----------|---------------|----------------|
| G1 | **Production database & concurrency** | P0 | SQLite dev; claim-lock tested on SQLite | PostgreSQL in prod + CI claim-race proof |
| G2 | **Road routing runtime (OSRM)** | P0 | Adapter + mocks GO; live OSRM NO_GO | Self-hosted OSRM region extract, health checks, fallback policy |
| G3 | **Production deployment** | P0 | Local scripts only | Staging + prod: API, DB, tiles, OSRM, secrets, CORS |
| G4 | **Observability** | P0 | Minimal | Logs, metrics, alerts, request IDs, ride/dispatch dashboards |
| G5 | **Real-time presence / dispatch** | P1 | REST heartbeat 30s | WebSocket or gateway; stale/offline semantics documented |
| G6 | **Rider product** | P1–P2 | API only | Rider app or partner integration for real demand |
| G7 | **Payments & driver payout** | P2 | Ledger + Stripe foundations | Legal/compliance decision + Connect onboarding + payout UX |
| G8 | **Admin / ops platform** | P1 | Driver approval + basic CRL admin | Dispatch oversight, events, zones, support tickets, reporting |
| G9 | **Native driver app** | P2 | Web only | Background GPS, push, store distribution — if required |
| G10 | **Geocoding & address UX** | P1 | Raw lat/lng on rides | Geocoder + validation + address search |
| G11 | **Intelligence ops** | P1 | Compute-on-read | Cron/workers, retention, multi-city zone catalog |
| G12 | **Compliance & trust** | P1–P2 | Partial | Driver docs, insurance, background check integration, privacy policy for telemetry |
| G13 | **Repository hygiene** | P1 | Legacy folders coexist | Dormant code quarantine; single product path documented |
| G14 | **Load & scale testing** | P1 | Not done | Target drivers/rides per city; bottleneck report |
| G15 | **Documentation & handoff** | P1 | Strong internal docs | Runbooks, API contract, on-call, your team’s delivery docs |

---

# PART 3 — Questions for your company (please answer all that apply)

## SECTION A — Company fit & engagement model

**A1.** Have you shipped a **ride-hailing, delivery, or fleet telematics** product end-to-end (driver app + backend + dispatch)? List 2–3 references (NDA ok).

**A2.** Can you work in our **existing repo** (FastAPI + React) rather than greenfield rewrite? What % of engagements require rewrite vs evolve?

**A3.** Preferred engagement: fixed-price phases, T&M, dedicated squad, or hybrid? Minimum team size you would assign?

**A4.** Do you have **US mobility / Portland OR** market experience (regulation, airport zones, local ops)?

**A5.** Will you sign: NDA, IP assignment to us for work product, no reuse of our code in other clients without license?

**A6.** Provide a **rough ROM** (order of magnitude):

| Phase | Your low $ | Your likely $ | Your high $ | Weeks |
|-------|------------|---------------|-------------|-------|
| P0 production spine (G1–G4) | | | | |
| Driver product completion (UI/UX gaps) | | | | |
| Rider MVP | | | | |
| Payments pilot | | | | |
| Admin / ops | | | | |
| Native driver app | | | | |

---

## SECTION B — Production infrastructure (G1, G3, G4)

**B1.** **PostgreSQL:** Propose target version, hosting (RDS, Cloud SQL, Supabase, self-managed), connection pooling (PgBouncer?), and migration strategy from SQLite/Alembic.

**B2.** **Claim concurrency:** Our open-board dispatch uses DB-level claim locking. How will you **prove** no double-assign under PostgreSQL load? Describe test design (concurrent workers, expected QPS).

**B3.** **Hosting:** Recommend cloud (AWS / GCP / Azure / other) for:
- FastAPI API (containers? serverless?)
- PostgreSQL
- Static driver-app CDN
- Self-hosted OSRM
- Optional Redis for presence/sessions

Provide a **monthly cost estimate** at: (a) 50 drivers, (b) 500 drivers, (c) 5,000 drivers — same city.

**B4.** **CI/CD:** What pipeline do you propose (GitHub Actions, etc.)? Include: pytest on PG, Playwright smoke, migration gate, prod deploy approval.

**B5.** **Secrets:** How will `SECRET_KEY`, JWT keys, Stripe keys, DB URLs be managed (Vault, SSM, Doppler)?

**B6.** **Observability:** Which stack (Datadog, Grafana, CloudWatch, Sentry)? List **10 alerts** you would configure day one.

**B7.** **SLA:** What uptime target do you recommend for MVP vs production? RPO/RTO for database?

**B8.** **CORS & domains:** We need staging + prod driver URLs locked in CORS. Process?

---

## SECTION C — Routing & maps (G2, G10)

**C1.** **OSRM self-host:** Experience deploying OSRM with regional `.osm.pbf` extract? For **Portland metro**, estimate:
- Disk for graph
- RAM per `osrm-routed` instance
- Update cadence for map data
- HA pattern (single node vs cluster)

**C2.** **Fallback policy:** When OSRM is down, we use haversine straight-line. Confirm UI/backend must label “not road-accurate.” Any better degraded mode without paid API keys?

**C3.** **Map tiles:** We use `tile.openstreetmap.org` today. OSM tile policy limits bulk use. Propose **production tile strategy** (self-host, MapTiler, Stadia, etc.) with **monthly cost**.

**C4.** **Geocoding:** Recommend provider or self-host (Nominatim, Pelias) for pickup/dropoff search. Cost per 1k requests? Caching strategy?

**C5.** **ETA honesty:** We do **not** have live municipal traffic. Confirm you will **not** integrate TomTom/Mapbox traffic without explicit product approval and UI disclaimers.

**C6.** Deliverable: runbook to pass our **`HALFAPP_OSRM_RUNTIME_PROOF`** gate (health check script + test ride with road geometry).

---

## SECTION D — Real-time dispatch & presence (G5)

**D1.** Today: REST `POST /drivers/heartbeat` every 30s. Propose upgrade path:
- WebSocket gateway (which tech?)
- Or MQTT / SSE / long poll?
- Backward compatibility with existing mobile web?

**D2.** How do you handle **background location** on mobile web vs native? If native is required for quality, say so explicitly.

**D3.** Target **location freshness SLA** for dispatch (e.g. &lt; 15s)? How many location updates per driver per hour at scale?

**D4.** Should we keep **open-board** dispatch or move to **sequential offer** (Uber-style timer)? We have cascade code behind a flag — your recommendation with tradeoffs.

**D5.** Estimate engineering weeks to production-grade presence + offer push.

---

## SECTION E — Driver application completion (product gaps)

**E1.** Review our driver routes: cockpit, trips (filters + CSV), earnings, notifications, profile, settings, trip audit. What is **still missing** for a driver to work a full day without developer support?

**E2.** **UX audit:** Will you deliver a written UX review of map-first cockpit (readability while driving, safety, one-hand use)?

**E3.** **Offline / flaky network:** Specify expected behavior when heartbeat fails mid-ride. Implementation approach?

**E4.** **Push notifications:** Web push vs native FCM/APNs? Cost and feasibility for offer alerts?

**E5.** **Accessibility & i18n:** We have locale setting stub — scope for full i18n?

**E6.** **App store:** If we need Apple/Google driver app, Capacitor wrapper vs React Native vs Flutter — your recommendation with timeline.

---

## SECTION F — Rider side & marketplace completion (G6)

**F1.** Build **rider app** vs **integrate partner** (API-only)? Pros/cons for our stage.

**F2.** If you build rider MVP, minimum features for real demand loop:
- Request ride
- Cancel
- Track driver
- Pay (or cash flag)
- Rate trip  
Rank by priority; estimate weeks each.

**F3.** How will rider requests feed our **City Reality Layer** (demand signals) with privacy (H3 aggregation, k-anonymity)?

**F4.** Do we need a **separate rider backend** or extend `/rides/*` on same FastAPI service?

---

## SECTION G — Payments & earnings (G7)

**G1.** We have integer-cent `ride_pricing`, settlement **obligation rows**, Stripe Connect schema. What is missing for **legal US driver payout** in Oregon?

**G2.** Stripe Connect vs Adyen vs other — recommendation for marketplace with independent contractors?

**G3.** Timeline and cost for: driver onboarding (KYC), payout schedule, 1099 reporting, refund/chargeback handling.

**G4.** Can we run **months** in “calculation record only” mode (no money movement) while legal review completes? What code paths must stay disabled?

**G5.** Driver-facing copy: we forbid “you got paid” unless bank deposit confirmed. Confirm compliance with your payment UX patterns.

---

## SECTION H — City intelligence “brain” (G11) — SIL + CRL

We built v0.1 **without paid traffic API keys**:

- **SIL:** H3/grid busy + slow heat, route quotes, SHA-256 proof receipts  
- **CRL:** Rule-based “why demand here” (commute, hub, shortage, events)  
- **Telemetry:** Fleet GPS speed samples  

**H1.** Review architecture in `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01.md` Section 4. Valid? What would you change?

**H2.** **Compute model:** Today aggregates recompute on API read. Propose worker/cron architecture (Celery, RQ, K8s jobs, Lambda schedule).

**H3.** **Data retention:** `driver_telemetry_points` grows unbounded. Retention policy and implementation?

**H4.** **Multi-city:** We seed Portland zones (airport, downtown). Process and cost to onboard city #2?

**H5.** **ML roadmap:** When (if ever) would you add ML demand forecast vs keep rule engine? Required data volume (rides/day)?

**H6.** **Privacy review:** Aggregated H3 cells, k-anonymity thresholds — sufficient for GDPR/CCPA-style concerns? What legal review do you recommend?

**H7.** **Research:** Cite any papers or industry benchmarks you use for demand/supply imbalance detection (we do not need marketing claims — need engineering references).

**H8.** Deliverable: wire **map tap → explain** and **suggested positioning** in cockpit with honest copy — estimate weeks.

---

## SECTION I — Admin & operations (G8)

**I1.** Minimum **admin dashboard** for launch: list rides, drivers, approvals, manual city events, CRL overview, support tickets. Wireframe or feature list?

**I2.** **Support tooling:** Our drivers can file trip issues (`driver_support_tickets`). Integrate with Zendesk/Intercom or build internal queue?

**I3.** **Dispatch override:** Do ops need manual assign / cancel / re-offer? Priority?

**I4.** **Reporting:** Daily rides, completion rate, cancel rate, avg wait — SQL views or BI tool (Metabase, Looker)?

**I5.** RBAC: we have `admin` role. Multi-tenant ops roles needed?

---

## SECTION J — Compliance, safety, legal (G12)

**J1.** **Driver onboarding docs:** License, insurance, vehicle registration — store and verify how? Third-party (Checkr, Persona)?

**J2.** **Insurance** for TNC operation in Oregon — your experience or partner referral?

**J3.** **Terms of service / privacy policy** for driver telemetry and aggregated intelligence — can your legal partner draft or review?

**J4.** **Safety features:** In-app emergency, trip sharing, audio recording — required for launch? Scope?

**J5.** **Simulation rides:** Must never appear as real earnings in prod. How will you enforce via config + CI?

---

## SECTION K — Quality, testing, and code (what we may ask you to deliver)

**K1.** Will you run our existing test suite on day 1 and report baseline pass/fail?

**K2.** **Test gaps you see:** List top 10 missing tests (integration, load, security, E2E).

**K3.** **Security audit:** OWASP API top 10 pass — include in scope? Pen test budget?

**K4.** **OpenAPI contract:** We lack drift CI between backend and `api.js`. Propose solution (codegen, Spectral, etc.).

**K5.** **Load test:** Target numbers — concurrent drivers online, rides/hour, telemetry inserts/sec — your recommended targets for Portland MVP.

**K6.** **Code access:** Can you work in GitHub with PR reviews? Branch strategy?

**K7.** **Dormant code:** We have legacy `frontend/`, dossier routes, `video-gate/`. Delete vs archive vs document — your recommendation.

---

## SECTION L — Numbers we need from you (fill in)

| Metric | Our guess (internal) | Your validated estimate |
|--------|----------------------|-------------------------|
| Weeks to P0 production spine | 3–6 | |
| Weeks to driver product “complete” (no rider) | 4–8 | |
| Weeks to rider MVP | 8–16 | |
| Weeks to payments pilot | 6–12 | |
| Engineers FTE for first 90 days | 2–4 | |
| Monthly infra cost @ 100 active drivers | $? | |
| Monthly infra cost @ 1,000 active drivers | $? | |
| OSRM server monthly cost | $? | |
| Map tile monthly cost @ 1k drivers | $? | |
| Geocoding monthly cost @ 10k rides | $? | |
| Break-even rides/day for ops cost | ? | |

---

## SECTION M — Research & technique (optional deep dive)

If your team has research capacity, we welcome brief memos on:

**M1.** Demand prediction without external traffic APIs — minimum viable data requirements.

**M2.** H3 vs S2 vs quadkey for privacy-preserving aggregation at urban scale.

**M3.** OSRM match vs Valhalla for fleet trace snapping (cost/benefit).

**M4.** Open-board vs sequential dispatch for **early marketplace liquidity** (academic or industry sources).

**M5.** Driver cognitive load studies for map-first UI while vehicle in motion — design constraints.

---

# PART 4 — What we can provide to your team

To scope accurately, we can share:

| Asset | Notes |
|-------|-------|
| Git repository access | Private GitHub; NDA required |
| `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01.md` | 724-line technical brain doc |
| `docs/CURRENT_TRUTH.md` | GO/NO-GO status table |
| `docs/RUN_LOCAL.md` | One-command local run |
| Demo environment | On request after NDA |
| Product owner availability | For weekly sync |
| Existing test logs | 342 backend tests, Playwright E2E |

**We will NOT ask you to:**

- Claim live municipal traffic without approved providers  
- Copy-paste unrelated greenfield code that ignores our `/drivers/*` API  
- Enable real money movement without explicit legal sign-off  

---

# PART 5 — Suggested response format

Please return a single PDF or Markdown document with:

1. **Executive summary** (1 page) — your understanding + recommended path  
2. **Answers** to Sections A–L (table or numbered)  
3. **Phased proposal** — Phase 0 (P0 spine), Phase 1 (driver complete), Phase 2 (rider or ops), Phase 3 (payments/native)  
4. **Team roster** — roles, seniority, allocation %  
5. **Timeline Gantt** (high level)  
6. **Commercial** — ROM, payment milestones, change control  
7. **Risks & assumptions** — what you need from us to hit dates  
8. **Appendix** — architecture diagram, sample similar work, references  

---

# PART 6 — Priority order (if budget is limited)

If you can only fund **one phase**, we recommend this order:

1. **P0 — Production spine** (PostgreSQL, deploy, OSRM proof, observability)  
2. **Driver product hardening** (network/offline, notifications, profile, ops runbooks)  
3. **Admin + intelligence workers** (CRL/SIL cron, zone catalog, support queue)  
4. **Rider MVP** OR **payments pilot** — business decision, not purely technical  
5. **Native app + advanced dispatch** — only after web spine proven  

---

# PART 7 — Contact & versioning

| Field | Value |
|-------|-------|
| Document version | 1.0 |
| Internal reference | `HALFAPP_EXTERNAL_PARTNER_COMPLETION_DISCOVERY_01` |
| Related internal report | `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01` |
| Questions addendum | Request updated `_02` if scope changes |

---

*This document is intended for external vendors, agencies, and engineering partners. It describes gaps honestly so proposals are comparable. It is not a commitment to procure any specific scope until a signed SOW exists.*
