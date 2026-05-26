# HalfApp Driver — Master Completion Checklist

**Document ID:** `HALFAPP_COMPLETION_MASTER_CHECKLIST_01`  
**Date:** 2026-05-23  
**Purpose:** Internal daily checklist. **To email an external company, use one file only:** `HALFAPP_PARTNER_COMPLETION_PACKAGE_01.md` (question format).  
**Status key:** ✅ Done · 🟡 Partial / foundation only · ❌ Not done · 🔀 Decision required  

**Deep dives (only when needed):**

| Doc | Use for |
|-----|---------|
| **`HALFAPP_COMPLETION_MASTER_CHECKLIST_01.md`** | **What to build — start here daily** |
| `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_01.md` | Architecture & “brain” (concise) |
| `HALFAPP_PROGRAM_BRAIN_AND_SYSTEM_REPORT_02_EXPANDED.md` | Deep narrative + Phase A/B engineering detail |
| `HALFAPP_EXTERNAL_PARTNER_COMPLETION_DISCOVERY_01.md` | Vendor questions & ROM |
| `CURRENT_TRUTH.md` | GO/NO-GO proof table |
| `BACKLOG.md` | Ticket IDs & closed lanes |

---

## How to read this file

1. **Section 1** — What is already done (do not rebuild).  
2. **Section 2** — **P0** must finish before production or external pilot.  
3. **Section 3** — **P1** driver product & ops polish (internal owner-car ready).  
4. **Section 4** — **P2** market / legal forks (rider, money, native).  
5. **Section 5** — Per-screen driver app gaps.  
6. **Section 6** — City intelligence (SIL + CRL) gaps.  
7. **Section 7** — Decisions you must make (blocks work).  
8. **Section 8** — Recommended build order (single path).  
9. **Section 9** — Verification ritual after each phase.

---

# SECTION 1 — Already done (do not reopen casually)

These are **proven** in code + tests. Vendors and agents should **extend**, not rewrite.

| Area | Status | Proof |
|------|--------|-------|
| JWT auth + RBAC | ✅ | `test_auth_jwt_middleware.py`, `test_rbac.py` |
| Refresh token rotation | ✅ | migration 0016, refresh tests |
| Ride lifecycle state machine | ✅ | `test_ride_001_transition_guards.py` |
| Open-board dispatch + atomic claim | ✅ | `test_ride_claim_lock_concurrency.py` |
| Sequential dispatch cascade (flag) | ✅ | RIDE-003 tests |
| Driver approval gate | ✅ | `test_driver_approval.py` |
| Integer-cent pricing + lock on complete | ✅ | `test_pricing_ledger_v01.py` |
| Settlement obligation rows (not payout) | ✅ | `test_ride_settlement_ledger.py` |
| Driver presence + heartbeat | ✅ | presence routes, MapHome 30s ping |
| Trip audit / receipt UI | ✅ | audit E2E lock |
| Route truth read UI | ✅ | route-truth E2E |
| Cockpit ride-flow (accept → complete) | ✅ | ride-flow E2E |
| Trips list + filters + CSV export | ✅ | `/drivers/me/trips`, TripsList |
| Settings (theme, units, quiet hours, locale) | ✅ | DriverSettings, preferences context |
| Password reset + sign-out all devices | ✅ | auth routes, migration 0027 |
| In-app notifications (lifecycle events) | ✅ | slice 04 |
| Ride chat storage + driver UI | ✅ | migration 0028 (rider delivery N/A) |
| Fleet telemetry + SIL + CRL v0.1 | ✅ | migrations 0029–0031, `/v1/sil/*`, `/v1/crl/*` |
| Production SECRET_KEY guard | ✅ | `production_guards.py` |
| Alembic migrations (31 revisions) | ✅ | head `0031_crl_foundation` |
| Backend test gate | ✅ | ~342 pytest |
| Driver unit tests + money-claim guards | ✅ | ~124+ unit, assert scripts |

---

# SECTION 2 — P0: Production spine (blocks real deployment)

**Goal:** Credible staging/production environment — not public launch yet.

