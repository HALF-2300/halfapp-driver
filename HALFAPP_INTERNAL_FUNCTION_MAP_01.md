# HalfApp Internal Function Map 01

Date: 2026-05-18

Verdict: **PARTIAL_GO**

The current program has a real driver-only backend lifecycle and an active React driver cockpit that calls it. It is not yet a fully truthful driver-like program because the polished cockpit still has simulated map coordinates, a local online/offline UI state, a local "hide for now" request action, and dormant/legacy surfaces that could be confused with active product if reintroduced.

No code changes were made for this report. Documentation only.

## Active Product Surfaces

- `backend`: FastAPI app started from `backend/main.py`.
- `driver-app`: React/Vite driver-only app routed by `driver-app/src/App.jsx`.
- `docs/RIDE_LIFECYCLE_CONTRACT.md`: current lifecycle contract for active backend driver/rider ride endpoints.

## Inactive / Legacy Surfaces

- `frontend`: legacy multi-role frontend. It is not active and has no `frontend/package.json`.
- `video-gate`: separate video tooling, unrelated to driver app function.
- Dormant backend router modules: `backend/routes/admin.py`, `backend/routes/admin_access.py`, `backend/routes/rides.py`, `backend/routes/users.py`, `backend/routes/test.py`.
- Dormant driver UI/component paths: `driver-app/src/components/RideList.jsx`, `Dashboard.jsx`, `AdminDashboard.jsx`, `DatabaseTest.jsx`, `SimpleDashboard.jsx`, `SimpleLoginTest.jsx`, `TestApp.jsx`, `DiagnosticApp.jsx`, `App-simple.jsx`, `App-working.jsx`, `utils/simpleAuth.js`, `utils/api_with_mock.jsx`.

## Backend Boot Path

`backend/main.py` imports `Base`, `engine`, and `ensure_ride_lifecycle_columns` from `backend/database.py`, imports active ORM model modules, creates tables, applies SQLite-only ride lifecycle column patches, creates the FastAPI app, configures CORS, defines `/health`, then includes only four routers.

Models loaded during boot:

- `models.user`: registers `User`.
- `models.ride`: registers `Ride`.
- `routes.notifications`: registers the `Notification` model inside the route file.

Database configuration:

- `DATABASE_URL` defaults to `sqlite:///./halfapp_local.db`.
- If the URL starts with `sqlite`, SQLAlchemy receives `check_same_thread=False`.
- PostgreSQL or other SQLAlchemy URLs can be supplied through `DATABASE_URL`.
- `ensure_ride_lifecycle_columns()` only alters SQLite databases, adding lifecycle columns to existing `rides` tables.

## Backend Route Map

Active registered paths from `backend/main.py`:

| Area | Active paths |
| --- | --- |
| Health | `GET /health` |
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Drivers | `GET /drivers/`, `GET /drivers/my-rides`, `GET /drivers/available-rides`, `POST /drivers/simulate-ride`, `POST /drivers/accept-ride/{ride_id}`, `POST /drivers/decline-ride/{ride_id}`, `POST /drivers/arrive-pickup/{ride_id}`, `POST /drivers/start-ride/{ride_id}`, `POST /drivers/complete-ride/{ride_id}`, `GET /drivers/earnings`, `PUT /drivers/profile`, `POST /drivers/update-location`, `GET /drivers/statistics` |
| Rider rides | `POST /rides/`, `POST /rides/{ride_id}/cancel` |
| Notifications | `GET /notifications/`, `POST /notifications/send`, `POST /notifications/{notification_id}/read`, `DELETE /notifications/{notification_id}`, `POST /notifications/driver/ride-alert` |

Inactive route modules that exist but are not registered:

- `routes.admin`: admin users, drivers, rides, analytics, active toggles.
- `routes.admin_access`: demo/in-memory admin access-code registration.
- `routes.rides`: older `/rides` router with a simplified create/list surface.
- `routes.users`: demo `/users/` list.
- `routes.test`: database connection and driver test-log endpoints.

Important mismatch: `driver-app/src/utils/api.js` still contains `testDatabaseConnection()`, `sendTestData()`, and `getTestLogs()` methods pointing at `/test/*`, but `/test` is not mounted in `backend/main.py`.

## Auth Flow

Driver registration:

- Frontend: `LoginScreen.jsx` sign-up mode validates email, password, name, and `license_no`, then calls `useAuth.register()`.
- API client: `driverAPI.register()` sends `POST /auth/register` with `role: "driver"`.
- Backend: `routes/auth.py` rejects non-driver roles, requires a driver license number, creates a `User`, returns JWT plus public user profile.

