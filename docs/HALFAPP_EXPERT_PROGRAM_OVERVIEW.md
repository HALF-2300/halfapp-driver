# HalfApp Expert Program Overview

Date: 2026-05-18

Audience: engineers, reviewers, technical operators, and product decision-makers who need a dense understanding of what the current program is, what is actually implemented, and where the system should move next.

## 1. Program Definition

HalfApp in this workspace is currently a driver-only ride-hailing MVP. The active product spine is:

- `backend`: FastAPI service for auth, driver profiles, driver availability, ride lifecycle, rider ride create/cancel, notifications, and earnings.
- `driver-app`: React/Vite driver application that authenticates drivers and renders the driver cockpit, trips, earnings, notifications, and profile screens.
- `docs/RIDE_LIFECYCLE_CONTRACT.md`: the current source of truth for the ride lifecycle and API payload behavior.

The program is not yet a full marketplace. It does not yet have production-grade rider apps, admin operations, real payments, audited fare splits, real dispatch fairness, route calculation, ETA calculation, geocoding, or complete transparency ledger support.

The safest expert interpretation is:

- The backend is the authority for ride lifecycle and completed-trip earnings.
- The active frontend is driver-only.
- Simulation is allowed only when explicit and backend-backed.
- Legacy code must not be treated as product behavior until it is revived through entrypoint registration, tests, and contract updates.

## 2. Source Boundaries

Active product surfaces:

- `backend/main.py`
- `backend/routes/auth.py`
- `backend/routes/drivers.py`
- `backend/routes/rider_rides.py`
- `backend/routes/notifications.py`
- `backend/models/user.py`
- `backend/models/ride.py`
- `backend/services/auth.py`
- `backend/services/dispatch.py`
- `driver-app/src/App.jsx`
- `driver-app/src/components/MapHome.jsx`
- `driver-app/src/components/TripsList.jsx`
- `driver-app/src/components/Earnings.jsx`
- `driver-app/src/components/Notifications.jsx`
- `driver-app/src/components/Profile.jsx`
- `driver-app/src/hooks/useAuth.jsx`
- `driver-app/src/utils/api.js`
- `driver-app/src/utils/rideModel.js`
- `driver-app/src/utils/driverState.js`

Inactive, legacy, or isolated surfaces:

- `frontend`: legacy multi-role frontend. It has no current `frontend/package.json` and calls backend routes that are not mounted by the active FastAPI entrypoint.
- `video-gate`: independent video verification/generation tooling. It is not part of the ride-hailing MVP.
- Dormant backend routers such as `routes.admin`, `routes.admin_access`, `routes.rides`, `routes.users`, and `routes.test`.
- Dormant driver-app components and diagnostic apps that are not imported by `driver-app/src/App.jsx`.

Expert rule: only code reachable from the active entrypoints should be described as current product behavior.

## 3. Backend Architecture

The backend is a FastAPI application backed by SQLAlchemy models and Pydantic response schemas. Local development defaults to SQLite through `sqlite:///./halfapp_local.db`. `DATABASE_URL` can point to another SQLAlchemy-supported database.

Startup behavior in `backend/main.py`:

- Imports the SQLAlchemy base and engine from `backend/database.py`.
- Imports active ORM model modules before table creation.
- Imports `routes.notifications` because the notification model is defined in that route module.
- Calls `Base.metadata.create_all(bind=engine)`.
- Applies SQLite-only additive lifecycle column patches through `ensure_ride_lifecycle_columns(engine)`.
- Configures development CORS origins plus optional `CORS_ORIGINS`.
- Registers `/health`, `/auth`, `/drivers`, `/notifications`, and rider-side `/rides`.

Mounted route surface:

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

Non-mounted route modules may compile and may contain useful code, but they are not active API surface.

## 4. Data Model

`User` represents all account roles, but the active driver app permits only drivers to register and log in through `/auth`.

Important `User` fields:

- Identity: `id`, `email`, `name`, `password_hash`, `role`, `created_at`.
- Driver registration: `license_no`.
- Activation: `is_active`, stored as a string value rather than a Boolean.
- Driver profile: `phone`, `emergency_contact`, `vehicle_make`, `vehicle_model`, `vehicle_year`, `license_plate`, `insurance_policy`.
- Driver presence: `availability`, `last_latitude`, `last_longitude`, `last_location_at`.