| ID | Item | Now | Done when | Owner hint |
|----|------|-----|-----------|------------|
| P0-1 | **PostgreSQL production DB** | Local PG proof **GO** | Hosted PG configured for staging/prod | Infra / backend |
| P0-2 | **Claim-race proof on PostgreSQL** | **GO** | Fresh PG Alembic + claim-race proof passed; keep CI green | Backend / QA |
| P0-3 | **OSRM runtime proof** | **GO** | Runtime proof passed; route truth honest when fallback is used | DevOps |
| P0-3b | **OSRM graph sizing** | Not documented | Host RAM/disk sized for regional extract (see `_02` §15 A1) | DevOps |
| P0-4 | **Staging + production deploy** | Local scripts (`run_dev.ps1`) | API + driver-app CDN + DB + secrets; staging URL | DevOps |
| P0-5 | **CORS production lock** | Partial | Explicit origins only; no wildcard in prod | Backend |
| P0-6 | **Observability baseline** | Minimal | Structured logs, request IDs, error tracking (Sentry or equiv.), 5–10 alerts | DevOps |
| P0-7 | **Production map tiles** | OSM public tiles (policy risk) | Self-hosted or licensed tile CDN | DevOps |
| P0-8 | **Internal owner test runbook** | Scattered flags | One doc: go online → get ride → complete → audit; no beta copy | Product |

**Exit criteria for P0:** Owner can run a real trip on **staging** with PG + OSRM + deployed apps; logs visible; no SQLite in prod.

---

# SECTION 3 — P1: Complete the driver product (internal use)

**Goal:** A driver (you) can work a full day on web app without developer help — still **no external driver beta**.

### 3.1 Infrastructure & platform

| ID | Item | Now | Done when |
|----|------|-----|-----------|
| P1-1 | **Real-time presence** | REST heartbeat 30s | WebSocket or gateway OR documented REST SLA; stale UX spec |
| P1-2 | **SIL/CRL background workers** | Recompute on every map API call | Cron/worker (e.g. arq + Redis); schedule compute bucket (see `_02` §15 A4) |
| P1-3 | **Telemetry retention** | Unbounded `driver_telemetry_points` | Retention policy (e.g. 14–30 days); consider `pg_partman` or purge job (see `_02` §15 A3) |
| P1-4 | **OpenAPI ↔ api.js contract CI** | Manual drift | Snapshot test fails on breaking API change |
| P1-5 | **Load test baseline** | None | Report: N concurrent drivers, M rides/hr before pain |
| P1-6 | **Repo hygiene** | `frontend/`, dossier, `video-gate/` | Archive or README quarantine; one product path in README |

### 3.2 Driver app surfaces

| ID | Item | Now | Done when |
|----|------|-----|-----------|
| P1-7 | **Cockpit session recovery** | ✅ 2026-05-26 | Stale-presence banner + resume notice + dismiss; network degraded + offline banners |
| P1-8 | **Stale presence UX** | ✅ 2026-05-26 | MapHome shows stale banner at 45s threshold with last-heartbeat time; go-offline gate |
| P1-9 | **Flaky network behavior** | 🟡 2026-05-26 | CockpitNetworkBanner: offline + degraded states wired; heartbeat-fail UX visible; no formal retry test yet |
| P1-10 | **Profile completion** | ✅ 2026-05-26 | Editable phone + emergency contact with save/cancel; vehicle section; dark theme aligned |
| P1-11 | **Notifications polish** | ✅ 2026-05-26 | Mark-read + mark-all-read; cockpit dark theme; unread dot; SHOW_DEMO_MESSAGES_TAB guard preserved |
| P1-12 | **Earnings ↔ audit language** | 🟡 2026-05-26 | Period selector (today/week/all) added; “obligation” framing consistent; deeper audit link deferred |
| P1-13 | **Bottom nav consistency** | ✅ 2026-05-26 | Account tab routes to /driver/profile; active state covers both /profile and /settings |
| P1-14 | **Geocoding / address** | Raw lat/lng on rides | Geocoder for display/search (even if coords still stored) |

### 3.3 Admin & ops (minimum)

| ID | Item | Now | Done when |
|----|------|-----|-----------|
| P1-15 | **Admin ride list + search** | ✅ 2026-05-26 | Search by ride id/driver id/rider id/status; match count; empty state |
| P1-16 | **Support ticket queue** | DB + driver POST | Admin view/respond workflow (even minimal) |
| P1-17 | **City events UI** | API `POST /admin/crl/events` | Form for concerts/operator events |
| P1-18 | **Zone catalog ops** | Portland seeds in code | Import/edit zones per city (admin or CSV) |
| P1-19 | **CRL overview dashboard** | API only | Simple admin page: cause breakdown + hot cells |

### 3.4 Intelligence product (honest v0.2)

