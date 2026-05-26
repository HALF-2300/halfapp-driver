# HalfApp Active Product Spine

Status: **Driver-side execution system with supporting APIs.** Not a complete Lyft-like marketplace.

Authoritative classification: `docs/SYSTEM_TRUTH.md`  
Stage 0 truth boundary: `docs/PRODUCT_BOUNDARY_STAGE0.md` and `docs/CURRENT_TRUTH.md`.  
**Two-sided build order:** `docs/HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md`

This repository contains multiple historical surfaces that can look like a full marketplace. They are not. The active product spine:

- `backend`
- `driver-app`
- `rider-app` (Phase 1 rider loop)

Everything else is supporting documentation, demo tooling, generated artifact, dependency cache, or legacy/archive.

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

React/Vite driver app. Supply-side cockpit for the ride loop.

### `rider-app`

React/Vite rider app (Phase 1). Demand-side: request ride, track status, cancel. See `rider-app/README.md`.

Local browser storage may hold auth tokens and UI preferences. It must not be
presented as real ride or earnings truth.

## Inactive, Legacy, Or Isolated Surfaces

### `frontend`

**ARCHIVE · NOT WIRED · NOT PRODUCTION.** See `frontend/README.md`. Legacy multi-role UI; not mounted on the active API. Must not be used as evidence of rider or admin production readiness.

### `rider-stub`

**DEMO ONLY.** See `rider-stub/README.md`. Single-page API demo for staging smoke tests. Not a rider product.

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

To reach Lyft-like functionality, these must be built as **products** (not API stubs or ledger code alone):

- Rider app (demand-side UI)
- Payments UX (checkout, capture, payout, disputes)
- Ops/Admin console (control plane)

Also out of scope until explicit orders:

- Treating this repo as a two-sided marketplace today
- Real nearest-driver/geospatial dispatch
- Reviving the legacy `frontend/` as production surface
- Integrating `video-gate` into the ride-hailing MVP
