# HalfApp — Launch Blockers (Open List)

**Last updated:** 2026-05-25  
**Boundary:** **PUBLIC_LAUNCH_NO_GO** (unchanged).  
**Rule:** A blocker is closed **only with proof** (test output, signed report, regulator document, screenshot, log evidence). Re-wording does not close anything.

This document is the single canonical list of what still must be true before HalfApp can move from internal product to a real controlled pilot, then to public launch. The order is approximate but enforced: technical proof first, then legal/operational, then deployment, then stores.

---

## Status legend

| Symbol | Meaning |
|--------|---------|
| 🔴 | OPEN — not started or actively blocked |
| 🟡 | PARTIAL — implementation exists, proof pending |
| 🟢 | CLOSED — closed with proof; link to evidence |

---

## Tier 1 — Local technical proof (must close before anything else)

| ID | Blocker | Status | Closes with |
|----|---------|--------|-------------|
| **G1** | PostgreSQL local proof: `alembic upgrade head` on a real PG, 10-driver claim race shows 1 winner / 9×409 | 🟢 **CLOSED 2026-05-25** | Fresh PostgreSQL 16 temporary cluster; Alembic head + claim-race tests passed. Evidence: `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md`, `docs/P0_G7_ALEMBIC_POSTGRES_PROOF_01.md` |
| **G2** | OSRM runtime proof: `scripts/prove_osrm_runtime.py` exits 0; a real route records `route_provider=osrm_self_hosted`, `used_fallback=false` | 🟢 **CLOSED 2026-05-25** | `prove_osrm_runtime.py` exit 0 on 3 Portland routes; real OSRM pytest passed. Evidence: `docs/P0_G2_OSRM_RUNTIME_PROOF_01.md` |
| **E2E** | Live-stack `session-recovery.spec.ts` passes (3 STATE × refresh + skeleton scenario) | 🟢 **CLOSED 2026-05-25** | Exit code 0 on this machine; 3 passed + 1 flaky on retry (test-timing, not product). Real bug fixed: `SilMapLayer.jsx` heat-layer race that crashed cockpit to ErrorBoundary. Evidence: `docs/HALFAPP_DELIVERY_BLOCKER_CLOSURE_PASS_01.md` |
| **G3** | Owner courier day: full rider → driver → complete loop on owner's own vehicle (or controlled local area) | 🔴 OPEN | Owner walks `docs/OWNER_COURIER_DAY_WALKTHROUGH_01.md` and fills sign-off in `docs/OWNER_COURIER_DAY_REPORT_01.md`. AI agents are forbidden from marking this GO. |

**Why Tier 1 must come first:** until these four are GO, every claim about real-world fitness is unproven. Skipping them and starting Tier 2 work is wasted effort if a foundational gate fails.

---

## Tier 2 — Legal / business prerequisites (outside repo scope)

| ID | Blocker | Status | Closes with |
|----|---------|--------|-------------|
| **L1** | Business entity (LLC / Pvt Ltd / equivalent) registered in operating jurisdiction | 🔴 OPEN | Certificate of incorporation on file |
| **L2** | Tax registration (GST / VAT / sales tax appropriate to jurisdiction) | 🔴 OPEN | Tax ID issued by authority |
| **L3** | Trade / operating license appropriate to the service (transport network company, courier, delivery, etc.) | 🔴 OPEN | License document issued by city/state |
| **L4** | Terms of Service + Privacy Policy + Driver/Courier Agreement, counsel-reviewed | 🔴 OPEN | Signed legal review note |
| **L5** | Data-protection registration (GDPR / India DPDP / etc. as applicable) | 🔴 OPEN | Registration acknowledgement |

**Closure rule:** counsel sign-off only. Internal copy does not close a legal blocker.

---

## Tier 3 — Driver / courier operating prerequisites