| ID | Item | Now | Done when |
|----|------|-----|-----------|
| P1-20 | **Map tap → explain** | List panel only | Tap hex on map → `GET /v1/crl/explain` |
| P1-21 | **Suggested positioning** | API exists, UI not wired | Cockpit shows “consider area X” with disclaimer |
| P1-22 | **Multi-city zone pack** | Portland only | Process to add city #2 |
| P1-23 | **Time baseline job** | Updated on compute | Nightly `crl_time_pattern` rollup |

**Exit criteria for P1:** Internal owner-car test for 1 week on staging; all P1-7–P1-14 pass manual script; ops can file/view support tickets.

---

# SECTION 4 — P2: Strategic completion (needs business decision)

Do **not** start until Section 2 P0 is done and Section 3 P1 driver gaps are triaged.

| ID | Item | Now | Done when | Decision |
|----|------|-----|-----------|----------|
| P2-1 | **Rider app** | API only (`POST /rides/`) | Rider can request + cancel + track | Build vs partner vs defer |
| P2-2 | **Real marketplace demand** | Test/sim rides | CRL/SIL fed by real rider volume | Depends on P2-1 |
| P2-3 | **Payments pilot** | Stripe schema; gated | Legal sign-off + Connect onboarding + payout UX | Go / no-go / calculation-only forever |
| P2-4 | **Driver bank payout** | NO | Money in bank + honest UI | Requires P2-3 + compliance |
| P2-5 | **Native driver app** | Web only | iOS/Android store app | Required for background GPS? |
| P2-6 | **Push notifications** | In-app only | FCM/APNs or Web Push for offers | Tied to P2-5 |
| P2-7 | **Advanced dispatch** | Open board | Sequential offer / geo eligibility | Product strategy |
| P2-8 | **Compliance pack** | Partial approval | License/insurance/background check vendor | Legal |
| P2-9 | **TNC insurance / Oregon ops** | Not started | Counsel + policy | Legal |
| P2-10 | **Dossier spine** | Parallel `/supply` routes | Wire OR delete from `main.py` | Architecture fork |
| P2-11 | **ML demand forecast** | Rule-based CRL | Only if data volume justifies | Research |
| P2-12 | **External driver beta** | Deferred | Onboarding, waitlist, support scale | After P0+P1 |

---

# SECTION 5 — Driver app screen checklist

Quick per-route view. ✅ = shippable for internal test; 🟡 = usable gaps; ❌ = missing.

| Route | Screen | Status | Still needed |
|-------|--------|--------|--------------|
| `/` | Login / register / forgot password | ✅ | — |
| `/driver` | Map cockpit | 🟡 | P1-9 retry test; P1-21 positioning nudge |
| `/driver/trips` | Trips list | ✅ | — |
| `/driver/trips/:id/audit` | Trip audit | ✅ | Optional narrative above fold |
| `/driver/earnings` | Earnings | 🟡 | Deeper audit link; P1-12 partial |
| `/driver/notifications` | Alerts | ✅ | Mark-read done; push delivery deferred P2-6 |
| `/driver/profile` | Profile | ✅ | Editable contact + vehicle; dark theme |
| `/driver/settings` | Settings | ✅ | — |
| — | Street Intelligence panel | 🟡 | P1-20, P1-21 |
| — | City Reality panel | 🟡 | P1-20 |
| — | Ride chat | 🟡 | Rider-side delivery N/A |
| — | Navigation panel | 🟡 | External maps only; no in-app steps |

---

# SECTION 6 — Backend / API checklist

| API area | Status | Still needed |
|----------|--------|--------------|
| `/auth/*` | ✅ | — |
| `/drivers/*` lifecycle | ✅ | — |
| `/drivers/me/trips` + export | ✅ | — |
| `/drivers/me/telemetry` | ✅ | P1-3 retention |
| `/v1/sil/*` | 🟡 | P1-2 workers |
| `/v1/crl/*` | 🟡 | P1-2 workers; P1-19 admin UI |
| `/admin/crl/*` | 🟡 | P1-17 UI |
| `/rides/*` rider | ✅ API | P2-1 rider UI |
| Payments / Stripe webhooks | 🟡 flagged | P2-3 decision |
| WebSocket / realtime | ❌ | P1-1 |
| Geocoding service | ❌ | P1-14 |
| Full admin CRUD | 🟡 | P1-15–P1-19 |

---

# SECTION 7 — Decisions required (unblocks planning)

Answer these in writing before vendor SOW or next sprint:

| # | Question | Options | Blocks |
|---|----------|---------|--------|
| D1 | Deploy where? | AWS / GCP / Azure / other | P0-4, cost |
| D2 | PostgreSQL host? | RDS / Supabase / self-managed | P0-1 |
| D3 | OSRM: self-host region? | Portland first; which host | P0-3 |
| D4 | Map tiles in prod? | Self-host / MapTiler / other | P0-7 |
| D5 | Rider product? | Build app / partner API / defer | P2-1, P2-2 |
| D6 | Money movement? | Calculation-only / Stripe pilot / defer | P2-3, P2-4 |
| D7 | Driver app form factor? | PWA web / Capacitor / RN native | P2-5, P2-6 |
| D8 | Dispatch model long-term? | Open board / sequential / hybrid | P2-7 |
| D9 | Dossier spine? | Delete / wire / keep parallel | P1-6, P2-10 |
| D10 | First launch geography? | Portland only / multi-city | P1-22 |
| D11 | External drivers when? | After P0+P1 internal week / date TBD | P2-12 |

---

# SECTION 8 — Single recommended build order

Use this sequence so you do not get lost. **Do not skip P0.**

```
Phase 0 — PRODUCTION SPINE (weeks 1–4)
  P0-1 PostgreSQL proof (GO)
  P0-2 PG claim-race proof (GO)
  P0-3 OSRM runtime proof (GO)
  P0-4 Deploy staging (+ prod shell)
  P0-5 CORS lock
  P0-6 Observability
  P0-7 Production tiles
  P0-8 Owner test runbook

Phase 1 — DRIVER COMPLETE (weeks 4–8)
  P1-7  Cockpit session recovery
  P1-8  Stale presence UX + tests
  P1-9  Network degradation tests
  P1-10 Profile fields
  P1-11 Notifications polish
  P1-12 Earnings/audit copy lock
  P1-13 Nav shell consistency
  P1-14 Geocoding (minimal)

Phase 2 — OPS + BRAIN OPS (weeks 6–10, overlap ok)
  P1-2  SIL/CRL workers
  P1-3  Telemetry retention
  P1-15–P1-19 Admin minimum
  P1-20–P1-23 Intelligence UX v0.2

Phase 3 — HARDENING (weeks 8–12)
  P1-1  Realtime presence (if needed)
  P1-4  OpenAPI contract CI
  P1-5  Load test
  P1-6  Repo hygiene

Phase 4 — BUSINESS FORKS (only after Phase 0–1 sign-off)
  Resolve D5–D11
  Then: P2-1 rider OR P2-3 payments OR P2-5 native (pick one primary)
```

---

# SECTION 9 — Verification ritual (after each phase)

Run from repo root (adjust paths):

```powershell
# Backend
cd backend
py -3.11 -m alembic upgrade head
py -3.11 -m pytest tests -q

# Driver app
cd ..\driver-app
npm test
npm run build
npm run test:e2e:ride-flow
```

**Phase 0 extra:** OSRM health script, staging smoke URL, PG connection from API.

**Phase 1 extra:** Manual owner-car script (see P0-8 runbook).

**Record results** in a one-line note at bottom of this file (changelog).

---

# SECTION 10 — What we explicitly will NOT do (without new approval)

- Claim **official / live municipal traffic** without provider + UI approval  
- Claim **road-accurate routing** when OSRM down (haversine fallback)  
- Claim **driver got paid** without bank deposit proof  
- Enable **real money movement** without legal sign-off  
- **External driver beta** before P0 + P1 exit criteria  
- **Greenfield rewrite** abandoning `/drivers/*` API and Alembic history  
- Wire **dossier spine** to driver app without architecture decision D9  

---

# SECTION 11 — Progress tracker (edit by hand)

| Phase | Target date | Status | Notes |
|-------|-------------|--------|-------|
| P0 Production spine | | ⬜ Not started / 🟡 In progress / ✅ Done | |
| P1 Driver complete | | ⬜ / 🟡 / ✅ | |
| P1 Ops + brain ops | | ⬜ / 🟡 / ✅ | |
| P1 Hardening | | ⬜ / 🟡 / ✅ | |
| P2 Business fork chosen | | ⬜ / 🟡 / ✅ | Decision doc link: |

**Changelog**

| Date | Note |
|------|------|
| 2026-05-23 | Master checklist created — consolidates brain report §12–15, discovery Part 2, backlog P0–P2, product roadmap gaps |

---

*This is the single completion source of truth. Update this file when items ship; link PRs in changelog. For vendor ROM questions, use `HALFAPP_EXTERNAL_PARTNER_COMPLETION_DISCOVERY_01.md`.*
