# HalfApp Driver — Sprint-to-Drivers Directives (3 months)

**Document ID:** `HALFAPP_SPRINT_TO_DRIVERS_DIRECTIVES_01`  
**Date:** 2026-05-25  
**Audience:** AI coding agent executing on `halfapp-driver`  
**Source of truth:** `docs/HALFAPP_PROGRAM_BRAIN_COMPREHENSIVE_REPORT_06.md` (supersedes older big-picture)  
**Companion docs (must read):**
1. `docs/HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md` (style + execution discipline)
2. `docs/PRODUCT_BOUNDARY_STAGE0.md` (forbidden claims / honest product framing)
3. `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md` (closed lanes)
4. `docs/CURRENT_TRUTH.md` (current state + gate matrix)
5. `docs/HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md` (Phase DONE definitions)
6. `docs/P1_2_SESSION_RECOVERY_VERDICT_01.md` (session recovery: backend GO, E2E TODO)

---

## 0. How to use this document

You are executing a **3-month sprint** toward “Sprint-to-Drivers” targets (50+ drivers at first launch, native push, POD, Connect payouts, TestFlight beta, App Store submission).

**Rule: do not guess decisions.** Any item marked **BLOCKED: answer decision** must stop until the program owner answers.

**Rule: do not reopen closed lanes.** If a change would touch a closed lane from `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md`, stop and request rescope.

**After each task (whether code or docs):**
- Update `docs/CURRENT_TRUTH.md` if you materially change shipped behavior or “go/no-go” status.
- Create a short proof artifact in `docs/` named like `docs/*SPRINT_TO_DRIVERS_*_REPORT.md` (one page max).
- Include a “Governance check” line in your report using the checks listed in §6.

---

## 1. Sprint guardrails (non-negotiables)

These are the same invariants as the Phase playbook, scoped to this sprint’s delivery goals:

1. **Backend authority is the source of truth.** Driver UI must render facts from backend endpoints or label them as local/mock-only.
2. **No money-claim lies.** Never present “paid to your bank / instant pay / wallet balance” as truth without provider-evidenced backend state + docs/guards.
3. **No client-side dispatch.** Job assignment/claim winner selection must be backend-authoritative.
4. **No OSRM production claims without runtime proof.** Fallback honesty must remain honest if OSRM is down.
5. **No closed-lane edits without rescope.** Do not modify claim lock SQL, lifecycle transition guards, cascade logic, driver approval gate behavior, or production `SECRET_KEY` behavior.
6. **No “AI dispatch” on the product path.** Ride AI advisory is allowed only as advisory/non-mutating (and only where already implemented).
7. **Honesty in documentation and UI.** If a capability is behind a feature flag, treat it as demo-only or pilot-only and label accordingly.

References:
- Forbidden claims language: `docs/PRODUCT_BOUNDARY_STAGE0.md`  
- Closed lanes: `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md`  
- Truth discipline: `docs/CURRENT_TRUTH.md`  

---

## 2. Sprint outcomes (what “done” means)

### Product outcomes (owner-acceptance)
- **Launch target:** enable a first launch with **50+ drivers** (public beta or commercial beta).
- **Speed target:** drivers using the system in **3 months** (not “prototype users” only).
- **Native strategy (iOS):** Capacitor wrap → TestFlight → App Store.
- **Courier loop completeness:** driver online → receives assignment → completes delivery → sees receipt/earnings projection → ops/admin can monitor/cancel/resolve disputes.

### Sprint execution outcomes (agent acceptance)
- All backend tests are green on this checkout for the targeted scope (see §4 tasks).
- P0 “proof lanes” are closed where human runtime is required (see §3.1).
- Production deployment documentation exists with concrete env vars + smoke tests.

---

## 3. Sprint phases by month