| ID | Blocker | Status | Closes with |
|----|---------|--------|-------------|
| **D1** | Driver license verification process | 🔴 OPEN | Vendor contract OR documented manual KYC flow |
| **D2** | Background check process | 🔴 OPEN | Vendor contract OR documented manual process with consent capture |
| **D3** | Vehicle verification (registration, fitness, insurance certificate per driver vehicle) | 🔴 OPEN | Document collection flow + review SLA |
| **D4** | Commercial / for-hire insurance on each operating vehicle (personal cover does not apply to platform trips) | 🔴 OPEN | Insurance certificate per driver on file |
| **D5** | Document expiry tracking | 🔴 OPEN | Implemented + admin alert tested |
| **D6** | Driver onboarding flow with KYC | 🔴 OPEN | End-to-end UI + backend |

---

## Tier 4 — Insurance and liability

| ID | Blocker | Status | Closes with |
|----|---------|--------|-------------|
| **I1** | Platform operator liability cover | 🔴 OPEN | Active insurance policy on file |
| **I2** | Driver gap insurance (Period 1/2/3 if applicable) | 🔴 OPEN | Active policy on file |
| **I3** | Rider/customer protection cover | 🔴 OPEN | Active policy on file |
| **I4** | Incident reporting + escalation policy | 🔴 OPEN | Written SOP + dry-run |

---

## Tier 5 — Payments and payout (code + legal + financial)

| ID | Blocker | Status | Closes with |
|----|---------|--------|-------------|
| **P1** | PSP merchant account (Stripe / Razorpay / equivalent) | 🟡 CODE PATH EXISTS, NO MERCHANT | Live merchant account + production keys; first real charge captured |
| **P2** | Real customer charge → settlement → driver payout chain | 🔴 OPEN | One live small-value round trip with reconciliation evidence |
| **P3** | Tax invoice / receipt with legally required fields | 🟡 PARTIAL (audit receipt exists) | Regulatory invoice format reviewed by counsel |
| **P4** | Refund and dispute handling SOP | 🔴 OPEN | Written process + UI + first dry-run |
| **P5** | Driver payout schedule + statement | 🟡 OBLIGATION ROWS ONLY | Real payout executed + statement delivered |
| **P6** | PCI scope assessment | 🔴 OPEN | Counsel/security review note |

---

## Tier 6 — Privacy, security, data

| ID | Blocker | Status | Closes with |
|----|---------|--------|-------------|
| **S1** | `SECRET_KEY` boot guard in production | 🟢 CLOSED | `backend/production_guards.py` + `tests/test_production_guards.py` |
| **S2** | Token rotation + revocation | 🟢 CLOSED | Migration 0016 + `tests/test_auth_refresh_rotation.py` + `settings-logout-all-btn` |
| **S3** | CORS allowlist enforced in production | 🟢 CLOSED | `tests/test_production_guards.py` |
| **S4** | Structured request logging with correlation IDs | 🟢 CLOSED | `backend/middleware/request_logging.py` + `tests/test_request_logging_middleware.py` |
| **S5** | Encryption at rest for PII | 🔴 OPEN | Production DB config: TDE / column-level encryption documented |
| **S6** | Backup + tested restore | 🔴 OPEN | Daily backup automated + one verified test restore |
| **S7** | Right-to-erasure / data export endpoints | 🔴 OPEN | Implemented + reviewed by counsel |
| **S8** | Audit log of admin actions on personal data | 🔴 OPEN | Implemented + tested |
| **S9** | Threat model + penetration test | 🔴 OPEN | Third-party report on file |
| **S10** | Secret rotation policy | 🔴 OPEN | Written policy + first rotation executed |

---

## Tier 7 — Hosting and operations (deployment, outside source tree)

| ID | Blocker | Status | Closes with |
|----|---------|--------|-------------|
| **H1** | Production backend host (app servers + managed Postgres) | 🔴 OPEN | URL + uptime monitor + access policy |
| **H2** | Production driver-app hosting (CDN / static) | 🔴 OPEN | Same |
| **H3** | Production rider-app hosting | 🔴 OPEN | Same |
| **H4** | Domain + TLS + HSTS | 🔴 OPEN | TLS report (SSL Labs A or better) |
| **H5** | Centralized log aggregation consuming `halfapp.request` | 🔴 OPEN | First production request visible in aggregator |
| **H6** | Metrics + alerts (uptime, p95 latency, error rate) | 🔴 OPEN | Alert fires correctly on a drill |
| **H7** | On-call + incident runbook | 🔴 OPEN | Written runbook + one dry-run |
| **H8** | Daily DB backup + tested restore | 🔴 OPEN | See S6 |
| **H9** | Staging environment mirroring production | 🟡 DOCUMENTED, NOT PROVEN | Staging URL + last-deployed-from-main timestamp |

