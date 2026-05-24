# HalfApp Driver — Expert Inquiry (Single File)

**Document ID:** `HALFAPP_PARTNER_COMPLETION_PACKAGE_01`  
**Date:** 2026-05-23  
**From:** HalfApp program owner  
**To:** Engineering / product expert or company  

**Repository (NDA on request):** `halfapp-driver` — FastAPI + SQLAlchemy + React/Vite driver web app  
**Alembic head:** `0031_crl_foundation` · **Backend tests:** 342 · **Driver unit tests:** 124+  

**Please return:** One document answering every **Your answer** cell below, plus phased proposal (timeline, team, ROM, risks).

---

# What we are aiming at

**HalfApp Driver** is a **driver-side ride marketplace MVP** — backend owns truth; the web app displays it.

| Phase | Goal | Not in scope yet |
|-------|------|------------------|
| **Now** | **Owner-car staging** — real PostgreSQL, deploy, OSRM proof; one person runs a full day on staging | Public driver beta, PBOT commercial launch |
| **Next** | **Driver product complete** — session recovery, network UX, admin minimum, intelligence workers | Rider app, bank payouts |
| **Later** | **Business forks** — Portland trusted drivers, payments pilot, native app | Only after staging + internal week |

**Dispatch model (fixed for now):** **Open board** — all eligible drivers see the pool; each driver **claims a specific ride by ID**; **first atomic claim wins**. This is **not** nearest-driver auto-assign. Do **not** propose replacing this without explaining tradeoffs.

**Payments (fixed for now):** **Calculation record only** — integer-cent `ride_pricing` ledger, trip audit receipt. **No** “driver got paid to bank” unless deposit is proved. Real money movement requires legal sign-off.

**Honesty (non-negotiable):** No live official traffic claims; no road-accurate routing when OSRM fallback is active; no greenfield rewrite abandoning our API and Alembic history.

---

# How to respond

1. Read **Sections 1–3** (context).  
2. If we grant repo access: run tests in **Section 4** and review **Section 5** files.  
3. Fill **every “Your answer”** in **Section 6** (main questions).  
4. Use **Section 7** optional research only where you need external sources.  
5. Return format per **Section 8**.

---

# SECTION 1 — Confirm you understand our product

| # | Statement | Your answer (Agree / Disagree + why) |
|---|-----------|--------------------------------------|
| 1.1 | Backend is authoritative for ride state, pricing, dispatch, presence, intelligence | |
| 1.2 | Active code is only `backend/` + `driver-app/` — not legacy `frontend/` or dossier spine in driver app | |
| 1.3 | Open-board claim: drivers choose a ride; many drivers may claim the **same** ride; one winner, others get 409 with transparency proof | |
| 1.4 | Claim uses row lock + conditional UPDATE on that ride row (see `backend/services/dispatch.py`) — **not** a worker queue scanning with SKIP LOCKED | |
| 1.5 | Claim-lock is proven on **SQLite** (10-driver race test); we need **PostgreSQL** proof before production | |
| 1.6 | Pricing is `ride_pricing` integer cents — **not** a separate double-entry accounting system today | |
| 1.7 | SIL/CRL use H3 aggregates and rule-based copy — **not** ML or municipal traffic APIs | |

**1.8.** In one paragraph: what is HalfApp today and what should we do in the next 90 days?  
**Your answer:**

---

# SECTION 2 — What we believe works (validate against repo)

| # | Capability | Your validation (Yes / Partial / No) |
|---|------------|-------------------------------------|
| 2.1 | JWT auth, refresh tokens, driver approval gate | |
| 2.2 | Lifecycle: accept → arrive → start → complete | |
| 2.3 | Trips filters + CSV, earnings, notifications, settings | |
| 2.4 | Trip audit receipt, route truth UI | |
| 2.5 | Fleet telemetry (5s ping), SIL map, CRL explain API | |
| 2.6 | Playwright ride-flow E2E + ~342 pytest | |

**2.7.** What is the **single highest-risk gap** you see in our codebase?  
**Your answer:**

**2.8.** What is the **single best week-1 action** toward staging?  
**Your answer:**

---

# SECTION 3 — Key files to review

| Area | Path |
|------|------|
| Claim / dispatch | `backend/services/dispatch.py` |
| Lifecycle | `backend/services/lifecycle.py` |
| Pricing ledger | `backend/services/ride_pricing.py`, `models/ride_pricing.py` |
| Routing / OSRM | `backend/services/routing_service.py` |
| SIL / CRL | `backend/services/sil_compute.py`, `crl_attribution.py` |
| Driver API | `backend/routes/drivers.py` |
| Frontend boundary | `driver-app/src/utils/api.js` |
| Cockpit | `driver-app/src/components/MapHome.jsx` |
| Claim race test | `backend/tests/test_ride_claim_lock_concurrency.py` |

