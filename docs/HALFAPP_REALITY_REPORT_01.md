# HalfApp — Honest Reality Report

**Date:** 2026-05-25  
**Audience:** owner (decision-making about what can and cannot be claimed)  
**Posture:** preservation first, then stabilization, then legal/business, then public launch.  
**Do not use this document to make any claim that is not literally listed under "What is real today."**

---

## 0. Preservation status (first objective)

| Item | Status |
|------|--------|
| All accumulated Shadow work staged | **DONE** — 219 files, multi-session body of work |
| Local commit on feature branch | **DONE** — branch `delivery-programme-execution-01`, commit `52853c2` |
| Pushed to GitHub remote | **BLOCKED** — `gh auth login` not run on this machine; git push returned "Repository not found" (GitHub's response for unauthorized) |
| PR opened on `sannat2300-web/halfapp-driver` | **BLOCKED** — same auth dependency |

**Owner action to unblock preservation in the cloud:**

```powershell
gh auth login          # follow prompts; allow git credential setup
git push -u origin delivery-programme-execution-01
gh pr create --base main --head delivery-programme-execution-01 --fill
```

The work is **not lost** — `git log` on this machine shows the commit. But it is not redundant until pushed.

---

## 1. What is real today

These items have shipped code, passing tests, and honest copy. Nothing in this list assumes anything that has not been proven on this machine.

### Backend product spine

| Surface | Proof |
|---------|-------|
| Auth + JWT + RBAC | `tests/test_auth_jwt_middleware.py`, `tests/test_rbac.py` |
| Refresh-token rotation + revocation | migration `0016`, `tests/test_auth_refresh_rotation.py` |
| Ride lifecycle (requested → accepted → driver_arrived → in_progress → completed) | `tests/test_ride_001_transition_guards.py`, `tests/test_ride_lifecycle.py` |
| Open-board atomic claim lock (first-claim-wins) | `tests/test_ride_claim_lock_concurrency.py` |
| Sequential dispatch cascade | `tests/test_ride_003_dispatch_cascade.py` |
| Driver approval workflow | `tests/test_driver_approval.py` |
| Pricing ledger (integer cents) | `tests/test_pricing_ledger_v01.py` |
| Settlement obligation rows (NOT payouts) | `tests/test_ride_settlement_ledger.py` |
| Route snapshots foundation | `tests/test_route_snapshots_foundation.py` |
| Production SECRET_KEY boot guard | `tests/test_production_guards.py` |
| CORS hardening (wildcard rejected, prod requires explicit origins) | `tests/test_production_guards.py` |
| Structured request logging (`request_id`/`driver_id`/`ride_id`) | `tests/test_request_logging_middleware.py` (new this session) |
| Simulated ride_payments (Phase 3) | `tests/test_ride_payment_phase3.py` |
| Active-ride recovery endpoint | `tests/test_active_ride_recovery.py` |

**Test gate at HEAD:** 390 passed, 9 skipped (SQLite dev). 9 skipped require live PostgreSQL/Docker.

### Driver-app (cockpit)

| Surface | State |
|---------|-------|
| Login + register | shipped |
| Map cockpit with backend-owned presence | shipped |
| Online/offline toggle | shipped |
| Open-board incoming-job sheet + accept | shipped |
| Lifecycle advance (to pickup → arrived → in progress → complete) | shipped |
| Trips list (paged, filtered, backend-backed) | shipped |
| Trip audit / receipt with pricing ledger view | shipped |
| Earnings screen with simulated payment records | shipped |
| Notifications inbox (backend-only, demo tab DEV-gated) | shipped |
| Profile + Settings (vehicle, session, password change, logout-all, prefs) | shipped |
| Session recovery (refresh mid-job preserves state) | code shipped — E2E needs live stack to verify |
| Stale presence banner | shipped |
| Delivery vocabulary consistently used in UI copy | shipped |

**Test gate at HEAD:** 150 passed; `assert-no-money-claims`, `assert-no-ai-providers`, `assert-prod-truth` all OK.

### Rider-app and Ops-app

- `rider-app` Phase 1–3: request, status, fare estimate, receipt on complete, history
- `ops-app` Phase 4: operator panel for backend state inspection

(Inherited from prior sessions; tests present in `backend/tests/test_ops_phase4.py` and rider-app suite.)

---

## 2. What is honest but NOT real today

Things people might assume work, that actually do not.

| Area | Reality |
|------|---------|
| **Real money movement** | No. The system has `ride_pricing` (cent-accurate calculation) and a Stripe code path behind `PAYMENTS_ENABLED`/`PAYOUTS_ENABLED` flags, but there is no production PSP integration in use, no bank deposit, no settled payouts. Payments execution Phase 4–5 exists as code, not as proven money handling. |
| **Production OSRM routing** | No. The OSRM client code is implemented and unit-tested with mocked HTTP. Runtime against a real OSRM container has **not** been proven on this workstation. Routes can degrade to `haversine_fallback` (straight-line). |
| **PostgreSQL production schema** | Migrations are PG-compatible in code and the CI job `postgres-claim-race` is wired, but **local PostgreSQL proof is not run on this machine** (Docker not installed/started here). |
| **Push notifications** | No. UI has a preference toggle but the build does not deliver push. Stated explicitly in the Notifications screen: "Push delivery is not enabled in this build." |
| **Live road-network ETA** | No. ETAs are based on stored fields, not live traffic. |
| **Nearest-driver auto-dispatch** | Off by default. Open-board pool is the default. There is a flag (`HALFAPP_AUTO_ASSIGN=1`) that uses simple nearest-online, but it is not the default product. |
| **Real rider mobile app shipped to App Store / Play Store** | No. `rider-app` is a Vite web app at present. No iOS or Android build/store submission has been done. |
| **Driver mobile app on App Store / Play Store** | No. `driver-app` is a web PWA. No native shell, no store listing. |
| **Production hosting** | No. The runbook documents `uvicorn` on `127.0.0.1` and `npm run dev`. There is no live VPS/cloud deployment proven from this repo's docs. |
| **Marketplace / city-scale ops** | No. No multi-city zones, no airport rules, no fleet command center. |
| **Geocoding from typed addresses** | No. Coordinates must be supplied; labels are not proved locations. |
| **LLM/AI in dispatch/pricing/lifecycle** | No. `assert-no-ai-providers.mjs` enforces this. The "Engineering Intelligence" shell is LOCAL_CONTEXT_ONLY and not in the ride product path. |
| **WebSocket realtime gateway** | No. The cockpit uses polling + on-online refresh; SSE exists for ride pool but not a full realtime presence WS. |

---

## 3. P0 gates (must all be GREEN before any public claim)

| Gate | Status | Blocker |
|------|--------|---------|
| **G1** Postgres claim-race local proof | PARTIAL_GO | Docker / local PG on owner workstation |
| **G2** OSRM runtime proof              | PARTIAL_GO | Docker / OSRM container on owner workstation |
| **G3** Owner courier day               | PENDING_OWNER | Human end-to-end walkthrough; AI is forbidden from marking this GO |
| **G4** Dossier Path A vs B decision    | GO (decision doc only) | — |
| **G5** Surface freeze / OpenAPI drift  | GO | — |
| **G6** SYSTEM_TRUTH reconciliation     | GO | — |
| **G7** Alembic on PostgreSQL           | PARTIAL_GO (folded into G1) | Same as G1 |

**Overall P0:** PARTIAL_GO. Three of seven gates are owner-runtime-blocked. They cannot be closed by an AI agent.

---

## 4. What must happen before HalfApp can legally and safely run for real public users

This is not a code roadmap — it is the reality checklist. Each row is a stop sign until satisfied.

### 4.1 Business and licensing (outside this repo)

| Requirement | Why it blocks public launch |
|-------------|----------------------------|
| Business entity (LLC / Pvt Ltd / equivalent in jurisdiction) registered | No legal person can sign rider/driver/merchant contracts |
| Trade/operating license appropriate to the jurisdiction (e.g., transport network, courier, last-mile delivery) | Operating without it is illegal in most cities |
| Tax registration (GST/VAT/sales tax depending on country) | Required to invoice and to pay drivers |
| Terms of Service + Privacy Policy + Driver/Courier Agreement, reviewed by counsel | Required to bind users and to comply with data law |
| Data protection registration (GDPR / India DPDP / etc.) where applicable | Required before storing personal data of real users |

### 4.2 Driver / courier operating (outside this repo)

| Requirement | Why it blocks public launch |
|-------------|----------------------------|
| Driver license verification + background check process | Liability + insurance condition |
| Vehicle verification (registration, fitness, insurance) | Liability + transport regulations |
| Commercial / hired-vehicle insurance on the operating vehicle | Personal insurance does not cover for-hire trips |
| Document expiry tracking (license, RC, PUC, insurance) | Regulatory and insurance requirement |
| Onboarding flow with KYC | Anti-fraud + tax obligation |

### 4.3 Insurance and liability (outside this repo)

| Requirement | Why it blocks public launch |
|-------------|----------------------------|
| Platform/operator liability cover | Protects company in incidents |
| Driver gap insurance (Period 1/2/3 if applicable) | Protects drivers and platform |
| Rider/customer protection cover | Standard for the industry |
| Incident reporting + escalation policy | Required by regulators and insurers |

### 4.4 Payments and payout (code + legal)

| Requirement | Status here | What's missing |
|-------------|-------------|----------------|
| PSP merchant account (Stripe / Razorpay / equivalent) | code path exists, flag-gated | live merchant account, real keys, proven capture/refund |
| Real customer charge → settlement → driver payout chain | NOT PROVEN | end-to-end live test with small real value, reconciliation, dispute handling |
| Tax invoice / receipt with legal fields | partial (audit receipt UI) | regulatory invoice format |
| Refund and dispute handling SOP | NOT STARTED | written process + UI |
| Driver payout schedule + statement | obligation rows only | actual payout execution + statement PDF/email |
| PCI scope assessment | NOT DONE | needed before handling any card data, even tokenized |

### 4.5 Privacy, security, data (code + legal)

| Requirement | Status here |
|-------------|-------------|
| `SECRET_KEY` boot guard in production | **GO** (`production_guards.py`) |
| Token rotation + revocation | **GO** (migration 0016, logout-all) |
| CORS allowlist enforced in production | **GO** (`tests/test_production_guards.py`) |
| Structured request logging with correlation IDs | **GO** (new this session) |
| Encryption at rest for PII | DEPLOYMENT CONCERN — not in repo |
| Backup + restore plan | DEPLOYMENT CONCERN — not in repo |
| Right-to-erasure / data export endpoints | NOT IMPLEMENTED |
| Audit log of admin actions on personal data | NOT IMPLEMENTED |
| Threat model + penetration test | NOT DONE |
| Secret rotation policy | NOT DOCUMENTED |

### 4.6 Hosting and operations (deployment, outside the source tree)

| Requirement | Status here |
|-------------|-------------|
| Production backend host (managed Postgres + app servers) | NOT PROVISIONED |
| Production driver-app hosting (CDN/static) | NOT PROVISIONED |
| Production rider-app hosting | NOT PROVISIONED |
| Domain + TLS + HSTS | NOT PROVISIONED |
| Centralized log aggregation (Loki / CloudWatch / etc.) consuming `halfapp.request` | NOT WIRED — middleware emits, no shipper |
| Metrics + alerts (uptime, p95 latency, error rate) | NOT WIRED |
| On-call + incident runbook | NOT WRITTEN |
| Daily DB backup + tested restore | NOT IMPLEMENTED |
| Staging environment that mirrors production | DOCUMENTED, NOT PROVEN |

### 4.7 Mobile / device readiness

| Requirement | Status here |
|-------------|-------------|
| iOS native or store-grade PWA (App Store Connect account, app ID, provisioning, App Store Review compliance) | NOT STARTED |
| Android native or TWA (Play Console account, signing key, Play Review compliance) | NOT STARTED |
| App-store privacy nutrition labels | NOT WRITTEN |
| Push notification certificates (APNs / FCM) | NOT CONFIGURED |
| Background location handling that survives App Store review | NOT DESIGNED |
| Crash reporting (Sentry / Crashlytics) | NOT WIRED |

### 4.8 Product completeness before public

| Requirement | Status here |
|-------------|-------------|
| Real-time presence with WebSocket or SSE (not polling) | partial (SSE in pool only) |
| Live ETA from proven routing | blocked on G2 (OSRM runtime) |
| Background location with battery-aware tracking | NOT IMPLEMENTED |
| Rider support flow that reaches a human | NOT IMPLEMENTED (driver support_ticket exists; rider side does not) |
| Driver earnings statement (per period, downloadable) | partial |
| Trip dispute flow | NOT IMPLEMENTED |
| Cancellation policy enforcement (fees, blocks) | NOT IMPLEMENTED |
| Accessibility (WCAG basics) | NOT AUDITED |

---

## 5. Recommended next direction (without faking progress)

A safe ordering — each phase fully closed before the next begins.

### Phase A — Lock and verify what already works (1–2 weeks, owner-only)

1. **Push the preserved branch** (this PR), so the work is durable in the cloud.
2. Owner runs G1: install Docker, start PostgreSQL, run `pytest -k claim_race` on PG. Report goes to `P0_G1_*`.
3. Owner runs G2: start OSRM Portland container, run `scripts/prove_osrm_runtime.py`. Report goes to `P0_G2_*`.
4. Owner runs G3: full courier day on the owner vehicle in a controlled area. Fill `OWNER_COURIER_DAY_REPORT_01.md`.
5. Run E2E `session-recovery.spec.ts` against the live stack to close Slice 6 TODO.

**Exit criterion:** every gate either GREEN or honestly RED with a written reason.

### Phase B — Legal and business (parallel, owner + counsel)

1. Pick jurisdiction, register entity, open business bank account.
2. Engage counsel for ToS / Privacy / Driver Agreement.
3. Apply for transport / delivery operating license.
4. Get commercial insurance quotes.

**Exit criterion:** owner can lawfully sign up one real driver and process one paid customer trip in the chosen jurisdiction.

### Phase C — One-driver, one-rider real pilot (still no public claim)

1. Provision the smallest viable production stack (one app server, managed Postgres, TLS).
2. Wire log shipping (`halfapp.request` → aggregator).
3. Onboard the owner as the first verified driver under the legal entity.
4. Run one real customer trip with real (small) payment through the live PSP.
5. Generate the legal tax invoice; pay the driver via real payout.

**Exit criterion:** one round trip of money has actually happened, with a verifiable bank statement.

### Phase D — Mobile store readiness

1. Wrap driver-app and rider-app as PWAs that pass store review, or build minimal native shells.
2. Set up APNs/FCM, crash reporting, store-listing privacy labels.
3. Submit to internal-testing tracks only.

**Exit criterion:** store-installed builds work end-to-end for the same single-driver pilot.

### Phase E — Closed pilot (5–10 invited drivers, hand-picked riders)

Only after Phases A–D are done. No public marketing.

### Phase F — Public launch in one city

Only after a clean closed pilot, regulator sign-off, and an operations team that can answer a phone during a trip.

---

## 6. What HalfApp must NOT claim before each phase

| Claim | Earliest phase that allows it |
|-------|------------------------------|
| "Production ready" | not before Phase C succeeds |
| "Drivers get paid" | not before Phase C produces a real payout |
| "Live routing" | not before G2 GREEN |
| "Works at scale on Postgres" | not before G1 GREEN |
| "Available on iPhone / Android" | not before Phase D store builds exist |
| "Marketplace" | not before Phase F (real public launch with multiple drivers) |
| "Insured trips" | not before commercial insurance is in force |
| "Legal in city X" | not before the operating license for city X is issued |

Until then the only honest framing is: **"HalfApp is an internal driver-product spine with backend-authoritative lifecycle, simulated payments, and an owner test mode — not a public service."**

---

## 7. Where to look next

- Operational truth table: `docs/CURRENT_TRUTH.md`
- Reconciled backlog: `docs/BACKLOG.md`
- Each shipped slice GO has a report at `docs/<SLICE_NAME>_01.md`
- Each P0 gate report at `docs/P0_G{1..7}_*_REPORT.md`
- Closed-lane do-not-touch list: `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md`
- Forbidden claims: `docs/PRODUCT_BOUNDARY_STAGE0.md`

The repo is honest. Keep it that way.