### Month 1 — Foundation (close P0 + fix test breaks + production scaffolding + iOS skeleton)
Focus:
1. Close P0 gates that block production-like readiness (`G1`, `G2`, `G7`) and coordinate `G3` (owner courier day).
2. Fix the **current 4 failing pytest tests** (remove ambiguity by producing a failure inventory doc).
3. Finish `P1.2` session recovery E2E (backend is already GO; Playwright TODO).
4. Production-grade hosting scaffolding (managed Postgres, OSRM server, domain+TLS) as runbooks + env var mapping.
5. Set up Apple developer account planning and add Capacitor integration so an iOS build pipeline is unblocked.

### Month 2 — Driver-complete (native push + POD + Connect payouts + TestFlight beta)
Focus:
1. Native push via APNs (through Capacitor).
2. Proof-of-delivery (P2.A).
3. Real Stripe Connect for driver payouts (P2.C).
4. TestFlight beta with 5–10 internal testers and collect feedback.

**Important governance conflict check:** the Phase playbook’s “one fork at a time” rule (from `docs/HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md`) conflicts with “POD + Connect payouts both in Month 2.”  
**BLOCKED: answer decision in §8 before starting either POD or Connect tasks.**

### Month 3 — Launch (App Store submission + onboarding + background checks + scale)
Focus:
1. App Store submission and driver onboarding flow.
2. Background checks integration (Checkr or similar).
3. Expand to 50+ drivers, iterate, and harden operational readiness.

---

## 4. Tasks (with file paths, acceptance criteria, and governance guardrails)

### Month 1 — tasks (foundation)

#### M1-T01: Produce pytest failure inventory + fix 4 failing tests
**Files touched (likely):**
- `backend/` tests (whatever fails)
- create: `docs/PYTEST_FAILURE_INVENTORY_01.md`
**Acceptance criteria:**
1. Run from repo root:
   ```powershell
   cd backend
   py -3.11 -m pytest -q --tb=no
   ```
2. Identify the 4 failing tests, document them in `docs/PYTEST_FAILURE_INVENTORY_01.md` with:
   - failing test nodeids
   - top assertion message
   - suspected root-cause category (e.g. schema drift, fixture mismatch, env gating, UI contract mismatch)
3. Fix failures so `py -3.11 -m pytest -q --tb=no` returns **zero failures**.
**Governance guardrails:**
- No changes to forbidden/closed lanes (auth claim middleware, claim lock SQL, lifecycle transition guards, approval gate behavior, production secret guards).
- If a failure is caused by schema drift, fix via migrations/contract alignment—not by bypassing tests.
**Proof artifact:**
- `docs/*SPRINT_TO_DRIVERS_MONTH1_REPORT_01.md`

#### M1-T02: Finish P1.2 session recovery E2E (Playwright)
**Files:**
- `driver-app/tests/session-recovery.spec.ts`
- `driver-app/playwright.ride-flow.config.js` (or relevant Playwright config)
- `docs/P1_2_SESSION_RECOVERY_VERDICT_01.md`
**Acceptance criteria:**
1. Start the ride-flow E2E stack as per existing E2E docs (whatever your repo uses in `npm run test:e2e:ride-flow`).
2. Run the spec:
   ```powershell
   cd driver-app
   npm run test:e2e:ride-flow -- tests/session-recovery.spec.ts --reporter=line
   ```
3. Update `docs/P1_2_SESSION_RECOVERY_VERDICT_01.md`:
   - Backend lane already PASS; confirm E2E lane PASS.
   - Overall verdict becomes **GO** when all 3 checklist items pass.
**Governance guardrails:**
- Do not change backend ride lifecycle behavior; fix only session hydration/resume/UI state reconciliation.

#### M1-T03: Close P0-G1 on PostgreSQL (claim race proof)
**Files:**
- `backend/tests/test_postgres_claim_race_proof_01.py`
- `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md`
**Acceptance criteria:**
1. From repo root:
   ```powershell
   docker compose up -d postgres
   ```
2. Run:
   ```powershell
   cd backend
   py -3.11 -m pytest tests/test_postgres_claim_race_proof_01.py -q
   ```
