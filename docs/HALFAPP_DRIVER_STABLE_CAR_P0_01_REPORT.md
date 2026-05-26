# HALFAPP_DRIVER_STABLE_CAR_P0_01 — Report

**Task:** `HALFAPP_DRIVER_STABLE_CAR_P0_01`  
**Date:** 2026-05-25  
**Scope:** P0 stability only — prove the **stable delivery execution car**. No P1/P2 features (push, POD, merchant payload, real PSP, batching, ML dispatch, full marketplace).

**Long-term direction:** `docs/HALFAPP_PROGRAM_BRAIN_COMPREHENSIVE_REPORT_05.md`, `docs/HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md` — **not executed in this task.**

---

## Overall verdict

| Verdict | Meaning |
|---------|---------|
| **PARTIAL_GO** | The **delivery execution car** is proven on SQLite + automated API spine (request → complete → receipt → ops). Session resilience and deployment sanity are **GO** at code/test level. **PostgreSQL claim-race** and **OSRM runtime** are **not closed in this environment** — prior Postgres proof and code-path proofs apply; runtime OSRM blocked (no Docker / no listener on `:5000`). |

**Do not treat PARTIAL_GO as production-ready staging.** Close G1 and G2 on an operator host with PostgreSQL + Docker OSRM, then re-run this report’s verification commands.

---

## Stable car definition (what we proved)

End-to-end **delivery job** path:

```text
requester creates job (POST /rides/)
  → driver accepts (or auto-assign when flagged)
  → arrive pickup
  → start
  → complete
  → requester receipt (GET /rides/{id}/payment)
  → ops visibility (GET /admin/rides, GET /admin/rides/{id})
```

**Terminology:** `Ride` = delivery job; `rider-app` = requester; `driver-app` = courier. See Report 05 §0.

---

## P0 gate results

### Gate 1 — PostgreSQL claim-race proof

| Item | Result |
|------|--------|
| **Verdict** | **PARTIAL_GO** |
| Test | `backend/tests/test_postgres_claim_race_proof_01.py` (`pytest -m postgres_claim_race_proof`) |
| This run | **Skipped** — `DATABASE_URL` not set in agent environment |
| Prior proof | **GO** — `docs/HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01_REPORT.md` (2026-05-22): 10 drivers, 1×200, 9×409 structured conflict, no duplicate winner |
| SQLite proxy | **GO** — `tests/test_ride_claim_lock_concurrency.py` (10 drivers, same 409 shape) |

**Required behavior (unchanged):**

- Multiple drivers `POST /drivers/accept-ride/{id}` concurrently  
- Exactly **one** `200` with `status=accepted`  
- Losers: **409** with `detail.claim_result == "lost"`, `truth_status == "backend_conflict"`  

**Operator command to close gate to GO:**

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://halfapp:****@localhost:55432/halfapp_test"
$env:SECRET_KEY = "pytest-halfapp-test-secret-32chars-minimum"
$env:HALFAPP_ENV = "test"
cd backend
py -3.11 -m pytest -q tests/test_postgres_claim_race_proof_01.py -s
```

**Caveat (documented in prior report):** Full `alembic upgrade head` on PostgreSQL may still fail on SQLite-specific DDL; claim-race proof used ORM `create_all` patch. Production needs Alembic/DDL reconciliation — separate from dispatch lock correctness.

---

### Gate 2 — OSRM runtime proof

| Item | Result |
|------|--------|
| **Verdict** | **NO_GO** (runtime) · **GO** (code + honest fallback) |
| Runtime this run | OSRM **not listening** at `http://127.0.0.1:5000`; Docker **not in PATH** on proof host |
| Evidence | `backend/runtime_evidence/ride_ai_route_grounding_runtime_proof.json` — `PARTIAL_GO_ROUTE_GROUNDING_CODE_COMPLETE_RUNTIME_PROOF_PENDING` |
| Code tests | **11 passed, 4 skipped** — `test_osrm_self_hosted_routing.py`, `test_ride_route_grounding.py`, `test_osrm_runtime_integration.py` (skipped without `OSRM_RUNTIME_URL`) |
| Fallback honesty | When OSRM down + `ROUTING_FALLBACK_ENABLED=true`, rides stamp `route_provider=haversine_fallback`, `used_fallback=true` — must not claim road-network truth |

