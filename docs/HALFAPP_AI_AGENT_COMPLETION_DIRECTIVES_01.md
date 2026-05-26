# HalfApp Driver — AI Agent Completion Directives (Phase: Close Gates → Delivery-Complete → One Fork)

**Document ID:** `HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01`  
**Date:** 2026-05-25  
**Audience:** AI coding agent (Claude Code, Cursor, etc.) executing on the `halfapp-driver` repo  
**Source of truth:** `docs/HALFAPP_PROGRAM_BRAIN_COMPREHENSIVE_REPORT_06.md` (this document operationalizes its Part XIV playbook)  
**Companion docs you must read before starting:**

1. `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md` — closed lanes, do-not-touch list
2. `docs/CURRENT_TRUTH.md` — short truth table
3. `docs/HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md` — Phase 1–4 DONE state
4. `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md` — owner courier day
5. `docs/PRODUCT_BOUNDARY_STAGE0.md` — forbidden claims

---

## 0. How to use this document

You are an AI coding agent working on a **delivery driver application** (single pickup → single dropoff, courier-side focus). The repo uses legacy "ride" vocabulary but the product is **delivery**, not passenger ride-hailing.

**Execution rules:**

- Work tasks **in order** within a priority tier (P0 → P1 → P2). Do not skip ahead.
- For each task: read the listed files first, plan the change, implement, run the acceptance command, then update the truth doc.
- If acceptance fails, **fix or stop and report** — do not mark complete.
- Never violate the non-negotiables in §4.
- After each completed task, append a row to `docs/CURRENT_TRUTH.md` and write a short `*_REPORT.md` in `docs/` with the proof.

**Reporting format expected after each task:**

```
TASK: <id>
STATUS: GO | NO_GO | PARTIAL
COMMAND RUN: <exact command>
PROOF: <test names / file lines / log excerpt>
DOCS UPDATED: <files>
GOVERNANCE CHECK: assert-no-money-claims ✓ | assert-no-ai-providers ✓ | assert-prod-truth ✓
NEXT TASK: <id or "BLOCKED: reason">
```

---

## 1. Priority 0 — Close the gates (G1–G6 from Report v5 Part XIII)

See gate reports:

| Gate | Report |
|------|--------|
| G1 | `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_01.md` |
| G2 | `docs/SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md` |
| G3 | `docs/OWNER_COURIER_DAY_REPORT_01.md` (owner sign-off) |
| G4 | `docs/DOSSIER_PATH_DECISION_01.md` |
| G5 | `docs/P0_G5_SURFACE_FREEZE_REPORT_01.md` |
| G6 | `docs/P0_G6_SYSTEM_TRUTH_RECONCILIATION_REPORT_01.md` |

### P0-G1: PostgreSQL as default dev DB + claim-race CI proof

**Goal:** Move the project off SQLite-first development. Prove the atomic claim lock under real concurrency.

**Files:** `docker-compose.yml`, `backend/.env.example`, `backend/README.md`, `.github/workflows/halfapp-driver-ci.yml`, `tests/test_postgres_claim_race_proof_01.py`

**Acceptance:** `docker compose up -d postgres`; `pytest -k claim_race` on PG; CI job `postgres-claim-race`; 1 winner / 9×409.

**Do not:** Change claim lock SQL (closed lane).

---

### P0-G2: OSRM runtime proof (NO_GO → GO)

**Goal:** `used_fallback=false` on Portland routes when OSRM is up.

**Files:** `docker-compose.yml` (osrm), `scripts/prove_osrm_runtime.py`, `tests/test_routing_service_real_osrm.py`, `docs/SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md`

**Acceptance:** OSRM up; `prove_osrm_runtime.py` exit 0; real OSRM test passes when URL set.

**Do not:** Remove haversine fallback.

---

### P0-G3: Owner courier day (single E2E walkthrough)

**Goal:** Human owner completes full loop once on staging.

**Files:** `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md`, `docs/OWNER_COURIER_DAY_REPORT_01.md`

**Acceptance:** Runbook accurate; owner fills report. **AI must not mark G3 GO.**

---

### P0-G4: Dossier Path A vs B decision

**Goal:** Decision doc only — no execution until owner picks.

**Files:** `docs/DOSSIER_PATH_DECISION_01.md`

---

### P0-G5: Surface-freeze / OpenAPI drift tests green

**Goal:** `test_active_route_surface_*` passes; drift detector stays strict.

**Files:** `backend/tests/test_active_route_surface.py`, `scripts/print_active_routes.py`

---

### P0-G6: SYSTEM_TRUTH.md reconciliation

**Goal:** Align with Phase 1–4 checklist (rider-app, ops-app, simulated payments).

**Files:** `docs/SYSTEM_TRUTH.md`, `docs/CURRENT_TRUTH.md`

---

## 2. Priority 1 — Delivery-complete the courier experience

**Run only after all P0 gates are GO.**

### P1.1: Push notifications — **NOT STARTED** (blocked on P0)

### P1.2: Session recovery mid-job — **TODO** (see `docs/P1_2_SESSION_RECOVERY_VERDICT_01.md`)

### P1.3: Delivery vocabulary pass (UI copy only) — **NOT STARTED**

### P1.4: Stale presence policy — **NOT STARTED**

---

## 3. Priority 2 — One fork at a time

Do not start until P0 + P1 courier-complete items are GO. Pick **one**: proof-of-delivery, merchant payload, real Stripe pilot, external courier beta.

---

## 4. Non-negotiables (all tiers)

- Backend authority for job state, presence, claims, pricing.
- No "paid to your bank" / wallet / instant-pay marketing (`assert-no-money-claims.mjs`).
- No LLM on dispatch/pricing/lifecycle product path (`assert-no-ai-providers.mjs`).
- No production mock bypass (`assert-prod-truth.mjs`).
- Driver-app must not call dossier `/supply`, `/demand`, `/trip`.
- Do not reopen AUTH-001, RIDE-001/002/003, DRIVER-002 without rescope.
- Allowed honest framing: **auditable partial delivery execution with explicit blocked states**.

---

## 5. Gate status snapshot (2026-05-25 agent pass)

| Gate | Status |
|------|--------|
| G1 | **GO** — fresh PostgreSQL 16 `alembic upgrade head` + claim-race proof passed locally — `P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md` |
| G2 | **GO** — `prove_osrm_runtime.py` exit 0 and real OSRM backend tests passed — `P0_G2_OSRM_RUNTIME_PROOF_01.md` |
| G7 | **GO** — fresh PostgreSQL 16 Alembic proof passed — `P0_G7_ALEMBIC_POSTGRES_PROOF_01.md`, `ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md` |
| G3 | **PENDING_OWNER** — template only |
| G4 | **GO** — decision doc written; execution deferred |
| G5 | **GO** — surface tests pass |
| G6 | **GO** — `SYSTEM_TRUTH.md` reconciled |

**Overall P0:** **PARTIAL_GO** — remaining gate is G3 owner courier day; then agent P1.1 (push, migration 0036).