**Tests to run:**

```powershell
cd backend && py -3.11 -m pytest tests -q
cd driver-app && npm test && npm run build && npm run test:e2e:ride-flow
```

**Your answer (pass/fail + notes):**

---

# SECTION 6 — Questions we need answered

Fill every cell. Give ranges (low / likely / high) for cost and time.

## 6.1 Production spine (P0 — blocks staging)

| ID | Question | Your answer |
|----|----------|-------------|
| Q1 | **PostgreSQL:** version, hosting (RDS / Supabase / other), connection pooling (PgBouncer?) for FastAPI + SQLAlchemy? | |
| Q2 | **Open-board claim on PostgreSQL:** Our pattern is lock **one ride row** + conditional UPDATE when many drivers claim the **same** ride. Is this sound? How do you **prove** no double-assign? What load test design? (**Do not assume SKIP LOCKED unless you explain why it fits this model.**) | |
| Q3 | **OSRM:** Self-host for **Oregon / Portland metro** — disk, RAM, CPU, single node vs HA? We have `docker/osrm-portland/` and mocked tests; runtime proof is NO_GO. | |
| Q4 | When OSRM is down: is haversine + honest “not road-accurate” label acceptable? | |
| Q5 | **Cloud** for API, PostgreSQL, static driver-app, OSRM, optional Redis? | |
| Q6 | **Monthly infra cost** at ~50, ~500, ~5,000 **online drivers** (same city)? | |
| Q7 | **CI/CD:** GitHub Actions — pytest on PostgreSQL, Playwright smoke, migration gate? | |
| Q8 | **Secrets:** SSM, Doppler, Vault, or other? | |
| Q9 | **Observability:** stack choice + **10 day-one alerts** you would configure? | |
| Q10 | **Map tiles:** production strategy (self-host / MapTiler / Stadia / other) and cost at ~1k drivers? | |
| Q11 | **CORS + staging/prod domains** — your process? | |
| Q12 | **Owner runbook:** go online → claim ride → complete → audit on staging — can you deliver this? | |

## 6.2 Driver app and reliability (P1)

| ID | Question | Your answer |
|----|----------|-------------|
| Q13 | **WebSocket vs SSE vs MQTT vs REST** for heartbeat and offer updates — recommendation for our stage? | |
| Q14 | **Session recovery:** driver refreshes browser mid-ride — must restore active ride from backend. How? | |
| Q15 | **Flaky network** during active ride — UX and backend behavior? | |
| Q16 | **Stale presence** — threshold, auto-offline, finish-ride-before-offline? | |
| Q17 | **PWA vs Capacitor vs React Native** — we are web today; need background GPS only if/when we go native. Recommendation and timing? | |
| Q18 | **Push notifications** for offer alerts — Web Push vs FCM/APNs vs in-app only at MVP? | |
| Q19 | **Geocoding** — provider or self-host for address display/search; cost and caching? | |
| Q20 | **Map cockpit UX** — safe while driving? What must change? | |
| Q21 | What is **still missing** on cockpit, earnings, notifications, profile for a full workday? | |
| Q22 | Same **“calculation record”** language on trips, earnings, audit — how do you enforce? | |

## 6.3 Intelligence — SIL, CRL, telemetry (P1)

| ID | Question | Your answer |
|----|----------|-------------|
| Q23 | **Background workers** for SIL/CRL (Celery, RQ, arq, cron) — we recompute on map read today. Recommendation? | |
| Q24 | **Telemetry retention** for `driver_telemetry_points` — days to keep, implementation (partition, TimescaleDB, purge job)? | |
| Q25 | **GPS ping every 5s** — appropriate? | |
| Q26 | **H3 vs S2 vs Quadkey** — we use H3; should we stay? | |
| Q27 | **Demand signals without paid traffic APIs** — minimum data before any forecast is honest? | |
| Q28 | **Map tap → explain** and **SIL suggest UI** — priority and week estimate? | |

## 6.4 Admin and ops (P1)

| ID | Question | Your answer |
|----|----------|-------------|
| Q29 | **Minimum admin dashboard** for internal pilot (rides search, approvals, support tickets, city events)? | |
| Q30 | Support tickets: Zendesk/Intercom vs internal queue? | |
| Q31 | **Reporting:** SQL views vs Metabase/Looker? | |