Driver login:

- Frontend: `LoginScreen.jsx` sign-in mode calls `useAuth.login()`.
- API client: `driverAPI.login()` sends `POST /auth/login`.
- Backend: rejects missing account, wrong password, inactive account, and non-driver role.

Token storage:

- `driverAPI.login()` and `driverAPI.register()` write `driver_token` and `driver_role` to `localStorage`.
- `driverAPI.logout()` removes both.
- `ProtectedRoute` allows access if `useAuth` has a user or `driver_token` exists. It also has a test-only `disable_guard` localStorage bypass.

`/auth/me`:

- `useAuth` probes `driverAPI.getProfile()` on startup when `driver_token` exists and `driver_role === "driver"`.
- Backend reads the bearer token, decodes it, loads the user by email, and returns a public user dict.

Role enforcement:

- Driver backend endpoints use `require_driver()` and require `UserRole.DRIVER`.
- Rider create/cancel endpoints require `UserRole.CUSTOMER`.
- Notification read/list require any authenticated user; notification send/delete and ride-alert require admin.
- The active driver app intentionally blocks customer/admin login.

Driver-only versus legacy/multi-role:

- Active `driver-app` is driver-only.
- Backend still has customer role support for rider ride create/cancel.
- Admin and older multi-role routes exist in files but are not active because `main.py` does not include them.

## Frontend Route Map

Active routes in `driver-app/src/App.jsx`:

| Route | Component | Current role |
| --- | --- | --- |
| `/#/login` | `LoginScreen` | Driver login/sign-up screen. |
| `/#/` | `MapHome` | Main home/cockpit. |
| `/#/rides` | `TripsList` | Backend completed trips list, despite the route name. |
| `/#/trips` | `TripsList` | Backend completed trips list. |
| `/#/earnings` | `Earnings` | Backend earnings. |
| `/#/notifications` | `Notifications` | Backend notifications plus demo-only messages tab. |
| `/#/profile` | `Profile` | Backend profile/statistics/notifications/earnings. |
| catch-all | redirect to `/` | Cockpit home. |

Screens using backend data:

- `MapHome`: `GET /drivers/available-rides`, `GET /drivers/my-rides`, `GET /drivers/earnings`, lifecycle transition endpoints, optional `POST /drivers/simulate-ride`.
- `TripsList`: `GET /drivers/my-rides`, filters `completed`.
- `Earnings`: `GET /drivers/earnings`.
- `Notifications`: `GET /notifications/`; messages tab is demo-only.
- `Profile`: `GET /auth/me`, `GET /drivers/statistics`, `GET /notifications/`, `GET /drivers/earnings`, `PUT /drivers/profile`, `POST /notifications/{id}/read`.

Screens/components not routed by `App.jsx`:

- `RideList.jsx`: connects to real backend ride endpoints but is dormant.
- `Dashboard.jsx`, `AdminDashboard.jsx`, and diagnostic/simple apps are not part of the active route tree.

## Ride Lifecycle Map

| State | Backend endpoint/source | Frontend component | Source of truth | Current truth status |
| --- | --- | --- | --- | --- |
| `requested` | `POST /rides/` by customer, or `POST /drivers/simulate-ride` for explicit driver MVP simulation. Listed by `GET /drivers/available-rides`. | `MapHome` shows first available ride when online. Dormant `RideList` can list available rides. | Backend `rides` table. | Real backend state. Simulation rides are explicit backend rows with `lifecycle_reason="simulation"`. |
| `accepted` | `POST /drivers/accept-ride/{ride_id}` sets `driver_id`, `accepted_at`. | `MapHome` Accept ride button; dormant `RideList` Accept Ride button. | Backend `rides` table. | Real backend state. |
| `arrived_at_pickup` | `POST /drivers/arrive-pickup/{ride_id}` sets `arrived_pickup_at`. | `MapHome` advance button; dormant `RideList` active actions. | Backend `rides` table. | Real backend state. |
| `in_progress` | `POST /drivers/start-ride/{ride_id}` sets `started_at`. | `MapHome` advance button; dormant `RideList` active actions. | Backend `rides` table. | Real backend state. |
| `completed` | `POST /drivers/complete-ride/{ride_id}` sets `completed_at` and computes `fare_amount`. | `MapHome` complete action, `TripsList`, `Earnings`, `Profile` stats. | Backend `rides` table. | Real backend state. |
| `cancelled` | `POST /rides/{ride_id}/cancel` by owning customer from `requested` or `accepted`. | No active driver-app route initiates rider cancel. Dormant `RideList` can display cancelled assigned rides without actions. | Backend `rides` table. | Real backend state, but mostly not surfaced in active cockpit beyond backend refresh behavior. |

