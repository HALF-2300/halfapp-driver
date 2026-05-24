# HalfApp Project Overview

Date reviewed: 2026-05-18

This document is an expert-facing overview of the current `halfapp-driver` workspace. It is intentionally direct about what is implemented, what is demo-only, what is legacy/incomplete, and what should be reviewed before the project moves forward.

## Executive Summary

The repository contains a ride-hailing MVP centered on a driver app and FastAPI backend, plus separate legacy/tooling surfaces. The active HalfApp product spine is driver-only MVP first:

- `backend`: FastAPI API with SQLite/PostgreSQL-compatible SQLAlchemy models, JWT auth, driver ride lifecycle endpoints, rider create/cancel endpoints, notifications, and tests.
- `driver-app`: React/Vite driver-focused app with authentication, a mobile-style cockpit, backend-backed ride lifecycle, earnings/profile/notifications screens, Playwright tests, and explicit mock/simulation controls.
- `docs`: Existing contract/alignment documents for ride lifecycle and driver-app/backend behavior.

Inactive or isolated surfaces:

- `frontend` is a legacy/archive candidate. It has source files and build output, but no `frontend/package.json`, so it cannot be built from its directory in the current tree. Some of its frontend routes call backend endpoints that are not currently registered by `backend/main.py`.
- `video-gate` is separate/unrelated tooling for video verification/generation. It is not part of the ride-hailing MVP product path.
- Dormant backend routers are not active product surface unless registered by `backend/main.py` and covered by tests.

The correct current direction is to stabilize `backend` + `driver-app`, not to expand into a full rider-driver-admin marketplace.

## Verified Current Status

Commands run during this review:

- `python -m pytest backend\tests -q` from the repo root: `15 passed`, with `22` warnings from PyJWT about the default development `SECRET_KEY` being too short for HS256.
- `npm run build` from `driver-app`: success. Vite built `dist/index.html`, `dist/assets/index-DECarbLw.css`, and `dist/assets/index-CTPtSmVI.js`.
- `python -m pytest tests -q` from `video-gate`: `51 passed` as isolated tooling, not active ride-hailing product surface.
- `npm run build` from `frontend`: failed because `frontend/package.json` does not exist.

Important verified warning:

- The backend uses `SECRET_KEY=change_me` by default. Tests pass, but PyJWT correctly warns that the HMAC key is only 9 bytes. This must be replaced before any non-local deployment.

## Repository Layout

### `backend`

Purpose: API, database models, auth, ride lifecycle, notifications, and tests.

Key files:

- `backend/main.py`: FastAPI app entrypoint. Registers models, creates tables, ensures SQLite lifecycle columns, configures CORS, exposes `/health`, and includes selected routers.
- `backend/database.py`: SQLAlchemy engine/session setup. Defaults to local SQLite at `sqlite:///./halfapp_local.db`, overridable with `DATABASE_URL`.
- `backend/models/user.py`: User model and role enum.
- `backend/models/ride.py`: Ride model and ride lifecycle timestamps.
- `backend/services/auth.py`: Password hashing, JWT creation/decoding, current-user lookup, and public user serialization.
- `backend/services/datetime_utils.py`: UTC timestamp helper used to avoid deprecated `datetime.utcnow()`.
- `backend/routes/auth.py`: Driver registration/login and `/auth/me`.
- `backend/routes/drivers.py`: Driver ride lifecycle, profile, location, earnings, and statistics.
- `backend/routes/rider_rides.py`: Customer ride creation and customer cancellation.
- `backend/routes/notifications.py`: Authenticated notifications and admin notification send/delete helpers.
- `backend/schemas/*`: Pydantic schemas for ride lifecycle, rider ride creation/cancel, and earnings.
- `backend/tests/*`: Pytest coverage for smoke, ride lifecycle, earnings contract, and rider cancellation.

### `driver-app`

Purpose: Driver-specific React app. This is the most current frontend surface for the driver MVP.

