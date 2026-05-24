# HalfApp Launch Blockers — Code-First Playbook (Single Copy-Paste Document)

**Document ID:** `HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01`  
**Date:** 2026-05-22  
**Audience:** Program owner, advanced engineers, coding agents  
**Workspace:** `c:\Users\him\Desktop\halfapp-driver`  
**Purpose:** One file that captures (1) what is wrong with HalfApp today, (2) why generic “drop-in code packs” do not fit this repo, and (3) the **grounded** solution path using **your existing** files — not a greenfield `app/` tree.

**Authority:** `backend/main.py`, green tests, `docs/CURRENT_TRUTH.md`, `docs/HALFAPP_DRIVER_PROGRAM_MASTER_REPORT_01.md`

---

# SECTION 0 — Why this document exists

You asked for:

1. A clear list of the program’s problems (not vague “AI consultant” bullets).
2. A **code-first** response to launch blockers — not Stripe/OSRM/JWT starter code in a folder that does not exist in HalfApp.
3. **One whole script** you can copy once, including the context of the other AI reply that could not see your repo and pasted unrelated `app/payments_api.py`-style packs.

**This file is that single artifact.** Open it, copy sections, or hand the whole file to the next agent.

---

# SECTION 1 — Executive verdict (plain language)

HalfApp Driver is a **real driver MVP**: backend-owned lifecycle, atomic open-board claims, integer-cent pricing with lock on complete, map-first cockpit with ride-flow E2E **GO**, trip audit UI, production `SECRET_KEY` boot guard.

It is **not** ready to claim: Uber-scale dispatch, production road routing, real money movement, rider product, or public launch without careful copy.

**Do not** paste a second marketplace implementation on top. **Evolve** `backend/` + `driver-app/` and decide the dossier spine before new money/dispatch features.

---

# SECTION 2 — All major problems (15), with plain meanings

## Critical / launch-blocking (top 5)

| # | Problem | Plain meaning |
|---|---------|----------------|
| **1** | **Payments visibility vs live money** | Phases 1–5.1 **GO** behind flags; bank-deposit claims still **NO_GO**. See refreshed Blocker 1 below. |
| **2** | **No production OSRM runtime proof** | Code + mocks **GO**; live Docker/VPS proof **NO_GO**. Often `haversine_fallback` — honest but not road network. |
| **3** | **Two marketplace spines in one repo** | Active: `/drivers/*`. Parallel: `/supply`, `/demand`, `/trip` + dossier `ledger_*`. UI does not call dossier — but both exist in `main.py`. |
| **4** | **Postgres claim proof not default CI** | RIDE-002 **GO** on SQLite; `test_postgres_claim_race_proof_01.py` exists but CI runs SQLite only. |
| **5** | **Incomplete session security** | `SECRET_KEY` boot guard **GO**. No refresh tokens, no revocation store. |

## Strategic / architecture (6–10)

| # | Problem | Plain meaning |
|---|---------|----------------|
| **6** | **Repository sprawl** | Legacy `frontend/`, dormant routers, `video-gate/`, dossier routes look like product. |
| **7** | **Dispatch depth** | Open board + audit **honest**; no full candidate/geo-fairness rounds. |
| **8** | **No geocoding / ETA product** | Coordinates supplied; map ≠ routing proof. |
| **9** | **Governance brain is docs-only** | Strong directives; no CI lint for forbidden marketing/UI claims. |
| **10** | **Doc drift** | `BACKLOG.md` vs shipped lanes can disagree. |

## Product / UX (11–15)

| # | Problem | Plain meaning |
|---|---------|----------------|
| **11** | **No rider app** | `POST /rides/` API only. |
| **12** | **No full admin OS** | Driver approval API only; legacy admin unmounted. |
| **13** | **Web app, not native** | React/Vite cockpit; not App Store driver shell. |
| **14** | **REST presence only** | No WebSocket gateway. |
| **15** | **Driver confusion risks** | Payout vs total, “did I get paid?”, route accuracy, decline → pool, simulation labels. |

## What is NOT a main problem anymore (closed — do not reopen casually)