**Required for GO (runtime):**

1. `docker compose up -d` in `docker/osrm-portland/`  
2. `OSRM_BASE_URL=http://127.0.0.1:5000`, `ROUTING_PROVIDER=osrm_self_hosted`  
3. Accept/complete a job; API fields: `route_provider=osrm_self_hosted`, `route_used_fallback=false`  
4. Stop OSRM; repeat — expect `haversine_fallback` and honest UI advisory  

**Operator commands:**

```powershell
cd docker/osrm-portland
docker compose up -d
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
$env:OSRM_RUNTIME_URL = "http://127.0.0.1:5000"
cd backend
py -3.11 -m pytest tests/test_osrm_runtime_integration.py -q
powershell -ExecutionPolicy Bypass -File ..\scripts\proof-ride-ai-route-grounding-runtime.ps1
```

See: `docs/SELF_HOSTED_ROUTING_PROOF_V0_2_STATUS.md`, `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md` §7.

---

### Gate 3 — Driver session resilience

| Item | Result |
|------|--------|
| **Verdict** | **GO** (backend + unit) · **PARTIAL_GO** (full browser E2E not re-run here) |

**Backend — GO**

| Capability | Proof |
|------------|-------|
| Mid-job recovery payload | `GET /drivers/me/active-ride` — `tests/test_active_ride_recovery.py` (**2 passed**) |
| Idempotent lifecycle POSTs | `Idempotency-Key` replay — `tests/test_driver_ride_idempotency_slice03.py` (**3 passed**) |
| Parallel key in-flight → 409 | `idempotency_in_progress` in same file |
| Claim conflict structure | `tests/test_ride_claim_lock_concurrency.py` |
| Ride pool SSE framing | `tests/test_ride_pool_sse.py` |

**Frontend — GO (unit)**

| Capability | Proof |
|------------|-------|
| `resilientFetch` + idempotency keys | `driver-app/tests/unit/slice03Resilience.test.js` |
| `useActiveRide` hook | `driver-app/src/hooks/useActiveRide.js` |
| Cockpit skeleton on load | `CockpitSkeleton.jsx`, `COCKPIT_SESSION_RECOVERY_V0_1.md` |

**Playwright (documented, not executed this run)**

- `driver-app/tests/session-recovery.spec.ts` — refresh @ accepted / arrived / in_progress  
- `driver-app/tests/sse-session-recovery.spec.ts` — SSE fan-out + hard refresh  

```powershell
cd driver-app
npm run test:e2e:ride-flow -- tests/session-recovery.spec.ts
npm run test:e2e:ride-flow -- tests/sse-session-recovery.spec.ts
```

**Note:** `npm test` in driver-app: **149/150 passed** — one pre-existing failure in `mapProvider v0.1` (display defaults), **not** in session/idempotency lane.

---

### Gate 4 — Deployment sanity

| Item | Result |
|------|--------|
| **Verdict** | **GO** |

**Checks (this run):**

```powershell
cd backend
py -3.11 scripts/verify_p0_deployment_sanity.py
# DEPLOYMENT SANITY PASS
```

| Check | Status |
|-------|--------|
| Ports 8000 / 3022 / 3023 / 3024 documented in runbook | OK |
| Vite `strictPort` 3022, 3023, 3024 | OK |
| `.env.example` CORS + OSRM + dispatch flags | OK |
| Dev CORS unions 3022–3024 | OK |

**Repeatable local stack** (`docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md`):

| Service | Port | Command |
|---------|------|---------|
| API | 8000 | `uvicorn main:app --reload --host 127.0.0.1 --port 8000` |
| Driver | 3022 | `cd driver-app && npm run dev` |
| Requester | 3023 | `cd rider-app && npm run dev` |
| Ops | 3024 | `cd ops-app && npm run dev` |

Proxy: set `VITE_API_PROXY_TARGET=http://127.0.0.1:8000` when apps call `/api`.

