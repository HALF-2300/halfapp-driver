# HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03 — Cockpit resilience (planned)

**Status:** GO  
**Date:** 2026-05-23  
**Lane:** Driver product completion — network/offline UX + safe ride-write retries  
**Depends on:** Slice 01–02 **GO** (`docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02.md`)

**Maps to roadmap:** `COCKPIT_SESSION_RESILIENCE_01` in `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`

---

## Purpose

Make the **map cockpit** honest and recoverable when the network flakes: visible offline state, bounded retries on read paths, and **idempotent ride writes** so double-taps / retries do not corrupt lifecycle.

This slice is **driver-app + minimal backend header support** — not notifications, not OSRM ops, not payments.

---

## In scope (Slice 03)

| # | Deliverable | Acceptance |
|---|-------------|------------|
| 1 | **`resilientFetch` helper** | Central wrapper in `driver-app/src/utils/` used by ride-critical `driverAPI` methods: timeout, limited retries (network/5xx only), no retry on 4xx except 401 refresh path |
| 2 | **Offline / degraded banner** | Cockpit (`MapHome.jsx`) shows `data-testid="cockpit-offline-banner"` when `navigator.onLine === false` or consecutive API failures; clears on successful refresh |
| 3 | **Ride-write `Idempotency-Key`** | Client generates stable key per user intent (e.g. `accept:{rideId}:{uuid}` stored until success); sent on POST transition endpoints |
| 4 | **Backend idempotency store (minimal)** | Table or reuse pattern: record `(driver_id, idempotency_key, endpoint, response_snapshot)`; replay same HTTP status + body on duplicate key within TTL |
| 5 | **Wire ride actions** | `acceptRide`, `declineRide`, `arrivePickup`, `startRide`, `completeRide`, `hideRide` / dismiss — header on POST only |
| 6 | **Tests** | Backend: duplicate key → same outcome, no double transition; Frontend: unit tests for banner + header attachment; ride-flow E2E still **GO** |
| 7 | **Docs** | This file → **GO** ritual; playbook Section 4B queue updated |

### Ride-write endpoints (active spine only)

All under `backend/routes/drivers.py` — **do not** add dossier `/trip` idempotency in this slice.

| Method | Path | Idempotency required |
|--------|------|----------------------|
| POST | `/drivers/accept-ride/{ride_id}` | Yes |
| POST | `/drivers/decline-ride/{ride_id}` | Yes |
| POST | `/drivers/decline-dispatch/{ride_id}` | Yes |
| POST | `/drivers/arrive-pickup/{ride_id}` | Yes |
| POST | `/drivers/start-ride/{ride_id}` | Yes |
| POST | `/drivers/complete-ride/{ride_id}` | Yes |
| POST | `/drivers/rides/{ride_id}/hide` | Yes |
| POST | `/drivers/dismiss-ride/{ride_id}` | Optional (legacy alias) |

**Read paths** (`GET` available-rides, presence, me/status): may use `resilientFetch` retries but **no** idempotency header.

---

## Out of scope (guardrails — do not creep)

| Out | Reason |
|-----|--------|
| Web push / service worker / VAPID | Slice 04+ |
| OSRM Docker healthcheck / routing provider changes | Slice 05 / `HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01` |
| Connect onboarding / Stripe API from driver app | Payments lane |
| `driver_profiles` / `driver_settings` schema changes | Slice 02 closed |
| Dossier `/supply`, `/demand`, `/trip` | Spine reconciliation |
| Queue/offline mutation replay (IndexedDB outbox) | Future; banner + retry is enough for Slice 03 |
| Changing pricing lock or payment execution | Payments lane |
| Replacing `DriverAPI.call` globally in one PR | Phase: ride writes first, then optional broader reads |

---

## Grounded starting points (repo)

| Area | Path | Today |
|------|------|--------|
| API client | `driver-app/src/utils/api.js` | `call()` has 401 refresh retry; `AbortSignal.timeout`; no network retry |
| Cockpit | `driver-app/src/components/MapHome.jsx` | `visibilitychange` refresh; `current_ride_id` resume (Slice 01) |
| Ride actions | `driver-app/src/utils/api.js` | `acceptRide`, `arrivePickup`, `startRide`, `completeRide`, … |
| Backend transitions | `backend/routes/drivers.py` | No `Idempotency-Key` header handling on driver POSTs |
| Idempotency precedent | `backend/services/payment_execution.py`, `models/payment_execution.py` | PSP layer only — pattern reference, not reuse table |
| E2E lock | `driver-app/tests/ride-flow-ui-proof.spec.ts` | Must stay **GO** after slice |