- P0 lifecycle, claim lock (RIDE-002), state machine (RIDE-001), dispatch cascade (RIDE-003), driver approval (DRIVER-002), auth lanes (AUTH-001)
- Ride-flow E2E on map-first cockpit (`HALFAPP_DRIVER_COCKPIT_RIDE_FLOW_E2E_LOCK_01` **GO**)
- Pricing lock + trip audit read UI
- Production `SECRET_KEY` guard (`HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01` **GO**)
- Test isolation (~262+ backend tests in one command)
- Engineering intelligence = **LOCAL_CONTEXT_ONLY** (not ride-product AI)

---

# SECTION 3 — Why the generic “5 code packs” do NOT fit HalfApp

Another assistant (without repo access) offered drop-in modules like:

- `app/payments_api.py`, `app/models_payments.py`
- `app/routing.py` (duplicate routing)
- `app/spine_gate.py` with `ACTIVE_SPINE` env
- `app/claims.py` with `Ride.state = "claimed"`
- `app/jwt_tokens.py` separate from your RBAC

**That is a new project layout.** HalfApp already has:

```
halfapp-driver/
  backend/
    main.py
    production_guards.py
    routes/drivers.py
    routes/dossier_marketplace.py
    services/dispatch.py
    services/routing_service.py
    services/ride_pricing.py
    services/ride_settlement.py
    services/auth.py
    services/rbac.py
    models/ride_pricing.py
    models/settlement_entry.py
    alembic/versions/0001..0015
  driver-app/
    src/utils/api.js          # /drivers/* only
    src/components/TripAuditReceipt.jsx
```

**Rule for all future work:** extend these paths. Do **not** add parallel `app/` package unless you are intentionally forking the product.

---

# SECTION 4 — Grounded solution map (5 launch blockers → your files)

---

## BLOCKER 1 — Payments / payout visibility (REFRESH 2026-05-22)

**Status:** **PARTIAL GO** — execution + provider visibility shipped; bank-deposit marketing still **NO_GO**.

### What is GO in-repo (Phases 1–5.1)

| Path | Role |
|------|------|
| `backend/models/payment_execution.py` + migrations `0017`–`0023` | Charge/refund/dispute execution rows; Connect transfers/payouts |
| `backend/services/payment_execution.py`, `payment_reconciliation.py` | PI creation, reconciliation, payout enrichment |
| `backend/routes/payments_webhooks.py` | Signed webhooks + dedupe; dual secrets; transfer/payout ingest (`PAYOUTS_ENABLED`) |
| `backend/routes/stripe_connect.py` | Connect onboarding + `GET /drivers/stripe/connect/status` (read-only flags) |
| `GET /drivers/me/payment-reconciliation`, `/payment-executions`, `/payouts` | Driver-scoped visibility |
| `driver-app/src/components/EarningsVisibilityPanel.jsx` | Execution + payout UI (`BETA_PAYMENT_*`, `BETA_PAYOUT_*`) |
| `driver-app/scripts/assert-no-money-claims.mjs` | CI semantic lock |
| `docs/HALFAPP_PAYMENTS_EXECUTION_05_GO.md`, `05_1_GO.md` | GO rituals + UI contract |

**Truth boundary (unchanged):**

- `pricing_earned_cents` = locked obligation (`ride_pricing`)
- `collected_cents` / `available_cents` = PSP execution truth
- `payout_*` = provider payout object status — **not** bank deposit confirmation
- Trip audit copy may still say `payment_execution: not_implemented` until product explicitly updates audit lane

**Env (default safe):** `PAYMENTS_ENABLED=0`, `PAYOUTS_ENABLED=0` — enable in staging only with webhook endpoints configured.

### What is still missing for “live money launch”

- Staging/production webhook proof on both platform + Connect endpoints
- Conscious audit-copy update (if desired) vs keeping `not_implemented` disclaimer
- Bank deposit / “sent to your bank” UI (policy: out of scope)

### Forbidden