3. Test passes with:
   - `successful_accepts == 1`
   - `structured_409_conflicts == 9`
**Governance guardrails:**
- Do not modify claim-lock code in this lane.

#### M1-T04: Close P0-G2 (OSRM runtime proof, no fallback for proof legs)
**Files:**
- `backend/scripts/verify_osrm_health.py`
- `backend/scripts/proof_osrm_portland_routes.py`
- `backend/tests/test_osrm_runtime_proof_portland.py`
- `docs/P0_G2_OSRM_RUNTIME_PROOF_01.md`
**Acceptance criteria (local):**
1. Start OSRM:
   ```powershell
   docker compose up -d osrm
   ```
2. Verify OSRM health:
   ```powershell
   cd backend
   py -3.11 scripts/verify_osrm_health.py
   ```
   Must exit 0 and print `OSRM_HEALTH_OK`.
3. Run runtime proof with strict non-fallback proof legs (Portland):
   ```powershell
   cd backend
   py -3.11 scripts/proof_osrm_portland_routes.py --strict --write-evidence
   ```
   Must exit 0 and print `VERDICT: GO — Portland OSRM runtime proof legs passed`.
4. (Optional but preferred) if you want test-level confirmation:
   ```powershell
   cd backend
   $env:HALFAPP_OSRM_RUNTIME_PROOF="1"
   py -3.11 -m pytest tests/test_osrm_runtime_proof_portland.py -q
   ```
**Governance guardrails:**
- No removal of haversine fallback behavior.
- No “road-network truth” claims when `used_fallback=true`.

#### M1-T05: Close P0-G7 on PostgreSQL (Alembic upgrade head)
**Files:**
- `backend/tests/test_alembic_postgres_upgrade_head.py`
- `docs/P0_G7_ALEMBIC_POSTGRES_PROOF_01.md`
**Acceptance criteria:**
1. Start postgres:
   ```powershell
   docker compose up -d postgres
   ```
2. Run:
   ```powershell
   cd backend
   py -3.11 -m pytest tests/test_alembic_postgres_upgrade_head.py -q
   ```
3. Test asserts Alembic version equals `0035_telemetry_retention_index`.
**Governance guardrails:**
- Do not rely on `create_all` for correctness.
- Fix schema drift via Alembic/migrations if needed.

#### M1-T06: Coordinate P0-G3 owner courier day (human-only sign-off)
**Files:**
- `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md`
- `docs/OWNER_COURIER_DAY_REPORT_01.md`
**Acceptance criteria:**
1. AI may run backend/driver smoke scripts to reduce owner burden, but must not mark G3 GO in docs.
2. Owner completes `OWNER_INTERNAL_TEST_RUNBOOK_01.md` loop and fills `OWNER_COURIER_DAY_REPORT_01.md`.
**Governance guardrails:**
- Explicitly human-only lane per directives.

#### M1-T07: Production-grade hosting scaffolding (managed Postgres + OSRM server + domain/TLS) as runbooks
**Files (must exist or be added):**
- existing: `docker-compose.yml` (local reference)
- existing: `docs/DEPLOY_ENV_VARS.md` (env contract)
- existing: `docs/DEPLOY_CORS_OBSERVABILITY_01.md` (logging + CORS)
- add: `docs/PRODUCTION_HOSTING_RUNBOOK_01.md`
- add: `docs/OSRM_PRODUCTION_DEPLOY_RUNBOOK_01.md`
**Acceptance criteria:**
1. Create the runbooks above with:
   - exact environment variables mapping (prod vs staging)
   - smoke tests to validate:
     - managed Postgres connectivity
     - Alembic upgrade head succeeds on a fresh database
     - OSRM runtime proof can run against the production OSRM endpoint
     - CORS origin allowlist behavior
