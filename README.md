# HalfApp Active Product Spine

Status: Driver-Only MVP first. **Not** a complete mobility or city-scale ride-hailing OS.

Stage 0 truth boundary: `docs/PRODUCT_BOUNDARY_STAGE0.md` and `docs/CURRENT_TRUTH.md`.

This repository currently contains multiple historical surfaces, but only two
directories are active HalfApp ride-hailing product surface:

- `backend`
- `driver-app`

Everything else is either supporting documentation, isolated tooling, generated
artifact, dependency cache, or legacy/archive candidate.

## Active Surfaces

### `backend`

FastAPI service for the driver-only MVP. The active route surface is exactly
what `backend/main.py` registers:

- `/health`
- `/auth/*`
- `/drivers/*`
- `/rides/*` from `routes/rider_rides.py`
- `/notifications/*`

Dormant backend route modules are not product surface unless `backend/main.py`
explicitly includes them and tests are added.

### `driver-app`

React/Vite driver app. This is the only active frontend for the ride-hailing MVP.
The cockpit, trips, and earnings screens must treat the backend as the source of
truth for ride lifecycle and completed-trip earnings.

Local browser storage may hold auth tokens and UI preferences. It must not be
presented as real ride or earnings truth.

## Inactive, Legacy, Or Isolated Surfaces

### `frontend`

Legacy/inactive. See `frontend/README.md`. Not mounted on the active API; must not
be used as evidence of rider/admin production readiness. Do not revive without an
explicit separate migration order.

### `video-gate`

Separate video verification/generation tooling. It is unrelated to the active
ride-hailing MVP path and must not be mixed into driver/backend stabilization
work.

### Dormant Backend Routers

These modules may exist in the tree but are inactive unless registered by
`backend/main.py`:

- `routes.admin`
- `routes.admin_access`
- `routes.rides`
- `routes.users`
- `routes.test`

Admin routes must not be enabled without auth and role tests.

## Simulation Policy

The driver-only MVP may create backend synthetic rides for development and
testing. Those rides must still enter the normal backend lifecycle:

`requested -> accepted -> arrived_at_pickup -> in_progress -> completed`

Simulation is explicit and controlled by frontend build-time configuration. It
is not a replacement for real rider dispatch, payments, geospatial matching, or
admin operations.

## Out Of Scope For This Spine

- Full rider-driver-admin marketplace expansion.
- Real payments.
- Complex nearest-driver/geospatial dispatch.
- Double-entry accounting ledger.
- Reviving the legacy `frontend`.
- Integrating `video-gate` into the ride-hailing MVP.