- Replacing `ride_pricing` math with frontend-submitted amounts
- Calling dossier `ledger_*` for driver-app money truth
- Marketing “deposited”, “instant pay”, or “sent to your bank” without explicit new policy + proof

---

## BLOCKER 2 — OSRM runtime proof + fallback labeling

### What you already have (keep)

| Path | Role |
|------|------|
| `backend/services/routing_service.py` | OSRM try → `haversine_fallback`, `used_fallback=true` |
| `backend/services/osrm_self_hosted_provider.py` | HTTP client |
| `backend/services/route_snapshots.py` | Persist quote/complete snapshots |
| `docker/osrm-portland/` | Compose for proof |
| `docs/RUNTIME_PROOF_PROCEDURE.md` | How to prove |
| `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` | Code GO, runtime NO_GO |
| `driver-app` map `data-route-provider` | Honest provider attribute |
| Trip audit / route truth UI | `osrm_runtime_claim: not_proved` when applicable |

### What is missing

- A **GO** runtime proof run (artifact: response JSON with `route_provider=osrm_self_hosted`, `used_fallback=false`)
- Optional: CI smoke that hits OSRM when `OSRM_BASE_URL` set (not required for local Windows dev)

### Grounded implementation order (mostly ops + docs)

1. On Linux/VPS or Docker-capable host:
   ```powershell
   cd c:\Users\him\Desktop\halfapp-driver\docker\osrm-portland
   # Follow README.md — prepare map, then:
   docker compose up -d
   ```
2. Run procedure in `docs/RUNTIME_PROOF_PROCEDURE.md`; save logs/screenshots.
3. Update `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` → runtime **GO** or stay **NO_GO**.
4. Set production env: `ROUTING_PROVIDER=osrm_self_hosted`, `OSRM_BASE_URL=...`, `ROUTING_FALLBACK_ENABLED=true` (fallback still honest if OSRM down).
5. **Do not** remove `haversine_fallback` from E2E — `ride-flow-ui-proof.spec.ts` allows it by design.

### Forbidden

- Claiming “production routing” while status doc says runtime NO_GO
- Hiding `data-route-provider=haversine_fallback` in UI

---

## BLOCKER 3 — Dual marketplace spine safety

### What you already have (keep)

| Path | Role |
|------|------|
| `backend/routes/drivers.py` | **Active** driver product API |
| `driver-app/src/utils/api.js` | Must only call `/drivers/*` + `/auth/*` |
| `backend/routes/dossier_marketplace.py` | Parallel foundation (supply/demand/trip) |
| `docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md` | Reconciliation rules |
| `driver-app/scripts/assert-no-ai-providers.mjs` | Pattern for forbidden strings in `src/` |

### What is missing

- Hard **runtime** gate so dossier is not mounted in production-shaped deploys by accident
- CI assertion: driver-app source never contains `/supply/`, `/demand/`, `/trip`

### Grounded implementation order (small code change)

**Option A — Env gate (recommended minimal slice)**

1. In `backend/main.py`, replace unconditional dossier mount with:

   ```python
   # Pseudocode — implement in main.py when executing this playbook
   import os
   if os.getenv("HALFAPP_DOSSIER_SPINE_ENABLED", "").strip().lower() in ("1", "true", "yes"):
       app.include_router(dossier_marketplace_router)
   ```

2. Default: **off** in production `.env`; **on** in pytest when `tests/test_dossier_dispatch_ledger_slice.py` needs it (set env in that test module or conftest marker).

3. Add test `tests/test_dossier_mount_gate.py`: with env unset, OpenAPI has no `/supply/heartbeat`.

4. Add driver-app test or extend `assert-no-ai-providers.mjs`:

   ```javascript
   const FORBIDDEN = [..., '/supply/', '/demand/', '/trip/']
   ```

**Option B — Strategic merge (months)** — single ride ID, single presence, single ledger. **Do not start here.**

### Forbidden

- Wiring `driver-app` to `POST /demand/request` without reconciliation doc + full E2E
- Dual-write from one UI action to `rides` and dossier trip tables

---

## BLOCKER 4 — Postgres claim concurrency proof

### What you already have (keep)