2. Runbook must include concrete commands the owner can execute (including `py -3.11 -m pytest tests/test_alembic_postgres_upgrade_head.py -q` and `py -3.11 scripts/proof_osrm_portland_routes.py --strict` with env overrides).
**Governance guardrails:**
- Do not document any “unsafe SECRET_KEY” production values.
- Do not bypass production guards.

#### M1-T08: Add Capacitor integration to `driver-app` (iOS build pipeline unblocked)
**Files:**
- `driver-app/` (React/Vite project)
- add: `driver-app/capacitor.config.*` (or repo’s agreed naming)
- add: `driver-app/ios/` (generated) and `driver-app/android/` if you choose multi-platform now
- add: `docs/CAPACITOR_MOBILE_PIPELINE_RUNBOOK_01.md`
**Acceptance criteria (Windows reality-aware):**
1. Capacitor is installed and the repo has a consistent web build → native wrapper pipeline.
2. `npx cap sync` succeeds on the workstation (or in a Node environment) and generates native folders.
3. Document the iOS build steps and what must run on macOS build machine/CI (Xcode build and signing).
**Governance guardrails:**
- Keep all marketplace-truth claims backend-driven; the wrapper must not add fake dispatch or money logic.

---

### Month 2 — tasks (native push + POD + Connect beta)

#### M2-T01 (BLOCKED: decision): Confirm fork policy for Month 2 scope (POD + Connect)
**Files:**
- `docs/HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md` (reference conflict)
- add: `docs/SPRINT_GOVERNANCE_OVERRIDE_01.md`
**Acceptance criteria:**
1. Program owner answers the decision in §8 (at least):
   - whether this sprint is allowed to implement multiple “fork” capabilities at once
   - if not, which one is prioritized (POD OR Connect)
2. Write `docs/SPRINT_GOVERNANCE_OVERRIDE_01.md` stating:
   - exactly what is being overridden
   - what remains forbidden
   - the order of QA/verification gates to prevent forbidden-claim drift

#### M2-T02: Native push via APNs (Capacitor Push Notifications)
**Files (must wire / extend):**
- Driver push preferences already exist (in-app preference, not delivery):
  - `driver-app/src/context/DriverPreferencesContext.jsx`
  - `driver-app/src/components/DriverSettings.jsx`
  - `driver-app/src/utils/api.js` (uses `notif_push_enabled`)
- In-app notification truth (already implemented; push must not replace it):
  - `backend/routes/notifications.py` (ride alerts: `POST /notifications/driver/ride-alert`)
  - `backend/services/driver_in_app_notifications.py` (`notify_driver_in_app`)
- Native push delivery (new / to implement):
  - add: `backend/services/driver_push_notifications.py` (provider interface + APNs adapter)
  - add: `backend/models/driver_push_token.py` (store iOS device tokens, associated to driver)
  - add: driver endpoint to register tokens (e.g. `POST /drivers/me/push-tokens` in `backend/routes/drivers.py`)
  - add: driver-app Capacitor push glue (exact TS file name TBD under `driver-app/src/`)
**Acceptance criteria:**
1. Driver app registers for iOS push tokens and stores them backend-side with explicit driver association.
2. When a new ride is assigned/available (depending on what you choose), a push is emitted and the user sees a notification while app is backgrounded (manual test is acceptable in beta).
3. Push is behind a feature flag so production staging can be toggled without redeploy.
4. Update `docs/CAPACITOR_MOBILE_PIPELINE_RUNBOOK_01.md` with push setup + test steps.
**Governance guardrails:**
- Push must reflect backend-authoritative state transitions (no client-side inference).
- No money claims in notification copy.

#### M2-T03 (P2.A): Implement Proof-of-Delivery (POD) end-to-end (backend + driver UI)
**Files (must extend):**
- Ride completion truth entry point:
  - `backend/routes/drivers.py`:
    - `@router.post("/complete-ride/{ride_id}")` and `_complete_ride_impl(...)`
  - `backend/schemas/ride_pricing.py` (`CompleteRidePricingBody` is the current completion payload)
  - ensure POD fields do not bypass pricing lock / `financial_locked` semantics