---

## Implementation sketch (for agents)

### Frontend

1. Add `driver-app/src/utils/resilientFetch.js`:
   - `resilientFetch(url, init, { maxRetries, retryOn })`
   - Default: 2 retries, backoff 300ms / 800ms, retry on `TypeError` / status ≥ 500
2. `driverAPI` ride POSTs: build `Idempotency-Key` header; persist key in `sessionStorage` until 2xx on that action+rideId
3. `MapHome.jsx`: subscribe `online` / `offline`; show banner; on `visibilitychange` call existing `refreshBackendTruth`

### Backend

1. Migration `0026_driver_idempotency_keys.py` (name TBD) — columns: `driver_id`, `idempotency_key`, `route_key`, `request_hash`, `response_status`, `response_json`, `created_at`
2. `backend/services/driver_idempotency.py` — `begin_or_replay(db, driver_id, key, route_key, handler) -> response`
3. FastAPI dependency: read `Idempotency-Key` header (optional for backward compat in dev; **required** in tests for ride writes once shipped)
4. Wrap transition handlers or use middleware scoped to ride POST routes

### Tests

- `backend/tests/test_driver_ride_idempotency_slice03.py`
- Extend `driver-app/tests/unit/` (new `resilientFetch.test.js` or extend `cockpitLayout` / MapHome source checks)
- Run full `npm run test:e2e:ride-flow` before GO

---

## GO ritual (copy-paste)

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03 — GO

Shipped:
- Alembic migration `0026_driver_idempotency_replays` (head 0026)
- Backend: `execute_idempotent_ride_write` on driver ride-write POSTs
  - accept-ride, decline-ride, decline-dispatch, arrive-pickup, start-ride, complete-ride, rides/hide (+ dismiss alias)
- Frontend: `resilientFetch` (POST-only retries), `callRideWrite` + `Idempotency-Key`
- Cockpit: `CockpitNetworkBanner` (offline + degraded) in MapHome
- Tests: `test_driver_ride_idempotency_slice03.py` (4) + `slice03Resilience.test.js` + guards PASS

Not shipped (Slice 04+):
- web push / service worker / VAPID
- OSRM ops healthcheck
- offline mutation outbox / background sync
- Connect onboarding / Stripe API from driver app
- Global GET retry via resilientFetch
```

## Endpoint map (repo truth)

| Action | Method | Path |
|--------|--------|------|
| accept | POST | `/drivers/accept-ride/{ride_id}` |
| decline | POST | `/drivers/decline-ride/{ride_id}` |
| decline_dispatch | POST | `/drivers/decline-dispatch/{ride_id}` |
| arrive | POST | `/drivers/arrive-pickup/{ride_id}` |
| start | POST | `/drivers/start-ride/{ride_id}` |
| complete | POST | `/drivers/complete-ride/{ride_id}` |
| hide | POST | `/drivers/rides/{ride_id}/hide` |
| dismiss (legacy) | POST | `/drivers/dismiss-ride/{ride_id}` → hide |

---

## Verification ritual (planned)

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
py -3.11 -m alembic upgrade head
py -3.11 -m pytest tests/test_driver_ride_idempotency_slice03.py -q

cd ..\driver-app
npm test
npm run test:e2e:ride-flow
npm run build
```

---

## Rollback

```powershell
cd backend
py -3.11 -m alembic downgrade 0025_driver_settings
```

Revert `api.js` ride methods to plain `call()`; remove banner from `MapHome.jsx`.

---

## PR body template (fill on ship)

```markdown
## HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03 — GO

### Summary
Adds cockpit offline visibility, bounded fetch retries on ride writes, and Idempotency-Key replay for driver lifecycle POSTs — without push, OSRM ops, or payments changes.

### Backend
- Migration: driver idempotency keys (TBD revision id)
- Ride POST handlers honor Idempotency-Key replay

### Frontend
- resilientFetch for ride-critical POSTs
- MapHome offline/degraded banner
- Client-generated Idempotency-Key per ride action

### Tests
- Backend idempotency tests PASS
- Frontend unit checks PASS
- ride-flow-ui-proof E2E PASS

### Out of scope
- web push, OSRM healthcheck, Connect onboarding, settings/profile schema
```

---

## Related

- Slice 02 GO: `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02.md`
- Playbook: `docs/HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01.md` (Section 4B)
- Program truth: `docs/CURRENT_TRUTH.md`