| Path | Role |
|------|------|
| `backend/services/dispatch.py` | `OpenBoardDispatchPolicy.claim_ride` — `FOR UPDATE` + conditional UPDATE |
| `backend/tests/test_ride_claim_lock_concurrency.py` | Concurrency on SQLite |
| `backend/tests/test_postgres_claim_race_proof_01.py` | **Postgres-specific** 10-driver race |
| `docs/HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01_REPORT.md` | Lane report |

### What is missing

- Postgres job in **CI** (`.github/workflows/halfapp-driver-ci.yml` currently uses SQLite only)

### Grounded implementation — CI job snippet

Add a second job to `.github/workflows/halfapp-driver-ci.yml` (copy when implementing):

```yaml
  postgres-claim-race:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: halfapp
          POSTGRES_PASSWORD: halfapp
          POSTGRES_DB: halfapp_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U halfapp -d halfapp_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install -r backend/requirements.txt

      - name: Postgres claim race proof
        env:
          DATABASE_URL: postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test
          PYTHONPATH: backend
          SECRET_KEY: pytest-postgres-claim-race-secret-32chars-min
          HALFAPP_ENV: test
          HALFAPP_ENABLE_RIDE_SIMULATION: "1"
          ALLOW_TEST_USER_SEED: "true"
        run: |
          python -m pytest backend/tests/test_postgres_claim_race_proof_01.py -q
```