`Ride` is the current lifecycle and earnings record. It is not yet a full marketplace audit record.

Important `Ride` fields:

- Identity and assignment: `id`, `customer_id`, `driver_id`, `customer_name`.
- Lifecycle: `status`, `created_at`, `accepted_at`, `arrived_pickup_at`, `started_at`, `completed_at`, `cancelled_at`, `lifecycle_reason`.
- Trip descriptors: `pickup_location`, `destination`, `pickup_latitude`, `pickup_longitude`, `dropoff_latitude`, `dropoff_longitude`.
- Earnings and trip metrics: `fare_amount`, `distance`, `duration`, `rating`.
- Miscellaneous: `notes`.

The API exposes `distance` as `distance_km` and `duration` as `duration_minutes` in contract-facing schemas.

Model limits:

- The visible models do not define database foreign key constraints between rides and users.
- `lifecycle_reason` is a single latest explanation, not an append-only audit history.
- `fare_amount` is stored on `Ride`; there is no payment ledger, payout ledger, fee allocation model, refund model, or tax model.
- Coordinates are stored, but the backend does not prove a geocoding or routing calculation.

## 5. Authentication And Authorization

Authentication uses bearer JWTs.

Current behavior:

- Passwords are hashed with bcrypt.
- JWTs are created by `backend/services/auth.py`.
- Tokens use HS256 and `SECRET_KEY`.
- `ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 60 minutes.
- `/auth/register` rejects non-driver roles in the active driver portal.
- `/auth/login` rejects inactive users and non-driver roles.
- `/auth/me` returns a public user dictionary and omits password hashes.
- Driver routes call a local `require_driver()` dependency.
- Rider ride create/cancel routes require a customer role.
- Notification list/read routes require an authenticated user; send/delete/ride-alert are admin-gated.

Security notes:

- The default development `SECRET_KEY` must not be used outside local development.
- There is no token revocation or refresh-token flow.
- Role checks are repeated at route level rather than centralized in a richer authorization policy layer.
- Client-side protected-route checks are convenience gates only; backend role checks are authoritative.

## 6. Ride Lifecycle

The implemented driver path is:

`requested -> accepted -> arrived_at_pickup -> in_progress -> completed`

Implemented terminal rider cancel path:

`requested|accepted -> cancelled`

Current driver decline behavior:

`accepted -> requested`

Driver decline is not a terminal rejection in this MVP. It releases the ride back to the open pool, clears the assigned driver, clears active-leg timestamps, and may store a reason in `lifecycle_reason`.

Implemented status meanings:

- `requested`: open pool ride, unassigned.
- `accepted`: claimed by a driver.
- `arrived_at_pickup`: driver marked arrival at pickup.
- `in_progress`: ride has started.
- `completed`: terminal completed ride.
- `cancelled`: terminal rider cancellation from `requested` or `accepted`.

Reserved but not emitted by active flows:

- `en_route_to_pickup`
- `waiting_for_rider`
- `declined`
- `expired`

The lifecycle contract intentionally forbids UI invention of ETA, route geometry, confidence score, hardcoded city map points, or unsupported earnings projections.

## 7. Dispatch Model

The active dispatch policy is an open board implemented by `OpenBoardDispatchPolicy`.

Current behavior:

- `GET /drivers/available-rides` returns rides where `status == "requested"` and `driver_id is null`.
- All eligible drivers can see the available pool.
- `POST /drivers/accept-ride/{ride_id}` uses a conditional SQL update requiring the ride to remain `requested` and unassigned.
- The first successful atomic claim wins.
- A competing claim receives HTTP 409 with a clear already-claimed detail.

This is honest for the MVP because it does not claim nearest-driver matching or hidden prioritization. It is still incomplete as a marketplace dispatch engine because it does not record:

- Which drivers were eligible.
- Which drivers saw a ride.
- Why a ride was ordered ahead of another.
- Why a driver was excluded.
- Which exact claim attempts lost a race.
- Which policy version made the decision.

The next expert-level dispatch increment should add visibility records, policy metadata, claim-attempt audit events, and deterministic ordering metadata.

## 8. Driver App Architecture

`driver-app` is a Vite React app using `HashRouter`. The active route tree is defined by `driver-app/src/App.jsx`.

Routes:

- `/#/login`: driver login and registration.
- `/#/`: main cockpit through `MapHome`.
- `/#/rides`: completed trips screen through `TripsList`.
- `/#/trips`: completed trips screen through `TripsList`.
- `/#/earnings`: earnings screen.
- `/#/notifications`: notifications screen.
- `/#/profile`: profile, statistics, notification, and earnings summary screen.