Key files:

- `driver-app/package.json`: Vite/React scripts and dependencies.
- `driver-app/src/App.jsx`: HashRouter routes for login, map home, rides/trips, earnings, notifications, and profile.
- `driver-app/src/hooks/useAuth.jsx`: Auth context; handles login/register/logout and startup token rehydration.
- `driver-app/src/utils/api.js`: Central driver API wrapper, including explicit offline mock fallback when `VITE_ALLOW_OFFLINE_MOCK=true`.
- `driver-app/src/utils/driverState.js`: Shared cockpit state names plus legacy/offline simulation helpers. Active rides and earnings are backend-sourced.
- `driver-app/src/utils/rideModel.js`: Maps backend `RideDriverView` payloads into display fields without inventing unsupported map/ETA data.
- `driver-app/src/components/MapHome.jsx`: Mobile-style driver cockpit wired to backend ride lifecycle.
- `driver-app/src/components/TripsList.jsx`: Routed trips screen backed by backend completed rides.
- `driver-app/src/components/RideList.jsx`: Dormant backend-backed available/my rides component, not currently imported by `App.jsx`.
- `driver-app/src/components/Earnings.jsx`: Backend earnings screen.
- `driver-app/playwright.config.js`: Default Playwright lane, with offline mock enabled by default.
- `driver-app/playwright.trust.config.js`: Trust lane that starts backend on a separate port and runs with mock fallback disabled.

### `frontend`

Purpose: A multi-role React frontend for landing, driver/customer/admin pages, and a stability dashboard. It appears older or incomplete relative to the maintained `driver-app`.

Current facts:

- `frontend/src/App.jsx` uses `BrowserRouter` and supports driver, rider/customer, admin, and stability routes.
- `frontend/src/components/AdminDashboard.jsx` calls `/admin/*` backend routes.
- `frontend/src/components/CustomerDashboard.jsx` calls `/rides/my-rides` and `/rides/request`.
- `frontend/src/components/DriverDashboard.jsx` calls driver ride endpoints.
- `frontend/src/utils/stabilityTracker.js` tracks browser errors, session events, and API metrics locally.
- `frontend/dist` exists, so it was built at some point.
- `frontend/package.json` is missing, so `npm run build` cannot run from `frontend` now.

Important mismatch:

- `backend/main.py` does not currently include the admin router, admin-access router, legacy rides router, users router, or test router. Therefore, frontend calls such as `/admin/users`, `/admin/rides`, `/rides/my-rides`, and `/rides/request` are not available through the current FastAPI app as registered.

### `video-gate`

Purpose: Independent Python video verification and generation orchestration tool.

Key files:

- `video-gate/gate/cli.py`: CLI entrypoint for running the candidate quality gate against an MP4.
- `video-gate/gate/report.py`: Builds `CandidateQualityReportV1`.
- `video-gate/gate/flow.py`: Dense optical-flow stability analysis using OpenCV Farneback flow.
- `video-gate/gate/frames.py`: Frame extraction and first/last frame similarity.
- `video-gate/gate/probe.py`: ffprobe-based container/codec/metadata inspection.
- `video-gate/core/agents/agent2.py`: Motion Auditor agent that passes, warns, or rejects generated MP4s.
- `video-gate/core/orchestrator/loop.py`: Autonomous generation -> audit -> promote/retry loop.
- `video-gate/core/orchestrator/config.py`: ComfyUI URL, generation defaults, retry policy, and output directories.
- `video-gate/core/orchestrator/manifest.py`: `ShotManifestV1` persistence.

The video-gate subsystem is not directly integrated into the ride-hailing backend or driver app. It is a separate tool in the same workspace.

## Backend Architecture

The backend is a FastAPI application with SQLAlchemy ORM and Pydantic response contracts. Local development defaults to SQLite, while `DATABASE_URL` can point at another SQLAlchemy-supported database. The app creates tables at startup with `Base.metadata.create_all(bind=engine)`.