Local run (when Postgres available):

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
$env:DATABASE_URL="postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test"
$env:SECRET_KEY="pytest-postgres-claim-race-secret-32chars-min"
$env:HALFAPP_ENV="test"
$env:HALFAPP_ENABLE_RIDE_SIMULATION="1"
$env:ALLOW_TEST_USER_SEED="true"
py -3.11 -m pytest tests/test_postgres_claim_race_proof_01.py -q
```

### Forbidden

- New `claims.py` with different status names (`claimed` vs your `accepted`)
- Removing SQLite tests — keep both

---

## BLOCKER 5 — JWT refresh + revocation

### What you already have (keep)

| Path | Role |
|------|------|
| `backend/services/auth.py` | Access JWT + bcrypt |
| `backend/services/rbac.py` | `AuthPrincipal`, lane guards |
| `backend/production_guards.py` | Boot-time `SECRET_KEY` guard |
| `backend/services/rate_limit.py` | Auth rate limiting |
| `driver-app` | `driver_token` in localStorage (MVP) |

### What is missing

- `refresh_tokens` table (hash only, never store raw refresh in DB)
- `POST /auth/refresh` with rotation (reuse detection)
- `POST /auth/logout` or `logout_all` revoking refresh family
- Optional: `token_version` on `users` for instant access invalidation

### Grounded implementation order

1. Migration `0017_refresh_tokens_foundation.py` — model in `backend/models/refresh_token.py`
2. `backend/services/refresh_tokens.py` — mint, rotate, revoke_all
3. Extend `backend/routes/auth.py` — `/auth/refresh`, `/auth/logout-all`
4. `driver-app/src/hooks/useAuth.jsx` — store refresh securely (httpOnly cookie ideal; if localStorage, document risk)
5. Tests: rotation, revoked refresh fails, access still expires independently

### Forbidden

- Separate `app/jwt_tokens.py` bypassing RBAC
- Long-lived access tokens without rotation

---

# SECTION 4B — Driver product completion (Slices 01–03) — GO

**Lane:** Driver UX completeness on active spine (`/drivers/*` + `driver-app`). Not payments Phase 6, not dossier merge.

**Authority:** `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_01.md` … `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03.md`

---

## SLICE 01 — Settings shell + cockpit resume (GO)

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_01 — GO

Shipped:
- Driver Settings route (/driver/settings): session + read-only Connect status + sign out
- GET /drivers/stripe/connect/status (DB-only; no Stripe API)
- MapHome: current_ride_id resume + visibilitychange refresh + cockpit-resume-notice
- Phase 5.2 payout list rows show Provider estimated arrival (arrival_date)
- Playbook Blocker 1 refreshed: payments PARTIAL GO; no bank-deposit claims
- Tests: driverSettings + test_stripe_connect_status.py + guards PASS

Not shipped (Slice 02+):
- profile/settings persistence (migrations + PUT)
- resilientFetch / offline banner / idempotency header on ride writes
- web push (sw.js + /drivers/me/push-subscription)
- OSRM ops-only healthcheck
```

| Path | Role |
|------|------|
| `driver-app/src/components/DriverSettings.jsx` | Settings shell |
| `driver-app/src/components/MapHome.jsx` | Active-ride resume |
| `backend/routes/stripe_connect.py` | `GET /drivers/stripe/connect/status` |

---

## SLICE 02 — Profile + settings persistence (GO)

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02 — GO

Shipped:
- Migrations 0024_driver_profiles + 0025_driver_settings (alembic head 0025)
- GET/PUT /drivers/me/profile (display_name, phone_e164, photo_url overlay)
- GET/PUT /drivers/me/settings (units, locale, theme, notification preference toggles)
- /driver/settings wired: preferences auto-save + app profile save
- GET /drivers/stripe/connect/status unchanged (DB-only read-only)
- GET /drivers/profile unchanged (User + vehicle read-only contract)
- Tests: test_driver_settings_profile_slice02.py + driverSettings unit checks

Not shipped (Slice 03+):
- web push / service worker / VAPID
- resilientFetch, offline banner, Idempotency-Key on ride writes
- OSRM ops healthcheck
- Connect onboarding buttons or Stripe API from driver app
```

### Scope (Slice 02)

| In | Out |
|----|-----|
| `driver_profiles` + `driver_settings` tables | Web push delivery |
| `/drivers/me/profile` + `/drivers/me/settings` | `resilientFetch` / offline banner |
| Settings UI persistence | OSRM healthcheck |
| Notification **preference** storage only | Stripe Connect onboarding from UI |

### Key paths (Slice 02)

| Path | Role |
|------|------|
| `backend/alembic/versions/0024_driver_profiles.py`, `0025_driver_settings.py` | Schema |
| `backend/models/driver_profile.py`, `driver_app_settings.py` | ORM |
| `backend/services/driver_profile_service.py`, `driver_app_settings_service.py` | get-or-create + partial PUT |
| `backend/routes/drivers.py` | `/me/profile`, `/me/settings` on existing router |
| `driver-app/src/components/DriverSettings.jsx` | Preferences + app profile UI |
| `driver-app/src/utils/api.js` | `getDriverAppSettings`, `putDriverAppSettings`, `getDriverMeProfile`, `putDriverMeProfile` |
| `backend/tests/test_driver_settings_profile_slice02.py` | Backend contract tests |

### API contracts (do not break)

- **`GET /drivers/profile`** — User + vehicle projection; `read_only: true` on GET. **Unchanged** (Slice 01 contract).
- **`GET/PUT /drivers/me/profile`** — App overlay only (`display_name`, `phone_e164`, `photo_url`). Separate table; does not replace User.name automatically.
- **`GET/PUT /drivers/me/settings`** — Partial PUT; invalid `units` / `theme` → `400`.
- **`GET /drivers/stripe/connect/status`** — DB flags only; no Stripe API from driver app.

### Verification (Slice 02)

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
py -3.11 -m alembic upgrade head
py -3.11 -m pytest tests/test_driver_settings_profile_slice02.py -q

cd ..\driver-app
npm test
npm run build
```

Expected: backend **5 passed** (slice02 file); frontend **101+** unit tests + `assert-no-ai-providers` + `assert-no-money-claims` OK.

### Rollback (Slice 02)

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
py -3.11 -m alembic downgrade 0023_stripe_payout_transfers
```

Revert `DriverSettings.jsx` to Slice 01 read-only if UI rollback needed.

### Guardrails (Slices 01–02)

- No bank-deposit / “sent to your bank” marketing (`assert-no-money-claims`; `DriverSettings.jsx` skipped for provider field names only).
- Connect status read-only in Settings — no onboarding button, no Stripe API from that screen.
- Push toggle stores **preference only** — no subscription endpoints until Slice 04b (web push).

---

## SLICE 03 — Cockpit resilience (GO)

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03 — GO

Shipped:
- Alembic: `0026_driver_idempotency_replays` (alembic head: 0026)
- Ride-write idempotency: accept, decline, decline-dispatch, arrive, start, complete, hide, dismiss
- Frontend: resilientFetch (POST-only retries), callRideWrite + Idempotency-Key
- Cockpit: offline/degraded banner (MapHome)

Verification (2026-05-23):
- pytest `test_driver_ride_idempotency_slice03.py` PASS
- `npm test` (105) + guards PASS
- `npm run build` PASS
- `npm run test:e2e:ride-flow` PASS

Not shipped (Slice 04b+):
- web push / VAPID / service worker
- OSRM ops healthcheck
- offline mutation outbox
- Connect onboarding / Stripe API from driver app
```

| Path | Role |
|------|------|
| `backend/alembic/versions/0026_driver_idempotency_replays.py` | Replay store |
| `backend/services/driver_idempotency.py` | `execute_idempotent_ride_write` |
| `backend/routes/drivers.py` | Wrapped ride-write POSTs |
| `driver-app/src/utils/resilientFetch.js`, `idempotencyKeys.js` | Client retry + keys |
| `driver-app/src/utils/api.js` | `callRideWrite` |
| `driver-app/src/components/CockpitNetworkBanner.jsx` | Offline/degraded UI |
| `backend/tests/test_driver_ride_idempotency_slice03.py` | Backend tests |
| `driver-app/tests/unit/slice03Resilience.test.js` | Frontend checks |

## SLICE 04 — In-app notifications (GO)

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_04 — GO

Shipped:
- Notifications inbox: AppShellLayout + ha-* chrome, mark-read, honest empty
- API: existing GET /notifications/, POST /notifications/{id}/read
- Demo Messages tab DEV-only (`import.meta.env.DEV`)
- Lifecycle in-app rows: ride accept + complete (`services/driver_in_app_notifications.py`)
- Settings link → /driver/notifications

Verification (2026-05-23):
- pytest `test_driver_notifications_slice04.py` PASS (2)
- `npm test` + guards PASS
- `npm run build` PASS
- `npm run test:e2e:ride-flow` PASS

Not shipped (Slice 04b+):
- web push / VAPID / service worker
```

| Path | Role |
|------|------|
| `backend/services/driver_in_app_notifications.py` | Gated `notify_driver_in_app` |
| `backend/routes/drivers.py` | Accept/complete → in-app notification |
| `driver-app/src/components/Notifications.jsx` | Inbox UI |
| `driver-app/src/utils/notificationDisplay.js` | `read` field mapping |
| `backend/tests/test_driver_notifications_slice04.py` | Backend tests |
| `driver-app/tests/unit/notificationsSlice04.test.js` | Frontend checks |

## SLICE 05 — OSRM ops-only (GO)

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_05 — GO

Shipped:
- scripts/osrm_healthcheck.ps1 + scripts/osrm_healthcheck.sh (Route API, code=Ok, positive distance)
- docs/HALFAPP_OSRM_OPS_ONLY_SLICE_05.md + HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_05.md
- docker/osrm-portland compose healthcheck on /route/v1/driving/...

Verification (ops):
- With OSRM up: healthcheck scripts exit 0
- Without OSRM: exit 1 (expected); no app/npm changes required

Not shipped:
- Production OSRM runtime GO (proof script + SELF_HOSTED_ROUTING_PROOF status doc)
- Routing service / UI / dispatch behavior changes
```

| Path | Role |
|------|------|
| `scripts/osrm_healthcheck.ps1` | PowerShell ops healthcheck |
| `scripts/osrm_healthcheck.sh` | Bash ops healthcheck |
| `docs/HALFAPP_OSRM_OPS_ONLY_SLICE_05.md` | Ops runbook |
| `docker/osrm-portland/docker-compose.yml` | Container healthcheck |
| `backend/scripts/verify_osrm_health.py` | Existing Python gate (proof procedure) |

### Next queue (recommended)

1. **OSRM runtime proof run** — `HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01` → update `SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md`
2. **Postgres claim CI** — `HALFAPP_POSTGRES_CI_01`

---

# SECTION 5 — Recommended execution order (code-first roadmap)

| Week | Slice | ID | Outcome |
|------|-------|-----|---------|
| — | Driver settings shell + resume | `HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_01` | **GO** — see Section 4B |
| — | Profile + settings persistence | `HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02` | **GO** — alembic `0025`, `/me/profile`, `/me/settings` |
| — | Cockpit offline / idempotency | `HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03` | **GO** — `resilientFetch`, banner, ride-write keys |
| 1 | Postgres claim in CI | `HALFAPP_POSTGRES_CI_01` | RIDE-002 credible on real DB |
| 1 | OSRM runtime proof run | `HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01` | Status doc GO or honest NO_GO |
| 2 | Dossier mount env gate | `HALFAPP_DOSSIER_MOUNT_GATE_01` | No accidental dossier in prod |
| 2 | Driver-app dossier path grep CI | `HALFAPP_DRIVER_API_BOUNDARY_CI_01` | UI cannot call dossier |
| 3–6 | Payments boundary + tables + webhooks | `HALFAPP_PAYMENTS_EXECUTION_01` | **GO** Phases 1–5.1 — see Blocker 1 |
| 4–6 | Refresh + revocation | `HALFAPP_AUTH_REFRESH_REVOCATION_01` | **GO** in-repo — see `docs/CURRENT_TRUTH.md` |

**Do not** run payments and dossier merge in parallel without a program owner decision.

---

# SECTION 6 — Dossier vs active spine decision (required once)

Choose **one** before scaling team:

| Path | Meaning | Cost |
|------|---------|------|
| **A — Evolve active spine** | Keep open board `/drivers/*`; enrich pricing, payments, OSRM on `rides` + `ride_pricing` | Lower risk |
| **B — Merge dossier** | Unify presence, ride IDs, dispatch, `ledger_*` vs `settlement_entries` | High risk, months |

**Current product truth:** Path **A** (driver app uses `/drivers/*` only).

---

# SECTION 7 — Full verification script (copy-paste block)

Run from repo root after any slice. Adjust paths if needed.

```powershell
# === HALFAPP VERIFICATION RITUAL ===
cd c:\Users\him\Desktop\halfapp-driver

# Active routes truth
py -3.11 scripts\print_active_routes.py

# Backend full suite (SQLite)
cd backend
$env:HALFAPP_ENV="test"
$env:SECRET_KEY="pytest-halfapp-test-secret-32chars-minimum"
$env:HALFAPP_ENABLE_RIDE_SIMULATION="1"
py -3.11 -m pytest tests -q
cd ..

# Driver app unit + forbidden provider strings
cd driver-app
npm test
npm run build

# Driver product completion Slice 02 (profile + settings)
cd ..\backend
py -3.11 -m pytest tests/test_driver_settings_profile_slice02.py -q
cd ..\driver-app

# Ride-flow E2E (map-first cockpit full lifecycle)
npm run test:e2e:ride-flow
cd ..

# Optional: Postgres claim race (requires local Postgres)
# cd backend
# $env:DATABASE_URL="postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test"
# $env:SECRET_KEY="pytest-postgres-claim-race-secret-32chars-min"
# py -3.11 -m pytest tests/test_postgres_claim_race_proof_01.py -q

# Forbidden in frontend (manual grep)
# Select-String -Path driver-app\src -Pattern "api.anthropic.com|api.openai.com|/supply/|/demand/|/trip/" -Recurse
```

Expected healthy baseline (2026-05-22, post–Slice 02):

- Backend: **260+ passed** (SQLite full suite)
- Slice 02 file: **5 passed** (`test_driver_settings_profile_slice02.py`)
- Driver unit: **101+ passed** (includes guard scripts in `npm test`)
- Ride-flow E2E: **1 passed**
- Build: success
- Alembic head: **`0025_driver_settings`**

---

# SECTION 8 — Agent / developer rules (paste into next Cursor task)

```markdown
## HalfApp launch blocker rules

1. Active product: `backend/` + `driver-app/` only for ride product.
2. Driver app API: `/auth/*` and `/drivers/*` only — never dossier `/supply|demand|trip` in UI.
3. Money: `ride_pricing` + `settlement_entries` are truth; PSP is separate execution layer.
4. Do not claim OSRM production until `SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS` runtime GO.
5. Do not add greenfield `app/` package — extend `backend/services`, `backend/routes`, Alembic.
6. Do not reopen closed P0 lanes (RIDE-001/002/003, DRIVER-002, AUTH-001) without explicit rescope.
7. Every driver-visible fact must come from backend records + tests.
8. Playwright ride-flow must stay GO after UI changes.
```

---

# SECTION 9 — Message you received (generic AI) — what to do with it

**What it was:** A template FastAPI project for Stripe, OSRM, spine gate, claims, JWT — useful as **ideas**, not as a patch.

**What to do:**

- Save ideas: webhook idempotency, refresh rotation, `FOR UPDATE SKIP LOCKED`, OSRM healthcheck compose.
- **Do not** copy files into the repo as `app/`.
- Use **Section 4** of this playbook instead — file paths match HalfApp.

**OneDrive folder:** External assets only. Planning truth lives in `docs/` inside git.

---

# SECTION 10 — Quick reference: key file index

```
Governance
  docs/CURRENT_TRUTH.md
  docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md
  docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md
  docs/HALFAPP_DRIVER_PROGRAM_MASTER_REPORT_01.md

Backend entry
  backend/main.py
  backend/config.py
  backend/production_guards.py

Lifecycle + dispatch
  backend/routes/drivers.py
  backend/services/dispatch.py
  backend/services/lifecycle.py
  docs/RIDE_LIFECYCLE_CONTRACT.md

Money (ledger, not PSP)
  backend/models/ride_pricing.py
  backend/models/settlement_entry.py
  backend/services/ride_pricing.py
  backend/services/ride_settlement.py

Routing
  backend/services/routing_service.py
  backend/services/osrm_self_hosted_provider.py
  docker/osrm-portland/

Dossier (parallel — not UI)
  backend/routes/dossier_marketplace.py

Auth
  backend/services/auth.py
  backend/services/rbac.py

Driver UI
  driver-app/src/App.jsx
  driver-app/src/components/MapHome.jsx
  driver-app/src/components/DriverSettings.jsx
  driver-app/src/components/EarningsVisibilityPanel.jsx
  driver-app/src/components/TripAuditReceipt.jsx
  driver-app/src/utils/api.js
  driver-app/tests/ride-flow-ui-proof.spec.ts

Driver product completion (Slices 01–02 GO)
  docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_01.md
  docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02.md
  backend/models/driver_profile.py
  backend/models/driver_app_settings.py
  backend/tests/test_driver_settings_profile_slice02.py

Tests
  backend/tests/test_postgres_claim_race_proof_01.py
  backend/tests/test_ride_claim_lock_concurrency.py
  backend/tests/test_production_guards.py

CI
  .github/workflows/halfapp-driver-ci.yml
```

---

# SECTION 11 — Next action for you (pick one line)

Reply to your agent with exactly one of:

1. `Run OSRM runtime proof — HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01 (see docs/RUNTIME_PROOF_PROCEDURE.md)`
2. `Implement HALFAPP_POSTGRES_CI_01 — add CI job from Section 4 Blocker 4`
3. `Implement HALFAPP_DOSSIER_MOUNT_GATE_01 — env gate in main.py per Section 4 Blocker 3`
4. `Run OSRM runtime proof only — update SELF_HOSTED_ROUTING_PROOF status doc`
5. `Run OSRM runtime proof only — update SELF_HOSTED_ROUTING_PROOF status doc`

---

**End of playbook** — `HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01`

*Copy this entire file to share with collaborators. Update when a blocker lane reaches GO in `docs/CURRENT_TRUTH.md`.*