Core client-side modules:

- `useAuth.jsx`: token rehydration, login/register/logout, current-user loading.
- `api.js`: central API wrapper, token headers, backend calls, optional offline mock support, optional simulation support.
- `driverState.js`: local cockpit state names and persistence helpers.
- `rideModel.js`: contract-aware ride display mapping.
- `MapHome.jsx`: driver cockpit and lifecycle interaction surface.

The driver cockpit loads backend truth by fetching:

- available rides,
- assigned rides,
- earnings,
- profile/availability.

It advances active rides through backend lifecycle endpoints. It does not persist real active rides or completed earnings in localStorage.

Important UI truth boundaries:

- `driver_token` and `driver_role` are local auth cache helpers.
- `halfapp_driver_state` is a local UI state helper for online/offline cockpit state.
- `halfapp_driver_database` and `halfapp_mock_backend_rides` are mock-only localStorage keys when offline mock mode is explicitly enabled.
- `disable_guard` is a test-only route guard bypass.
- The "Hide for now" cockpit action is local only; it does not dismiss a ride on the backend.

## 9. Simulation And Mock Policy

The MVP supports two different non-production concepts:

Backend simulation:

- Enabled through `VITE_ENABLE_RIDE_SIMULATION=true`.
- Calls `POST /drivers/simulate-ride`.
- Creates a real backend `Ride` row in `requested` status.
- Marks the row with `lifecycle_reason="simulation"`.
- Sends it through the normal backend lifecycle after creation.

Offline mock fallback:

- Enabled only through `VITE_ALLOW_OFFLINE_MOCK=true`.
- Uses localStorage-backed mock drivers and mock rides.
- Exists for development and E2E fallback scenarios.
- Must never be presented as production behavior.

Expert rule: backend simulation is more truthful than local mock behavior because it exercises the real database and lifecycle transitions. Mock mode is useful for isolated UI testing but not for proving product behavior.

## 10. Earnings Model

Driver earnings are computed from completed rides assigned to the current driver.

Current behavior:

- `GET /drivers/earnings` sums completed ride `fare_amount`.
- It returns total, weekly, and today earnings.
- It returns completed ride counts over the same scopes.
- It returns recent completed rides.
- `complete-ride` computes and stores a fare using internal pricing constants and stored distance.

Limits:

- There is no separate financial ledger.
- There is no platform fee split.
- There is no payout settlement.
- There is no refund or adjustment model.
- There is no monthly chart endpoint.
- Distance and duration are stored values, not route-engine proof.

The UI must describe this as backend-computed completed-trip earnings, not as settled payout truth.

## 11. Notifications

Notifications are mounted under `/notifications`. The route module also defines the SQLAlchemy notification model, which is why `backend/main.py` imports it before table creation.

Current notification behavior supports authenticated listing and read state, plus admin-gated send/delete/driver ride alert helpers. This is not a complete messaging system. The driver-app notifications screen contains demo-only messaging concepts that should not be treated as live rider chat unless backend message models and endpoints are added.

## 12. Testing And Verification

Current test coverage is concentrated around the active backend lifecycle and active driver-app behavior.

Backend coverage includes:

- smoke tests,
- ride lifecycle transitions,
- open-board first-claim-wins behavior,
- rider cancellation,
- earnings contract,
- active route surface checks.

Driver-app coverage includes:

- authentication flow tests,
- navigation flow tests,
- smoke MVP tests,
- trust/mock-off contract tests,
- Playwright config for default E2E and trust lane E2E.

Useful verification commands:

```bash
python -m pytest backend/tests -q
```

```bash
cd driver-app
npm run build
```

```bash
cd driver-app
npm run test:e2e
```

```bash
cd driver-app
npm run test:e2e:trust
```

For lifecycle contract inspection:

```bash
cd backend
py -3.11 scripts/print_openapi_driver_rides.py
```

## 13. Deployment Readiness

The program is local-development-ready and useful for MVP behavior testing. It is not production-ready without several changes.

Production blockers:

- Replace the default `SECRET_KEY` and manage secrets through deployment infrastructure.
- Decide the production database and migration strategy. `create_all` plus SQLite additive patches are not enough for production schema management.
- Restrict CORS to real public origins.
- Define deployment-specific auth token lifetime, revocation, and refresh strategy.
- Add structured logging, request IDs, and operational observability.
- Add a real migration tool such as Alembic before persistent production data.
- Add database constraints and indexes for ownership, assignment, lifecycle queries, and notification queries.
- Validate transaction semantics under the selected production database.
- Remove or hard-disable local mock and guard-bypass affordances in production builds.

## 14. Current Risks

Product truth risks:

- Legacy surfaces can mislead reviewers if treated as active behavior.
- The active driver app is truthful about backend lifecycle, but still contains local UI state and mock-mode pathways that require clear labeling.
- `Hide for now` is local-only and does not create backend dismissal truth.
- Notifications include demo-only messaging concepts.

Backend risks:

- Development secret defaults are insecure for deployment.
- Lack of migrations will become dangerous as schemas evolve.
- Lack of foreign keys and ledger models limits auditability.
- Role enforcement is manual and duplicated.
- `is_active` is a string, not a Boolean.

Marketplace risks:

- Open board dispatch is simple and honest, but not yet auditable fairness.
- There is no durable driver visibility or dispatch decision record.
- There is no route calculation proof or ETA contract.
- There is no financial ledger or payout settlement model.

Frontend risks:

- Offline mock mode must remain explicit.
- Protected-route token presence is not security; it is only UI gating.
- Route names can be confusing: `/#/rides` currently renders completed trips, not the dormant `RideList` board.

## 15. Recommended Engineering Sequence

The efficient path is to stabilize the active product spine before reviving broader marketplace surfaces.

First:

- Keep `backend` and `driver-app` as the only active product path.
- Keep `docs/RIDE_LIFECYCLE_CONTRACT.md` aligned with OpenAPI and tests.
- Remove or clearly quarantine legacy/dormant UI files that are not part of the active app.
- Ensure production builds cannot silently enter offline mock mode.

Second:

- Introduce Alembic or another migration discipline.
- Add foreign keys and indexes appropriate to the active ride/user/notification queries.
- Centralize role authorization helpers.
- Replace development secrets and tighten CORS for deployment.

Third:

- Add a minimal append-only marketplace ledger.
- Record ride created, visibility, claim attempted, claim won, claim lost, decline/release, cancel, complete, and earnings calculation events.
- Add dispatch policy metadata and deterministic ordering metadata to available-ride responses.
- Convert local "Hide for now" into backend-backed visibility dismissal if it remains a product feature.

Fourth:

- Add route snapshot models before making ETA, distance, or routing claims.
- Add a pricing and payout ledger before making settlement or fare-split claims.
- Add real rider/admin surfaces only after the backend contracts and tests support them.

## 16. Expert Summary

HalfApp currently has a credible driver-only MVP spine: a FastAPI backend, a React driver app, backend-backed ride lifecycle transitions, backend-computed completed-trip earnings, customer-side ride create/cancel endpoints, and focused tests. The architecture is intentionally narrower than a full marketplace.

The strongest current property is truth discipline: the app is moving away from local fake ride state toward backend-owned lifecycle state. The main technical challenge is preserving that discipline as the program expands into dispatch, spatial routing, payments, auditability, rider experience, and admin operations.

The next major architecture step should not be a larger UI. It should be a durable transparency foundation: migrations, constraints, dispatch visibility records, claim audit events, route snapshots, and eventually a financial ledger. Those layers will let the product make stronger claims without turning the frontend into a source of invented marketplace truth.