Startup behavior:

- Imports `models.user`, `models.ride`, and `routes.notifications` so their SQLAlchemy tables are registered.
- Calls `Base.metadata.create_all(bind=engine)`.
- Calls `ensure_ride_lifecycle_columns(engine)` for SQLite-only additive migrations of lifecycle columns on existing DB files.
- Configures CORS using built-in dev origins plus optional `CORS_ORIGINS`.
- Includes only these routers:
  - `/auth`
  - `/drivers`
  - `/notifications`
  - `/rides` from `routes.rider_rides`

Not registered in `backend/main.py` at review time:

- `routes.admin`
- `routes.admin_access`
- `routes.rides`
- `routes.users`
- `routes.test`

That means code exists for those routers, but those endpoints do not appear in the active FastAPI app unless `main.py` is changed.

## Backend Data Model

### User

Defined in `backend/models/user.py`.

Fields:

- `id`
- `email`
- `name`
- `password_hash`
- `role`: enum values `customer`, `driver`, `admin`
- `license_no`
- `is_active`
- `created_at`
- Driver profile fields: `phone`, `emergency_contact`, `vehicle_make`, `vehicle_model`, `vehicle_year`, `license_plate`, `insurance_policy`
- Driver presence fields: `availability`, `last_latitude`, `last_longitude`, `last_location_at`

Notes:

- `is_active` is stored as a string (`"true"`/`"false"`), not a Boolean.
- `license_no` is unique and nullable.
- Driver profile and location state are persisted on the user row.

### Ride

Defined in `backend/models/ride.py`.

Fields:

- `id`
- `customer_name`
- `customer_id`
- `driver_id`
- `status`
- `pickup_location`
- `destination`
- `fare_amount`
- `distance`
- `duration`
- Lifecycle timestamps: `created_at`, `accepted_at`, `arrived_pickup_at`, `started_at`, `completed_at`, `cancelled_at`
- `lifecycle_reason`
- `notes`
- `rating`

Notes:

- The database column names use `distance` and `duration`.
- API contracts expose these as `distance_km` and `duration_minutes`.
- `customer_id` is nullable for legacy compatibility, but customer-side cancel requires ownership.
- There are no foreign key constraints in the visible model definitions.

## Auth And Authorization

Authentication uses JWT Bearer tokens.

Key behavior:

- Passwords are hashed with bcrypt.
- Password input is truncated to bcrypt's 72-byte limit.
- JWTs use HS256 with `SECRET_KEY`.
- Access token expiry defaults to 60 minutes via `ACCESS_TOKEN_EXPIRE_MINUTES`.
- `/auth/register` is intentionally driver-only in the currently registered auth route.
- `/auth/login` rejects non-driver users because this backend entrypoint is currently aligned with the driver app.
- `/auth/me` returns a public user dict and omits `password_hash`.

Risks:

- Default `SECRET_KEY` is insecure and triggers PyJWT warnings in tests.
- Auth helpers do not appear to implement token revocation or refresh tokens.
- Role enforcement is route-level and manually repeated in multiple route modules.

## Ride Lifecycle Contract

The explicit source of truth is `docs/RIDE_LIFECYCLE_CONTRACT.md`.

Implemented statuses:

- `requested`
- `accepted`
- `arrived_at_pickup`
- `in_progress`
- `completed`
- `cancelled`

Reserved or future statuses:

- `en_route_to_pickup`
- `waiting_for_rider`
- `declined`
- `expired`

Current driver path:

1. Rider/customer creates request: `requested`, `driver_id=null`.
2. Driver accepts: `accepted`, `driver_id` set, `accepted_at` set.
3. Driver arrives at pickup: `arrived_at_pickup`, `arrived_pickup_at` set.
4. Driver starts ride: `in_progress`, `started_at` set.
5. Driver completes ride: `completed`, `completed_at` set, fare computed.