- POD storage + persistence:
  - add: `backend/models/proof_of_delivery.py` (or similar) and wire into ORM imports
  - add: Alembic migration(s) to store POD fields on backend truth
- Driver UI completion flow:
  - `driver-app/src/components/MapHome.jsx` (calls `driverAPI.completeRide(...)` when transitioning to `COMPLETED`)
  - `driver-app/src/utils/api.js` (`completeRide(rideId, pricingBody)`)
  - add: a POD capture UI component (PIN/photo/signature per §8 decisions) and connect it to the completion call
- Tests:
  - add/update: backend tests covering:
    - completion blocked without required POD fields
    - POD stored and returned in ride audit / receipt payloads
**Acceptance criteria:**
1. Completing a ride requires POD payload in the chosen sprint mode.
2. Backend persists proof with an audit trail and blocks completion without required fields.
3. Driver UI displays stored proof status and backend-provided completion.
4. No multi-stop expansion; keep single pickup/single dropoff model.
**Governance guardrails:**
- Stage 0 explicitly forbids claiming POD as existing; since we are implementing it now, update `docs/PRODUCT_BOUNDARY_STAGE0.md` (and `docs/CURRENT_TRUTH.md`) once code + tests prove it.
- No payments/wallet/payout claims.

#### M2-T04 (P2.C): Implement real Stripe Connect payouts path (connect onboarding + payout visibility)
**Files (already exist; extend behavior / wire UI):**
- Connect onboarding routes:
  - `backend/routes/stripe_connect.py` (`/drivers/stripe/connect/status`, `/start`, `/refresh`)
  - `backend/services/stripe_connect.py` (Connect Express onboarding helpers)
- Stripe webhook ingestion (connect transfers/payouts):
  - `backend/routes/payments_webhooks.py` (webhook dispatcher; verifies signature)
  - `backend/services/stripe_payout_ingest.py` (stores `StripePayout` + maps transfers)
- Payout visibility/reconciliation logic:
  - `backend/services/payment_reconciliation.py` (`enrich_reconciliation_with_payouts`)
  - `backend/routes/drivers.py` (`GET /drivers/me/payouts`)
- Driver UI data plumbing:
  - `driver-app/src/utils/api.js` (`getStripeConnectStatus()`, `getPayouts()`)
  - `driver-app/src/components/DriverSettings.jsx` (shows Connect enablement)
  - `driver-app/src/components/EarningsVisibilityPanel.jsx` (renders provider payout section)
- Tests:
  - `backend/tests/test_stripe_connect_status.py`
  - `backend/tests/test_payout_ingestion_phase5.py`
**Acceptance criteria:**
1. Driver can complete Connect onboarding (manual or guided) in a sandbox environment.
2. Payout visibility reflects provider evidence (e.g. pending/available/failed), not marketing copy.
3. On a completed trip, payout obligations are represented according to the chosen product definition, but **never** claimed as “paid to your bank” unless provider evidence indicates so.
4. Update `docs/PRODUCT_BOUNDARY_STAGE0.md` and `docs/CURRENT_TRUTH.md` for any newly shipped payout visibility capabilities.
**Governance guardrails:**
- Do not introduce “sent to your bank” language in UI.
- Do not bypass provider evidence checks.

#### M2-T05: TestFlight beta (5–10 internal testers) + capture feedback loop
**Files:**
- add: `docs/TESTFLIGHT_BETA_PLAN_01.md`
- update: `docs/CAPACITOR_MOBILE_PIPELINE_RUNBOOK_01.md`
**Acceptance criteria:**
1. Build is uploaded to TestFlight for internal testers.
2. Beta checklist completed:
   - login/register
   - accept/complete with POD (if POD enabled by governance decision)
   - push notifications on new assignment (if push enabled by governance decision)
   - earnings/payout visibility copy matches backend truth