## 6.5 Strategic forks (P2 — advise now, build later)

| ID | Question | Your answer |
|----|----------|-------------|
| Q32 | **Rider app:** build vs partner API vs defer? | |
| Q33 | **Payments:** stay calculation-only vs Stripe Connect pilot — what's missing for Oregon? | |
| Q34 | **Open-board vs sequential dispatch** — keep open board for early liquidity? | |
| Q35 | **Dossier spine** (`/supply`, `/demand`, `/trip`): delete, wire, or keep parallel? | |
| Q36 | **External driver beta** — checklist before non-owner drivers? | |

## 6.6 Compliance — Oregon (P2 unless we choose Portland beta)

| ID | Question | Your answer |
|----|----------|-------------|
| Q37 | If we run **Portland trusted-driver beta:** PBOT insurance, background checks, vehicle inspection — summary and cost? | |
| Q38 | Background vendor: Checkr, Yardstik, Persona, other? | |
| Q39 | Terms + privacy for telemetry and map aggregates — who drafts? | |

## 6.7 Commercial

| ID | Question | Your answer |
|----|----------|-------------|
| Q40 | Weeks to **P0 staging** (low / likely / high)? | |
| Q41 | Weeks to **driver-complete** without rider app? | |
| Q42 | Engineers **FTE** first 90 days? | |
| Q43 | **ROM by phase** (P0, driver, admin, intelligence, rider, payments, native)? | |
| Q44 | Can you work in our **existing repo** (no greenfield rewrite)? Engagement model? | |

### Decisions — your recommendation

| Decision | Options | Your recommendation |
|----------|---------|---------------------|
| Cloud | AWS / GCP / Azure / other | |
| PostgreSQL | RDS / Supabase / self-managed | |
| OSRM host | Oregon extract — which host | |
| Map tiles | Self-host / MapTiler / Stadia / other | |
| Rider product | Build / partner / defer | |
| Money movement | Calculation-only / Stripe pilot / defer | |
| Driver app | PWA / Capacitor / React Native | |
| Dispatch | Open board / sequential / hybrid | |
| Geography | Portland first / multi-city | |

### Build order

We propose: **P0 staging → P1 driver polish → ops/brain → business forks one at a time.** Agree? Your answer:

---

# SECTION 7 — Optional research topics

Use only if you need external sources. Our open-board model is **not** nearest-driver queue dispatch.

| # | Topic | Covers |
|---|-------|--------|
| 1 | PostgreSQL + PgBouncer + **same-ride multi-claim** concurrency on FastAPI | Q1, Q2, Q5, Q6 |
| 2 | OSRM Oregon extract sizing, fallback policy, map tiles, geocoding | Q3, Q4, Q10, Q19 |
| 3 | WebSocket vs SSE vs MQTT; PWA vs Capacitor vs RN | Q13–Q17 |
| 4 | Oregon TNC / PFHT compliance if we choose Portland beta | Q37–Q39 |
| 5 | H3 vs S2; demand signals without paid traffic APIs | Q26, Q27 |
| 6 | arq vs Celery; telemetry retention | Q23, Q24 |
| 7 | CI/CD, secrets, observability for FastAPI staging | Q7–Q9 |
| 8 | Admin minimum; open-board vs sequential for early liquidity | Q29–Q31, Q34 |

---

# SECTION 8 — Return format

One PDF or Markdown with:

1. **Executive summary** (1 page)  
2. **Section 1–2** confirmations  
3. **Section 6** — every question answered  
4. **Phased proposal:** P0 → P1 → P2  
5. **Team, timeline, ROM, risks & assumptions**  
6. **Appendix** — architecture diagram or similar work (optional)

---

# SECTION 9 — What we provide

| Asset | Available |
|-------|-----------|
| Private GitHub (NDA) | On request |
| Local run: API **8000**, driver-app **3022** | Yes |
| Test logs | Yes |
| Product owner sync | Weekly |

---

# SECTION 10 — What we will not accept

- Greenfield rewrite abandoning `/drivers/*` and Alembic  
- Claiming live official traffic or road-accurate routing when fallback active  
- “Driver got paid” without bank deposit proof  
- Real money movement without legal sign-off  
- Nearest-driver dispatch redesign **without** explaining impact on open-board product  
- External driver beta before staging + internal owner-car week  

---

**Version:** 6.0 — clean expert inquiry (questions only; no pre-filled research)  
**Date:** 2026-05-23  

*Send this file only.*