Driver decline behavior:

- Valid only from `accepted` and only for the assigned driver.
- Returns the ride to the open pool by setting `status="requested"` and clearing `driver_id`.
- Clears active-leg timestamps.
- Stores optional reason in `lifecycle_reason`.
- Does not create a terminal `declined` status in the MVP.

Rider cancel behavior:

- Valid only from `requested` or `accepted`.
- Requires the authenticated customer to own the ride.
- Sets `status="cancelled"`, `cancelled_at`, and optional `lifecycle_reason`.
- Preserves `driver_id` if already accepted so the driver can still see the cancellation in `my-rides`.

Fare behavior:

- `complete_ride` computes fare as `5.0 + distance * 1.5`.
- There is no visible pricing service, surge logic, payment authorization, driver payout ledger, or settlement model.

## Active Backend Endpoints

Registered by `backend/main.py`:

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /drivers/`
- `GET /drivers/my-rides`
- `GET /drivers/available-rides`
- `POST /drivers/simulate-ride`
- `POST /drivers/accept-ride/{ride_id}`
- `POST /drivers/decline-ride/{ride_id}`
- `POST /drivers/arrive-pickup/{ride_id}`
- `POST /drivers/start-ride/{ride_id}`
- `POST /drivers/complete-ride/{ride_id}`
- `GET /drivers/earnings`
- `PUT /drivers/profile`
- `POST /drivers/update-location`
- `GET /drivers/statistics`
- `POST /rides/`
- `POST /rides/{ride_id}/cancel`
- `GET /notifications/`
- `POST /notifications/send`
- `POST /notifications/{notification_id}/read`
- `DELETE /notifications/{notification_id}`
- `POST /notifications/driver/ride-alert`

Code exists but is not registered in the active app:

- `/admin/*`
- `/admin-access/*`
- Legacy `/rides/*` from `routes/rides.py`
- `/users/*`
- `/test/*`

## Driver App Architecture

The driver app is a Vite + React + React Router frontend. It is configured as a driver-only app and uses `HashRouter`, which makes routes look like `/#/rides`, `/#/earnings`, and so on.

Routes:

- `/login`: login and registration screen.
- `/`: `MapHome`, the cockpit-style driver home.
- `/rides`: `TripsList`.
- `/trips`: `TripsList`.
- `/earnings`: earnings screen.
- `/notifications`: notifications screen.
- `/profile`: profile screen.

Authentication:

- `useAuth.jsx` stores authenticated user state.
- `driver_token` and `driver_role` are stored in localStorage.
- Route protection accepts either in-memory `isAuthenticated` or a token in localStorage.
- There is a test-only guard bypass through `disable_guard=true`.

API access:

- `src/utils/api.js` centralizes calls.
- `VITE_API_BASE` defaults to `http://127.0.0.1:8000`.
- `VITE_ALLOW_OFFLINE_MOCK=true` enables explicit fallback to local mock data on selected failed API calls.
- Default development env enables offline mock mode through `driver-app/.env.development`.
- Playwright default lane also enables offline mock by default.
- Trust lane disables offline mock and runs a real backend.

Important honesty boundary:

- Offline mock mode is explicit and visible through `MockModeBanner`.
- API calls that mutate ride lifecycle (`acceptRide`, `declineRide`, `arrivePickup`, `startRide`, `completeRide`) do not have broad mock fallback in the current `api.js`; they call the backend directly.

## Driver App User Flows

### Driver Registration/Login

The driver app posts to:

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

The backend enforces driver-only access. Registration requires:

- email
- name
- password of at least 6 characters
- driver license number of at least 5 characters

### Cockpit Backend Flow

Implemented in `MapHome.jsx` and `driverState.js`.

This is backend-sourced for the active product path:

- Driver starts offline.
- Driver goes online.
- App fetches backend available rides and assigned rides.
- When explicit simulation is enabled, app can ask the backend to create a requested simulation ride.
- Driver accepts, arrives, starts, and completes the backend ride.
- Completed trips are stored by the backend.
- Trips and earnings screens read backend data.

Simulation mode is not live dispatch, but it is no longer a local-only trip ledger: simulated rides still use the backend lifecycle.

### Backend-Backed Ride Management

Implemented in the cockpit (`MapHome.jsx`) for the active path. `RideList.jsx` remains a dormant backend-backed component and is not currently routed by `driver-app/src/App.jsx`.

The active cockpit now:

- Fetch `/drivers/available-rides`.
- Fetch `/drivers/my-rides`.
- Creates explicit backend simulation rides through `/drivers/simulate-ride` only when `VITE_ENABLE_RIDE_SIMULATION=true`.
- Lets drivers accept requested rides through `/drivers/accept-ride/{ride_id}`.
- Advances assigned rides through arrive/start/complete.
- Refreshes backend earnings after completion.

`TripsList.jsx` and `Earnings.jsx` now read backend rides/earnings instead of local completed-trip storage for the active product path.

### Earnings

`Earnings.jsx` uses `GET /drivers/earnings` as its source of truth. If the backend is unavailable, it shows an error instead of substituting local completed-trip earnings as real product truth.

## Legacy Multi-Role Frontend

The `frontend` directory contains a broader React app:

- Landing page.
- Driver login/register/dashboard.
- Rider login/register/customer dashboard.
- Admin login/dashboard.
- Stability dashboard.
- A small design system under `frontend/src/design`.

Important concerns:

- It cannot currently be built because `frontend/package.json` is missing.
- It uses localStorage keys `token` and `role`, while `driver-app` uses `driver_token` and `driver_role`.
- It defaults `VITE_API_BASE` to `http://localhost:8000`, while `driver-app` defaults to `http://127.0.0.1:8000`.
- Its customer dashboard calls `/rides/my-rides` and `/rides/request`, but the active backend registers `POST /rides/` and `POST /rides/{ride_id}/cancel` from `rider_rides.py`.
- Its admin dashboard calls `/admin/*`, but `backend/main.py` does not include `routes.admin`.

Recommendation: treat `frontend` as either a legacy artifact to remove/archive or a separate product surface that needs a revival plan. It should not be assumed production-ready.

## Video Gate Architecture

`video-gate` is a separate subsystem for video QA and autonomous generation control.

Core concepts:

- A candidate MP4 is probed, hashed, sampled, and analyzed.
- Optical flow is measured to identify unstable motion.
- First/last frame similarity is measured to identify visual drift.
- A structured report decides whether the candidate is approved, warn-review, or rejected.
- Rejected candidates can produce retry guidance for generation parameters.

Agent 2, the Motion Auditor:

- Intercepts generated clips after generation.
- Runs ffprobe, optical-flow, and similarity checks.
- Returns `PASS`, `WARN`, or `REJECT`.
- `REJECT` blocks downstream upscaling and returns retry guidance such as lowering CFG.

Orchestrator loop:

1. Requests a batch of ComfyUI generations.
2. Audits each candidate with Agent 2.
3. Promotes the first approved or warn-review candidate.
4. If none qualifies, adjusts CFG/control strength and retries.
5. Saves a shot manifest with candidate records and final status.

This subsystem depends conceptually on ComfyUI at `http://127.0.0.1:8188` for real generation runs, but tests mock generation and pass locally.

## Configuration And Environment

Backend:

- `DATABASE_URL`: defaults to `sqlite:///./halfapp_local.db`.
- `SECRET_KEY`: defaults to `change_me`; must be replaced.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: defaults to `60`.
- `CORS_ORIGINS`: optional, unioned with dev defaults in current `main.py`.

Driver app:

- `VITE_API_BASE`: defaults to `http://127.0.0.1:8000`.
- `VITE_ALLOW_OFFLINE_MOCK`: enables explicit mock fallback when set to `true`.

Video gate:

- ComfyUI base URL is configured in code as `http://127.0.0.1:8188`.
- Candidate, promoted, and manifest directories live under `video-gate/output`.

## Testing And Quality Gates

Backend tests:

- `test_smoke.py`: health, register/login, profile, location.
- `test_ride_lifecycle.py`: driver lifecycle contract.
- `test_rider_cancel.py`: rider cancellation behavior.
- `test_earnings_contract.py`: earnings contract behavior.
- `conftest.py`: points tests at temporary SQLite before importing app.

Driver app tests:

- Default Playwright lane supports offline mock mode for fast UI/navigation checks.
- Trust lane disables mocks and starts a backend on a dedicated port.
- Tests cover auth flow, navigation flow, MVP cockpit demo loop, root registration/auth, and mock-off contract.

Video gate tests:

- Gate checks, Agent 2 behavior, and orchestrator behavior are covered.
- Current run: `51 passed`.

Build status:

- `driver-app`: builds successfully.
- `frontend`: cannot build without `package.json`.

## Main Risks And Gaps

### 1. Product surface split

There are at least two frontend directions:

- `driver-app`: current, driver-focused, tested, buildable.
- `frontend`: broader multi-role app, source present, build metadata missing, mismatched with active backend registration.

The controller decision for this phase is already made: continue with driver-only MVP first. `frontend` should remain legacy/archive candidate until explicitly approved later.

### 2. Simulation is explicit but not real dispatch

The mobile cockpit now uses backend ride lifecycle APIs for active product truth. Simulation can still be enabled explicitly, but simulated rides are created in the backend and move through the same lifecycle endpoints.

This matters because:

- Map coordinates remain approximate visualization, not live routing.
- Simulation rides are not real rider dispatch.
- Offline mock fallback can still emulate backend calls in local development when explicitly enabled.

The UI must keep simulation visibly labeled. The next product decision is not full marketplace expansion; it is how much real rider-request creation is needed after the driver-only cockpit is stable.

### 3. Insecure development defaults

The backend default `SECRET_KEY` is not acceptable outside local development. Tests currently warn about it.

Before deployment:

- Set a long random `SECRET_KEY`.
- Remove or tighten dev CORS origin union behavior.
- Decide token lifetime and refresh/logout story.

### 4. No real migration system

The backend uses `create_all` plus a SQLite-only helper for additive lifecycle columns. This works for local MVP work but is not a durable production migration strategy.

Before serious deployment:

- Add Alembic or another migration system.
- Define database constraints and foreign keys.
- Decide how to migrate existing SQLite data, if it matters.

### 5. Weak relational integrity

The visible SQLAlchemy models do not define foreign keys between rides and users. This allows inconsistent rows unless every route enforces integrity manually.

Suggested review:

- `Ride.customer_id -> User.id`
- `Ride.driver_id -> User.id`
- Delete/update behavior.
- Indexes for ride status, driver assignment, and customer ownership.

### 6. Admin code is not active in the app

Admin route code exists but is not registered. The legacy frontend expects `/admin/*`, but the active backend does not expose it.

This may be deliberate if the driver app is the focus. If admin functionality is needed, it must be registered, tested, and secured.

### 7. Admin access codes are in memory

`routes/admin_access.py` stores admin access codes in a module-level dictionary. This is demo-only:

- Codes vanish on restart.
- Codes are not persisted or audited.
- `/admin-access/list-codes` exposes generated codes if registered.

This should not be enabled in production without redesign.

### 8. Notifications are simple and route-owned

The `Notification` SQLAlchemy model lives inside `routes/notifications.py`. It works because `main.py` imports that route module before `create_all`, but route modules owning ORM models can make the project harder to reason about as it grows.

Consider moving notification models into `backend/models`.

### 9. Driver location is stored but not used for matching

`/drivers/update-location` persists latitude/longitude, but available rides are not spatially filtered. There is no dispatch algorithm, geocoding, route engine, ETA calculation, or map tile integration in the backend contract.

This is acceptable for MVP if stated clearly, but it is a major product gap for a ride-hailing app.

### 10. Fare and earnings are simplified

Fare is computed with constants in `complete_ride`. There is no:

- rider quote acceptance
- payment capture
- driver payout ledger
- fees/taxes/tips
- refunds/cancellations pricing
- currency model

This is fine for MVP, but should not be presented as production billing.

### 11. Dead or legacy modules exist

Examples:

- `backend/services/auth_optimized.py` appears to be dead code according to existing docs.
- `backend/routes/rides.py`, `users.py`, and `test.py` are not included in `main.py`.
- `driver-app/src/utils/api_with_mock.jsx` appears to be an older alternative API helper.
- `frontend` is incomplete as a buildable app.

These should be either revived intentionally or archived/removed to lower confusion.

## Suggested Next Steps

### Step 1: Preserve the product spine

The primary path is already selected:

- Driver-only MVP: keep `backend` + `driver-app`.
- Keep `frontend` as a legacy/archive candidate.
- Keep `video-gate` isolated from ride-hailing MVP work.
- Keep dormant backend routers out of active surface unless explicitly registered and tested later.

Do not expand into the full rider-driver-admin marketplace before the driver-only MVP is truthful.

### Step 2: Keep the cockpit backend-sourced

- Keep backend available ride polling or an eventual subscription as the active path.
- Keep backend statuses mapped to cockpit states.
- Keep accept/arrive/start/complete on backend lifecycle endpoints.
- Keep completed trips and earnings backend-sourced.
- Keep simulation behind `VITE_ENABLE_RIDE_SIMULATION=true` and visible UI labeling.

### Step 3: Harden backend configuration

Before any public environment:

- Require `SECRET_KEY` from environment.
- Use a long random key.
- Replace development CORS union with explicit production origins.
- Add proper migration tooling.
- Add foreign keys and indexes.
- Consider token refresh/revocation.

### Step 4: Resolve frontend legacy state

Either:

- Restore `frontend/package.json`, align routes, register backend routers, and add tests.

Or:

- Rename/archive `frontend` so future contributors do not assume it is active.

### Step 5: Keep contracts as source of truth

The project already has a good contract document in `docs/RIDE_LIFECYCLE_CONTRACT.md`. Continue that pattern:

- Backend schemas should generate OpenAPI from the same contract.
- Frontend should render only fields present in the contract.
- Tests should check that UI does not invent unavailable map/ETA/earnings data.

## Expert Review Questions

These are the questions I would ask the expert reviewer to answer:

1. Should the project move forward as a driver-only MVP or as a full rider-driver-admin platform?
2. Should `frontend` be revived, removed, or split into separate apps?
3. Should `MapHome` become the real backend-connected driver workflow?
4. What is the minimum production deployment target: local demo, private beta, or real public use?
5. Does the backend need PostgreSQL now, or is SQLite still acceptable for the next phase?
6. What ride dispatch model is expected: open pool, nearest-driver assignment, scheduled rides, or manual/admin-created rides?
7. What is the payment/fare source of truth: estimated fare, final metered fare, or admin-entered fare?
8. Are admin features required in the next milestone?
9. Should `video-gate` remain in this repository or be separated as its own tool?
10. What security baseline is required before sharing the app externally?

## Bottom Line

The project has a working and tested backend ride lifecycle, a buildable driver app, and a tested video gate subsystem. The main issue is not that nothing works; the main issue is that multiple generations of the product exist side by side.

For forward progress, the team should first choose the product spine, then remove or clearly isolate the inactive surfaces. After that, the most valuable engineering move is to connect the driver cockpit to the backend lifecycle so the most polished UI and the most truthful backend contract become one coherent product.