Reserved but not actively emitted states:

- `en_route_to_pickup`: backend accepts it as a source for arrival, but no active endpoint sets it.
- `waiting_for_rider`: backend accepts it as a source for start, but no active endpoint sets it.
- `declined` and `expired`: documented as future/reserved, not emitted by active backend.

Driver decline:

- Backend `POST /drivers/decline-ride/{ride_id}` only applies after `accepted`; it returns the ride to `requested`, clears `driver_id`, clears active timestamps, and optionally records `lifecycle_reason`.
- Active `MapHome` does not call this endpoint for an incoming `requested` ride. Its "Hide for now" button only clears the cockpit's local selected ride; the backend ride remains requested.
- Dormant `RideList.jsx` does call `declineRide()` for accepted rides.

## Demo / localStorage Map

| Key / location | Reads/writes | Classification | Later backend requirement |
| --- | --- | --- | --- |
| `driver_token` in `api.js`, `useAuth.jsx`, `App.jsx` | Stores bearer token and gates protected routes. | Necessary local auth cache, acceptable. | Keep as auth token storage or replace with more secure auth strategy later. |
| `driver_role` in `api.js`, `useAuth.jsx` | Stores expected role string. | UI auth helper, acceptable but not authoritative. | Backend remains authority. |
| `disable_guard` in `App.jsx` | Test-only protected-route bypass. | Safe only for tests. Dangerous if used outside E2E setup. | Keep isolated to tests or remove when no longer needed. |
| `halfapp_driver_state` in `driverState.js` | Persists online/offline cockpit state. | Safe UI preference/state helper. | Backend-backed availability/presence should become authoritative later. |
| `halfapp_active_ride` in `driverState.js` | Helper functions exist but active `MapHome` does not import them. | Dormant legacy/demo storage; dangerous if revived as real ride truth. | Do not present as real. Use backend `my-rides`. |
| `halfapp_trips` in `driverState.js` | Helper functions exist but current `TripsList` uses backend. | Demo-only legacy trip cache; dangerous if presented as real. | Must stay non-authoritative; backend completed rides are source. |
| `halfapp_driver_database` in `api.js` | Offline mock driver accounts when `VITE_ALLOW_OFFLINE_MOCK=true`. | Demo-only mock auth database. | Never present as production auth. |
| `halfapp_mock_backend_rides` in `api.js` | Offline mock ride lifecycle when `VITE_ALLOW_OFFLINE_MOCK=true`. | Demo-only mock backend. Dangerous if mock mode is hidden. | Real backend rides must remain source when mock is off. |
| `simple_drivers` in `utils/simpleAuth.js` | Dormant simple-auth local database. | Legacy/dormant; dangerous if reactivated as real auth. | Do not use in active driver path. |
| `DEMO_MESSAGES` in `Notifications.jsx` | Static sample messages tab. | Demo-only and labeled as not live rider chat. | Requires future backend chat/message support. |
| Map fallback coordinates in `MapHome.jsx` | Approximate visualization for pickup/dropoff labels. | Demo visualization; dangerous if presented as real location/ETA. | Requires backend contract fields for coordinates/route/ETA. |

## Backend-Backed Ride Components

`RideList.jsx` already connects to:

- Available rides: `driverAPI.getAvailableRides()`.
- My rides: `driverAPI.getMyRides()`.
- Accept ride: `driverAPI.acceptRide()`.
- Decline ride: `driverAPI.declineRide()`.
- Arrive pickup: `driverAPI.arrivePickup()`.
- Start ride: `driverAPI.startRide()`.
- Complete ride: `driverAPI.completeRide()`.

However, `RideList.jsx` is not imported or routed by `driver-app/src/App.jsx`. The active `/rides` route displays `TripsList`, not `RideList`. Therefore `RideList.jsx` is backend-capable but dormant.

## Cockpit / Backend Truth Gap

What is true now:

- The active cockpit calls real backend ride lifecycle endpoints.
- Trips and earnings are backend-backed.
- Explicit simulation creates backend-owned requested rides when `VITE_ENABLE_RIDE_SIMULATION=true`.

What is still not fully truthful:

- The cockpit map uses fallback Portland coordinates and not backend-provided pickup/dropoff coordinates.
- Online/offline state is local browser state, not backend driver availability/presence.
- "Hide for now" on an incoming request only hides the selected ride locally; it does not create a backend decline, expiry, or dispatch decision.
- There is no nearest-driver dispatch or real rider-driver assignment workflow beyond first available ride pulled by the cockpit.
- `RideList.jsx` has more complete ride-management controls but is dormant.
- Offline mock mode can simulate auth/rides in localStorage when explicitly enabled.

First connection needed to make the program more driver-like:

1. Make `MapHome` and/or the `/rides` route use one canonical backend ride-management surface for available, active, cancelled, and completed rides.
2. Replace local-only "Hide for now" with a truthful backend action or rename it as local-only filtering.
3. Backend driver availability should become the source of truth for online/offline status.
4. Add real location fields to the backend ride contract before presenting map position, ETA, or route as real.

## Recommended Next Implementation Slice

Do not start payments, nearest-driver dispatch, admin platform, or full marketplace work yet.

Recommended first slice:

- Route or fold the useful parts of `RideList.jsx` into the active cockpit/trips flow.
- Add an explicit backend-backed action for driver request dismissal only if the product wants a true decline/rebroadcast ledger; otherwise label cockpit dismissal as local filtering.
- Persist driver availability through `PUT /drivers/profile` or a dedicated presence endpoint, then have `MapHome` read that backend value.
- Keep trips and earnings backend-only.
- Keep simulation behind explicit env flags and visible labeling.

## Current Known Commands

Backend:

- `python -m pytest backend\tests -q`
- From `backend`: `uvicorn main:app --reload --host 127.0.0.1 --port 8000`
- From `backend`: `py -3.11 -m pytest tests/test_ride_lifecycle.py -q`

Driver app:

- From `driver-app`: `npm run dev`
- From `driver-app`: `npm run build`
- From `driver-app`: `npm run preview`
- From `driver-app`: `npm run test:e2e`
- From `driver-app`: `npm run test:e2e:trust`

These commands come from `backend/main.py`, `docs/RIDE_LIFECYCLE_CONTRACT.md`, and `driver-app/package.json`.

## Commands Run For This Report

- `python -m pytest backend\tests -q`: **18 passed**, with 24 warnings about the default `SECRET_KEY=change_me` being too short for HS256.
- `npm run build` from `driver-app`: **passed**. Vite emitted stale Baseline/Browserslist data warnings.

## Files Inspected

- `README.md`
- `docs/RIDE_LIFECYCLE_CONTRACT.md`
- `backend/main.py`
- `backend/database.py`
- `backend/requirements.txt`
- `backend/services/auth.py`
- `backend/models/user.py`
- `backend/models/ride.py`
- `backend/routes/auth.py`
- `backend/routes/drivers.py`
- `backend/routes/rider_rides.py`
- `backend/routes/notifications.py`
- `backend/routes/admin.py`
- `backend/routes/admin_access.py`
- `backend/routes/rides.py`
- `backend/routes/users.py`
- `backend/routes/test.py`
- `backend/tests/test_active_route_surface.py`
- `backend/tests/test_ride_lifecycle.py`
- `backend/tests/test_rider_cancel.py`
- `driver-app/package.json`
- `driver-app/playwright.config.js`
- `driver-app/playwright.trust.config.js`
- `driver-app/src/App.jsx`
- `driver-app/src/hooks/useAuth.jsx`
- `driver-app/src/utils/api.js`
- `driver-app/src/utils/driverState.js`
- `driver-app/src/utils/rideModel.js`
- `driver-app/src/components/LoginScreen.jsx`
- `driver-app/src/components/MapHome.jsx`
- `driver-app/src/components/TripsList.jsx`
- `driver-app/src/components/Earnings.jsx`
- `driver-app/src/components/RideList.jsx`
- `driver-app/src/components/Profile.jsx`
- `driver-app/src/components/Notifications.jsx`
- `driver-app/tests/trust/stage1-honesty.spec.ts`

## Final Judgment

We now know how the current program functions internally. The active driver MVP has a real backend ride lifecycle, real driver auth, backend-backed trips/earnings/profile/notifications, and a cockpit that already calls backend lifecycle endpoints. The main remaining truth gap is not the absence of a lifecycle backend; it is the mismatch between the polished cockpit experience and the limited backend contract for dispatch, availability, request dismissal, location, ETA, and map truth.