---

## Stable car API proof (new in this task)

**Test:** `backend/tests/test_stable_car_p0_01.py`  
**Result:** **1 passed** (SQLite)

Asserts:

- Rider `POST /rides/` → driver accept → arrive → start → complete  
- `GET /drivers/me/active-ride` during job  
- Rider `GET /rides/{id}` → completed  
- Rider `GET /rides/{id}/payment` → captured/authorized row  
- Admin `GET /admin/rides` + `GET /admin/rides/{id}` → completed + lifecycle_events  

**Runbook bundle (22 passed):**

```powershell
cd backend
py -3.11 scripts/owner_runbook_verify.py
# RUNBOOK API PASS
```

Includes: stable car, ride flow, rider auth, rider SSE, ops phase 4, active ride, idempotency, claim lock, ride pool SSE.

---

## Explicitly out of scope (not started)

Per task directive — **no work** in this lane on:

- Push notifications  
- Proof of delivery (photo/signature/PIN)  
- Merchant / order payload  
- Real PSP / Stripe product  
- Multi-stop batching  
- ML / LLM dispatch mutation  
- Full marketplace / external beta  

Ride AI dispatch panel remains **advisory only** — not part of stable-car proof.

---

## Gate summary table

| # | Gate | Verdict | Blocker to full GO |
|---|------|---------|-------------------|
| 1 | PostgreSQL claim-race | **PARTIAL_GO** | Re-run `test_postgres_claim_race_proof_01.py` on CI/staging PG |
| 2 | OSRM runtime | **NO_GO** (runtime) | Docker OSRM up + runtime proof script exit 0 |
| 2b | OSRM / fallback honesty (code) | **GO** | — |
| 3 | Session resilience | **GO** (API/unit) | Optional: re-run Playwright session specs |
| 4 | Deployment sanity | **GO** | — |
| — | Stable car API spine | **GO** | Owner browser sign-off still recommended |

---

## Recommended next actions (P0 only)

1. **Operator host:** Start Postgres + set `DATABASE_URL` → run postgres claim-race test → update this report Gate 1 to **GO**.  
2. **Operator host:** `docker/osrm-portland` → runtime proof → update Gate 2 to **GO**.  
3. **Owner:** One pass `OWNER_INTERNAL_TEST_RUNBOOK_01.md` in browser (requester + driver + ops).  
4. **Optional:** `npm run test:e2e:ride-flow` session-recovery specs on ride-flow stack ports.  
5. **Do not start P1** until overall **GO** on gates 1–2 or explicit accept of PARTIAL_GO for staging-only pilot.

---

## Artifacts added (this task)

| Path | Role |
|------|------|
| `backend/tests/test_stable_car_p0_01.py` | Stable car API integration test |
| `backend/scripts/owner_runbook_verify.py` | Runbook pytest bundle (referenced by runbook §6) |
| `backend/scripts/verify_p0_deployment_sanity.py` | Ports/CORS/env checks |
| `docs/HALFAPP_DRIVER_STABLE_CAR_P0_01_REPORT.md` | This report |

---

## Verification log (2026-05-25, agent environment)

| Command | Result |
|---------|--------|
| `py -3.11 scripts/verify_p0_deployment_sanity.py` | PASS |
| `py -3.11 scripts/owner_runbook_verify.py` | **22 passed** — RUNBOOK API PASS |
| `py -3.11 -m pytest tests/test_stable_car_p0_01.py …` (resilience bundle) | **12 passed** |
| `py -3.11 -m pytest tests/test_osrm_*.py tests/test_ride_route_grounding.py` | **11 passed, 4 skipped** |
| `test_postgres_claim_race_proof_01.py` | Skipped (no `DATABASE_URL`) |
| OSRM `:5000` / Docker | Not available |
| `driver-app npm test` | 149 pass, 1 fail (`mapProvider` — unrelated) |

---

**Signed verdict:** **PARTIAL_GO** — stable delivery car is **proven in code and SQLite**; **PostgreSQL** and **OSRM runtime** gates remain open for the operator environment.
