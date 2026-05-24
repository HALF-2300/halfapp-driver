# HALFAPP_PHASE2_ACCEPTANCE_AND_PHASE3_PRECHECK_01

Date reviewed: 2026-05-18

## Verdict

`GO` for accepting the previous `PARTIAL_GO` baseline as real.

`PARTIAL_GO` remains the overall project status because Phase 3 hardening is not implemented yet. The next safe implementation slice is a narrow production/beta `SECRET_KEY` boot guard with tests.

## Previous PARTIAL_GO Accepted

Accepted as current baseline:

- Phase 1 product spine stabilization is accepted.
- Phase 2 cockpit/backend truth alignment is accepted.
- Active product spine is `backend` + `driver-app`.
- `frontend` remains a legacy/archive candidate and was not physically deleted.
- `video-gate` remains unrelated tooling and was not touched.
- Dormant backend routers are not active product surface.
- Cockpit now uses backend ride lifecycle.
- `TripsList` and `Earnings` now read backend data.
- Simulation creates backend rides instead of local-only fake trips.

## Backend Routes Verified

Active backend route registration remains limited to `backend/main.py`:

- `/health`
- `/auth/*`
- `/drivers/*`
- `/rides/*` from `routes.rider_rides.py`
- `/notifications/*`

Confirmed dormant prefixes return inactive/not found:

| Prefix | Status checked | Result |
| --- | ---: | --- |
| `/admin` | `GET /admin` | `404` |
| `/admin-access` | `GET /admin-access` | `404` |
| `/test` | `GET /test` | `404` |
| `/users` | `GET /users` | `404` |

Confirmed active simulation route:

- `POST /drivers/simulate-ride` exists in OpenAPI.
- It is under the active driver router.
- It requires `require_driver`, so it requires a driver bearer token.
- It creates a normal backend `Ride` with `status="requested"` and `lifecycle_reason="simulation"`.
- It does not bypass accept/arrive/start/complete lifecycle rules.

## Cockpit / Backend Truth Verified

`MapHome.jsx`:

- Fetches backend available rides through `driverAPI.getAvailableRides()`.
- Fetches backend assigned rides through `driverAPI.getMyRides()`.
- Fetches backend earnings through `driverAPI.getEarnings()`.
- Maps backend ride statuses into cockpit states.
- Accepts rides through `driverAPI.acceptRide()`.
- Arrives at pickup through `driverAPI.arrivePickup()`.
- Starts rides through `driverAPI.startRide()`.
- Completes rides through `driverAPI.completeRide()`.
- Refreshes backend truth after completion.

`TripsList.jsx`:

- Loads `driverAPI.getMyRides()`.
- Filters backend rides with `status === "completed"`.
- Computes visible trip counts/earnings from backend ride fields.
- Does not read `halfapp_trips`.

`Earnings.jsx`:

- Loads `driverAPI.getEarnings()`.
- Displays `earnings_summary` and `recent_rides` from the backend response.
- Shows an unavailable state if backend earnings fail.
- Does not substitute local trip earnings as real product truth.

Acceptance result:

- No active ride lifecycle or active earnings UI depends on local completed-trip storage.

## localStorage Boundary

| Key | Current use | Classification | Product-truth risk |
| --- | --- | --- | --- |
| `driver_token` | Stores JWT or mock token for authenticated driver sessions. | Auth token | Acceptable for current MVP auth storage; should be reviewed later for security hardening. |
| `driver_role` | Stores expected role string used by driver app guard. | Auth token / auth metadata | Acceptable as client hint only; backend remains source of authorization truth. |
| `disable_guard` | Test-only route guard bypass in `App.jsx`. | UI/test helper | Dangerous outside tests; should not be set by product UI. |
| `halfapp_driver_state` | Persists cockpit online/offline UI state. | UI preference | Acceptable UI state; not ride truth. |
| `halfapp_active_ride` | Legacy helper in `driverState.js`; no longer used by active `MapHome`. | Dangerous if treated as product truth | Should be removed in a cleanup pass after confirming no active imports. |
| `halfapp_trips` | Legacy local completed-trip helper in `driverState.js`; no longer used by `TripsList` or `Earnings`. | Dangerous if treated as product truth | Must not be used for active lifecycle/earnings. Candidate for cleanup. |
| `halfapp_driver_database` | Offline mock login/register/profile backing store in `api.js`. | Offline mock helper | Dev-only. Dangerous if shown as production identity truth. |
| `halfapp_mock_backend_rides` | Offline mock backend-ride store used only when `VITE_ALLOW_OFFLINE_MOCK=true` fallback paths run. | Simulation/dev-only helper | Dev-only. Dangerous if treated as backend truth; trust lane disables mock fallback. |
| `simple_drivers` | Legacy `simpleAuth.js` local driver registry. | Offline mock / legacy helper | Dormant/legacy. Dangerous if product imports it later. |
| dynamic storage-test keys | `systemVerification.js` temporarily writes and removes a test value. | Test/helper | Acceptable if kept out of product truth paths. |

Boundary conclusion:

- Active ride lifecycle and active earnings are backend-sourced.
- Remaining localStorage helpers include legacy/dev-only keys that should be cleaned up later, but they are not currently the active source for completed rides/earnings.

## Simulation Safety Status

Verified controls:

- `driver-app/.env.development` sets `VITE_ENABLE_RIDE_SIMULATION=true`.
- `driver-app/playwright.trust.config.js` sets `VITE_ENABLE_RIDE_SIMULATION=false`.
- `MockModeBanner.jsx` shows a visible development banner when offline mock fallback or ride simulation is enabled.
- `MapHome.jsx` only renders simulation controls when `ALLOW_RIDE_SIMULATION` is true.
- The simulation control text says `Create backend simulation ride`.
- The simulation helper calls `POST /drivers/simulate-ride`.
- Backend simulation creates a backend `Ride`, not a local-only trip.

Recommendation:

- `/drivers/simulate-ride` should be disabled or dev-gated outside local/dev before beta or production.
- Smallest safe policy: require an explicit backend environment mode and allow this route only when `HALFAPP_ENV` is local/dev/test. In beta/production it should return `404` or `403`.
- Do not add admin gating yet unless admin routes and role tests are intentionally brought into scope.

## SECRET_KEY Hardening Recommendation

Current state:

- `backend/services/auth.py` defaults `SECRET_KEY` to `change_me`.
- Test runs pass but emit PyJWT `InsecureKeyLengthWarning`.
- This is acceptable only for local/dev, not beta/production.

Smallest next safe Phase 3 slice:

1. Add an environment mode variable, for example `HALFAPP_ENV`, with local/dev default.
2. In beta/production modes, refuse backend boot if:
   - `SECRET_KEY` is missing.
   - `SECRET_KEY` equals `change_me`.
   - `SECRET_KEY` is shorter than 32 bytes for HS256.
3. Keep local/dev boot behavior working with the existing default, but emit or preserve warnings.
4. Add focused tests that import/reload the auth config under mode/key combinations:
   - local/dev + default key: allowed.
   - beta + missing/default key: fails.
   - production + missing/default key: fails.
   - beta/production + long explicit key: allowed.

Do not combine this with migration work, payments, dispatch, or admin platform work.

## Files Inspected

Backend:

- `backend/main.py`
- `backend/routes/drivers.py`
- `backend/tests/test_active_route_surface.py`
- `backend/tests/test_ride_lifecycle.py`
- `backend/services/auth.py`

Driver app:

- `driver-app/src/components/MapHome.jsx`
- `driver-app/src/components/TripsList.jsx`
- `driver-app/src/components/Earnings.jsx`
- `driver-app/src/components/MockModeBanner.jsx`
- `driver-app/src/utils/api.js`
- `driver-app/src/utils/driverState.js`
- `driver-app/src/hooks/useAuth.jsx`
- `driver-app/src/App.jsx`
- `driver-app/.env.development`
- `driver-app/playwright.trust.config.js`

Scope intentionally not touched:

- `frontend`
- `video-gate`
- payments
- nearest-driver dispatch
- rider/admin marketplace expansion
- database migration/constraints work

## Commands Run

Backend tests:

```powershell
python -m pytest backend\tests -q
```

Result: `18 passed, 24 warnings`.

Driver app production build:

```powershell
npm run build
```

Result: passed.

Driver cockpit smoke:

```powershell
npx playwright test tests/smoke-mvp.spec.ts
```

Result: `1 passed`.

Trust/mock-off suite:

```powershell
npx playwright test --config playwright.trust.config.js
```

Result: `7 passed`.

Dormant-prefix and simulation-route check:

```powershell
python -c "from fastapi.testclient import TestClient; from main import app; c=TestClient(app); paths=['/admin','/admin-access','/test','/users']; print({p:c.get(p).status_code for p in paths}); print('/drivers/simulate-ride' in app.openapi()['paths'])"
```

Result:

```text
{'/admin': 404, '/admin-access': 404, '/test': 404, '/users': 404}
True
```

## Tests Passed / Failed

Passed:

- Backend pytest: `18 passed`.
- Driver app build: passed.
- Driver cockpit Playwright smoke: `1 passed`.
- Trust/mock-off Playwright suite: `7 passed`.
- Dormant prefix check: all listed prefixes returned `404`.

Warnings:

- PyJWT warns that default development `SECRET_KEY` is too short for HS256.
- Browser dependency freshness warnings from Vite/Browserslist.

Failed:

- None in the final verification pass.

## Exact Next Implementation Task

`HALFAPP_PHASE3_SECRET_KEY_BOOT_GUARD_01`

Scope:

- Implement a mode-aware backend boot guard for `SECRET_KEY`.
- Use an explicit environment variable such as `HALFAPP_ENV`.
- Preserve local/dev behavior.
- Fail fast in beta/production when `SECRET_KEY` is missing, `change_me`, or shorter than 32 bytes.
- Add focused tests for allowed/blocked key+environment combinations.

Non-goals:

- Do not change payments.
- Do not add nearest-driver dispatch.
- Do not revive admin/frontend.
- Do not alter video-gate.
- Do not start DB migration work.