---

## Tier 8 — Mobile / device readiness

| ID | Blocker | Status | Closes with |
|----|---------|--------|-------------|
| **M1** | iOS readiness (App Store Connect account, app ID, provisioning, review compliance) | 🔴 OPEN | App in TestFlight |
| **M2** | Android readiness (Play Console account, signing key, review compliance) | 🔴 OPEN | App in internal testing track |
| **M3** | App-store privacy nutrition labels written | 🔴 OPEN | Labels submitted with build |
| **M4** | Push notification certificates (APNs / FCM) | 🔴 OPEN | Test push delivered to device |
| **M5** | Background location handling that survives store review | 🔴 OPEN | Design doc + spike build |
| **M6** | Crash reporting (Sentry / Crashlytics) | 🔴 OPEN | First crash captured in dashboard |

---

## Tier 9 — Product completeness before public

| ID | Blocker | Status | Closes with |
|----|---------|--------|-------------|
| **PR1** | Real-time presence (WebSocket or SSE, not polling) | 🟡 PARTIAL (SSE on pool only) | Full presence stream on driver presence |
| **PR2** | Live ETA from proven routing | 🟡 PARTIAL | OSRM runtime GO; ETA product wiring/SLA still not public-launch ready |
| **PR3** | Background location with battery-aware tracking | 🔴 OPEN | Implemented + measured battery cost |
| **PR4** | Rider support flow that reaches a human | 🟡 IN-APP HELP ONLY | Real support channel + SLA |
| **PR5** | Driver earnings statement (per period, downloadable) | 🟡 PARTIAL | PDF / CSV export validated |
| **PR6** | Trip dispute flow | 🔴 OPEN | UI + ops queue |
| **PR7** | Cancellation policy enforcement (fees, blocks) | 🔴 OPEN | UI + backend policy |
| **PR8** | Accessibility audit (WCAG basics) | 🔴 OPEN | Audit report |

---

## What is closed today (proven, with evidence)

| ID | Blocker | Evidence |
|----|---------|----------|
| **S1** | Production SECRET_KEY guard | `backend/production_guards.py`, `tests/test_production_guards.py` |
| **S2** | Token rotation + revocation | Migration 0016, `tests/test_auth_refresh_rotation.py`, `settings-logout-all-btn` |
| **S3** | CORS hardening | `tests/test_production_guards.py` |
| **S4** | Structured request logging | `backend/middleware/request_logging.py` (7 tests pass) |
| **G1** | PostgreSQL Alembic + claim-race proof | `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md`, `docs/P0_G7_ALEMBIC_POSTGRES_PROOF_01.md` |
| **G2** | OSRM runtime proof | `docs/P0_G2_OSRM_RUNTIME_PROOF_01.md`, `docs/SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md` |
| **Internal product completion** | All 18 audited areas | `docs/HALFAPP_INTERNAL_PRODUCT_COMPLETION_PASS_01.md` (owner-accepted 2026-05-25) |
| **E2E (Tier 1)** | Live-stack session recovery on this machine | `docs/HALFAPP_DELIVERY_BLOCKER_CLOSURE_PASS_01.md` (2026-05-25); real bug fixed in `SilMapLayer.jsx` |

That is the entire closed list. Anything not on it is open by default.

---

## How this doc is maintained

- Closing a blocker = move the row, set status 🟢, link evidence. Never just edit wording.
- Adding a blocker = append to the right tier; do not re-number existing IDs.
- This file replaces the inline "blockers" lists previously scattered across reports. New reports should link here instead of restating.