3. Collect and summarize feedback with categories: onboarding friction, reliability, POD correctness, push usefulness.
**Governance guardrails:**
- Beta copy must remain honest (“beta/internal test”), no launch claims.

---

### Month 3 — tasks (launch + onboarding + scale)

#### M3-T01: App Store submission
**Files:**
- add: `docs/APP_STORE_SUBMISSION_RUNBOOK_01.md`
**Acceptance criteria:**
1. Archive/build configured for App Store.
2. Submission checklist completed (privacy policy, app description, required disclosures).
3. Build passes basic review checks (manual or CI where possible).
**Governance guardrails:**
- Documentation in app store listing must match `docs/PRODUCT_BOUNDARY_STAGE0.md` (no forbidden claims).

#### M3-T02: Driver onboarding flow (native + backend) + agreement capture
**Files (likely):**
- `backend/routes/auth.py` / `backend/routes/admin_driver_approval.py` (depending on existing approval workflow)
- `backend/` agreement storage if you capture TNC/terms acceptance
- `driver-app/` onboarding screens
**Acceptance criteria:**
1. Driver onboarding creates a consistent backend state machine (submitted → pending review → approved or rejected).
2. Driver agreement acceptance and required disclosures are stored with timestamps.
3. Ops/admin can review and approve using existing admin patterns.
**Governance guardrails:**
- Must not auto-approve without compliance steps.

#### M3-T03 (background checks): Integrate Checkr (or similar provider)
**Files (likely):**
- add: `backend/services/background_checks.py`
- add: `backend/routes/background_checks.py` or extend an onboarding route
- add: webhook handler for status updates
- add: `backend/tests/test_background_checks_integration.py` (contract tests with stubs)
**Acceptance criteria:**
1. Background check request created for a driver onboarding flow.
2. Provider webhook updates backend status deterministically.
3. Driver UI shows “pending review” states without guessing.
**Governance guardrails:**
- Never claim “background check passed” without webhook-evidenced status.

#### M3-T04: Expand to 50+ drivers + operational hardening
**Files:**
- update: telemetry/retention docs if needed (`backend/tests/test_telemetry_retention.py`)
- add: `docs/OPERATIONAL_SCALE_PLAYBOOK_01.md`
**Acceptance criteria:**
1. Onboarding supports at least 50 active drivers in a simulated load test (if you can run load; otherwise manual pilot with monitoring).
2. Incident response and rollback steps exist:
   - what to do if push fails
   - what to do if POD submission fails
   - how to suspend/restore driver acceptance safely
3. Feedback loop with weekly iteration cadence.
**Governance guardrails:**
- Keep “backend truth” invariant; avoid client-side patches to ride lifecycle.

---

## 5. Non-technical blockers to start in parallel (start now)

These are not code tasks; they are gating for “real drivers” and compliance:

- Legal entity / contracts: set up the contracting structure that governs driver onboarding, liability, and payment obligations.
- Insurance: courier liability, general liability, and coverage for accidents + disputes (carrier-specific requirements).
- Background check vendor SOW + pricing + required driver data fields.
- Background check legal disclosures (privacy policy language, consent records).
- App Store readiness: Apple developer account, bundle id strategy, team roles, and app review artifacts (privacy policy, data collection, content rating).
- Terms and driver agreement: platform TOS, delivery terms, dispute process, termination terms, data retention clauses.
- Operational SOPs: onboarding review process, exception handling, fraud monitoring, and escalation contacts.
- Fraud / safety policy: what constitutes “completed delivery” proof integrity and how disputes are handled.
- Support tooling plan: where testers report issues, how logs are triaged, and which owners respond.

---

## 6. Governance checks for every task (what your reports must assert)

When you finish a task, your report must include these lines:

- `assert-no-money-claims ✓` (no “paid to your bank / wallet / instant pay” language added to driver UI or notifications without provable backend truth)
- `assert-no-ai-providers ✓` (no LLM/modeled dispatch/pickup/inference added to dispatch/pricing/lifecycle product path)
- `assert-prod-truth ✓` (no bypass enabling mock/guard bypass in production build; production guards remain enforced)
- `assert-backend-authority ✓` (driver UI changes read or write only through backend-authoritative endpoints)
- `assert-no-closed-lane-edits ✓` (if code touches a closed lane, you stop and request rescope)

If a check cannot be satisfied (e.g. you must add a capability that was forbidden previously), you must:
1. write an explicit doc update plan, and
2. update `docs/PRODUCT_BOUNDARY_STAGE0.md` + `docs/CURRENT_TRUTH.md` only after tests prove the capability.

---

## 7. Verification ritual (commands to run)

Use these after finishing a batch of changes (especially after fixing tests or touching backend endpoints):

### Backend full test pass (sprint scope)
```powershell
cd backend
py -3.11 -m pytest -q --tb=no
```

### Targeted P0 proof tests
```powershell
cd backend
py -3.11 -m pytest tests/test_postgres_claim_race_proof_01.py -q
py -3.11 -m pytest tests/test_alembic_postgres_upgrade_head.py -q
py -3.11 scripts/verify_osrm_health.py
py -3.11 scripts/proof_osrm_portland_routes.py --strict --write-evidence
```

### Driver app tests (minimum)
```powershell
cd driver-app
npm test
npm run build
```

### E2E session recovery
```powershell
cd driver-app
npm run test:e2e:ride-flow -- tests/session-recovery.spec.ts --reporter=line
```

---

## 8. Decision questions (answer before code starts)

Do not guess. Provide answers so the plan can be made concrete for environment + provider choices:

1. **Hosting provider:** AWS vs GCP vs Azure (or other). Must support managed Postgres + HTTPS + secrets management.
2. **Managed Postgres:** RDS vs Supabase vs self-managed. What is the preferred CI/CD workflow?
3. **OSRM runtime hosting:** Will OSRM run as:
   - a container behind a VPS (likely),
   - an internal network service,
   - or a third-party OSRM provider?
4. **OSRM extract city/region:** Portland only for the first launch, or multi-city?
5. **Domain + TLS:** domain name(s) and whether to use Cloudflare, AWS ACM, or another certificate manager.
6. **Stripe plan choice:** Which Connect product onboarding flow?
   - Stripe Connect (standard vs express),
   - sandbox-first for internal beta,
   - and which exact payout visibility goal for Month 2?
7. **Fork conflict policy for Month 2:**  
   The Phase playbook says “pick one fork only” for POD vs Stripe pilot. For this sprint:
   - Are we authorized to implement both POD and Connect payout visibility in Month 2, or
   - do we prioritize POD first and defer Connect, or
   - prioritize Connect first and defer POD?
8. **Proof-of-delivery format (P2.A):**
   - PIN only,
   - photo required,
   - signature required,
   - how do disputes work operationally?
9. **Push strategy (APNs):**
   - direct APNs with provider keys,
   - or via a intermediary (e.g. FCM/APNs bridges),
   - and which notification trigger: “ride assigned” or “ride available”?
10. **Background check vendor:** Confirm Checkr vs alternative, and which workflow model (API polling vs webhooks).
11. **Target city launch:** Confirm “Portland first” vs another geography.
12. **Driver agreement requirements:** Which documents must be accepted before onboarding can start (TNC, insurance, privacy consents)?

---

## Appendix: sprint report templates (what you should create)

Create one of the following after each month or after major milestone completion:

- `docs/HALFAPP_SPRINT_TO_DRIVERS_MONTH1_REPORT_01.md`
- `docs/HALFAPP_SPRINT_TO_DRIVERS_MONTH2_REPORT_01.md`
- `docs/HALFAPP_SPRINT_TO_DRIVERS_MONTH3_REPORT_01.md`

Each report must include:
- TASKS completed with IDs
- Commands run
- Evidence links (logs, key test output excerpts)
- Governance checks line(s)

