# Ride lifecycle — driver API contract (Stage 3)

This document is the **source of truth** before UI or client code may claim behavior. The FastAPI **OpenAPI** schema at `/openapi.json` must match this document for the listed paths.

## Status vocabulary

Allowed `ride.status` values (string). Unless noted, transitions are enforced server-side.

| Status | Implemented? | Set by | Meaning |
|--------|--------------|--------|---------|
| `requested` | yes | rider create | Open pool; `driver_id` is null. |
| `accepted` | yes | driver accept | Driver assigned (no separate map/ETA fields yet). |
| `driver_arrived` | yes | driver arrive-pickup | Driver marked arrival at pickup. |
| `in_progress` | yes | driver start-ride | Trip started (rider on board). |
| `completed` | yes | driver complete-ride | Terminal; trip finished. |
| `cancelled` | yes | rider cancel | Terminal; rider-initiated cancel from `requested` or `accepted`. |
| `en_route_to_pickup` | storage compatibility only | — | Legacy storage alias normalized to `accepted`; not emitted by the API. |
| `arrived_at_pickup` | storage compatibility only | — | Legacy storage alias normalized to `driver_arrived`; not emitted by the API. |
| `waiting_for_rider` | storage compatibility only | — | Legacy storage alias normalized to `driver_arrived`; not emitted by the API. |
| `declined` | no (future) | — | Reserved for a true rider-decline ledger (current driver decline returns to pool instead). |
| `expired` | no (future) | — | Reserved; would require a scheduled job — see "Not in contract yet". |

**Current driver-driven path:** `requested` → `accepted` → `driver_arrived` → `in_progress` → `completed`.

**Driver decline (driver backs out after accept):** `accepted` → `requested`, `driver_id` cleared, pool re-opened. Optional `reason` stored in `lifecycle_reason`. Does **not** emit terminal `declined` in MVP.

**Rider cancel:** `requested|accepted` → `cancelled` (terminal). `cancelled_at` set; `lifecycle_reason` set when rider supplied one; `driver_id` preserved when previously set so the driver's `my-rides` reflects the cancellation.

## Payload: `RideDriverView`

Returned by `GET /drivers/available-rides`, `GET /drivers/my-rides`, and embedded as `ride` on transition responses. All timestamps are **ISO 8601 strings or null** (UTC where set by server).

| Field | Type | Notes |
|-------|------|--------|
| `id` | integer | |
| `customer_name` | string | |
| `status` | string | One of the values above. |
| `pickup_location` | string \| null | Text label/address only; coordinates are separate explicit fields. |
| `destination` | string \| null | |
| `pickup_latitude` | number \| null | Backend-authoritative coordinate for map visualization. Required on new ride create/simulation payloads. |
| `pickup_longitude` | number \| null | Backend-authoritative coordinate for map visualization. Required on new ride create/simulation payloads. |
| `dropoff_latitude` | number \| null | Backend-authoritative coordinate for map visualization. Required on new ride create/simulation payloads. |
| `dropoff_longitude` | number \| null | Backend-authoritative coordinate for map visualization. Required on new ride create/simulation payloads. |
| `fare_amount` | number \| null | **Driver display dollars only** — when `pricing` exists, equals `driver_total_payout_cents / 100` (commission + tips). Not the customer total. Legacy rows may predate the ledger. |
| `driver_shareable_fare_cents` | integer \| null | Top-level mirror of `pricing.driver_shareable_fare_cents` when quoted. |
| `driver_total_payout_cents` | integer \| null | Top-level mirror of `pricing.driver_total_payout_cents`. |
| `customer_total_cents` | integer \| null | Top-level mirror of `pricing.customer_total_cents`. |
| `platform_revenue_cents` | integer \| null | Top-level mirror of `pricing.platform_revenue_cents`. |
| `pricing` | object \| null | Integer-cent ledger (`RidePricingView`). Locked when ride completes. |
| `route_provider` | string \| null | Map foundation id (v0.2: `leaflet_osm`). |
| `traffic_provider` | string \| null | Traffic provider id (v0.2: `disabled`). |
| `distance_km` | number \| null | Stored route distance km; not computed from a map engine here. |
| `duration_minutes` | integer \| null | Stored duration minutes. |
| `created_at` | string \| null | |
| `accepted_at` | string \| null | |
| `arrived_pickup_at` | string \| null | |
| `started_at` | string \| null | Trip start (in progress). |
| `completed_at` | string \| null | |
| `cancelled_at` | string \| null | |
| `lifecycle_reason` | string \| null | Last decline/cancel reason text when applicable. |
| `ordering_rank` | integer \| null | Deterministic rank for this driver when returned by `GET /drivers/available-rides`. |
| `ordering_score` | number \| null | Backend ordering score when available. |
| `why_this_rank` | object \| null | Backend-generated ranking explanation when available. |
| `ride_visibility_id` | integer \| null | Backend `ride_visibility` row proving this ride was exposed to this driver. |
| `visibility_correlation_id` | string \| null | Correlates visibility, hide, and later audit work. |
| `visibility_reason` | string \| null | Machine-readable reason the ride was visible, currently `requested_unassigned_open_board`. |
| `dispatch_policy_id` | string \| null | Active dispatch policy identifier. |
| `dispatch_policy_name` | string \| null | Active dispatch policy display name. |
| `ordered_by` | string[] \| null | Backend sort keys used by the active dispatch policy. |
| `policy_version` | string \| null | Dispatch policy version that generated the available-rides view. |
| `generated_at` | string \| null | Server timestamp for the available-rides view. |

**Explicitly not in contract yet:** ETAs, route geometry, confidence scores. Clients must **not** invent these from other fields. Pickup/dropoff coordinates are now explicit backend fields and are the only coordinates the driver cockpit may render.

## Endpoints

### `GET /drivers/available-rides`

- **Auth:** Bearer, driver.
- **Response:** `RideDriverView[]` — rides with `status == "requested"` and `driver_id` null, excluding rides actively hidden by this driver.
- **Dispatch metadata:** each returned ride includes `ride_visibility_id`, `visibility_correlation_id`, `visibility_reason`, `ordering_rank`, `ordering_score`, `why_this_rank`, `dispatch_policy_id`, `dispatch_policy_name`, `ordered_by`, `policy_version`, and `generated_at`; the backend records/updates one `ride_visibility` row per driver/ride visibility.
- **Current policy:** `ranked_open_board_v1`, ordered by `ordering_score_desc`, then `created_at_asc`, then `ride_id_asc`.

### `GET /drivers/presence`

- **Auth:** Bearer, driver.
- **Response:** backend-owned presence state for the current driver, including requested/effective state, last state change, last heartbeat, and stale/disconnected reason when derived from backend timestamps.

### `PUT /drivers/presence`

- **Auth:** Bearer, driver.
- **Body:** `{ "state": "available" | "offline" | "paused" | "stale" | "disconnected" }`.
- **Result:** persists requested driver presence on the backend. The cockpit may cache the response for display, but local UI state is not marketplace truth.

### `POST /drivers/heartbeat`

- **Auth:** Bearer, driver.
- **Result:** persists `heartbeat_at` for the driver. Backend reads derive `stale` and `disconnected` from heartbeat age.

### `GET /drivers/my-rides`

- **Auth:** Bearer, driver.
- **Response:** `RideDriverView[]` — rides where `driver_id` equals the current driver (any status).

### `POST /drivers/accept-ride/{ride_id}`

- **Auth:** Bearer, driver.
- **Body:** none.
- **Valid from:** `requested` (unassigned).
- **Result:** `status` → `accepted`, `driver_id` set, `accepted_at` set (claim timestamp; no separate `claimed_at` column).
- **Eligibility:** driver lane only; effective presence must be `available`; profile must not be `pending` / `rejected` / `suspended` / `busy`; account must be active; driver must not already hold an active ride (`accepted`, `driver_arrived`, `in_progress`). Failures return HTTP 403 with `{ "error": "forbidden", "message": "..." }` and do not mutate the ride.
- **Race handling:** first claim wins through the active dispatch policy's atomic update (`SELECT … FOR UPDATE` + conditional `UPDATE`). If another driver already claimed the ride, response is HTTP 409 with structured `detail`: `{ "detail": "Ride already claimed", "ride_id", "claim_result": "lost", "truth_status": "backend_conflict", "reason": "ride_already_claimed", "current_status", "assigned_driver_id" }`.
- **Conflict proof:** losing claim attempts are recorded in `ride_claim_attempts`, `events`, `marketplace_ledger`, and `marketplace_ledger_events`; `GET /drivers/rides/{ride_id}/transparency` returns a driver-scoped view plus `dispatch_proof` (winner/loser/reason/ledger).
- **Response:** `RideTransitionResponse` — `{ "message": string, "ride": RideDriverView }`.

### `GET /drivers/rides/{ride_id}/transparency`

- **Auth:** Bearer, driver.
- **Access:** current driver must have seen the ride, attempted to claim it, or be assigned to it.
- **Response:** driver-scoped `visibility`, `claim`, `dismissal`, `audit`, `truth_labels`, plus nested `dispatch_proof` with:
  - `driver_visibility`: visibility row IDs, rank, score, policy, ordering rule, visibility reason, hide timestamps, and correlation IDs.
  - `claim_attempts`: claim attempt IDs, driver IDs, outcomes, competing driver IDs, reasons, policy versions, and HTTP status mapping.
  - `claim_winner_driver_id` and `claim_lost_driver_ids`.
  - `claim_conflict`: latest 409 proof when a conflict occurred.
  - `ledger_entries`: immutable marketplace ledger rows for claim attempts, wins, losses, and releases.

### `POST /drivers/decline-ride/{ride_id}`

- **Auth:** Bearer, driver.
- **Body (optional):** JSON `{ "reason"?: string }` (max 500 chars). Clients may send `{}` when there is no reason.
- **Valid from:** `accepted`, assigned to this driver.
- **Result:** `status` → `requested`, `driver_id` null, timestamps for active leg cleared; `lifecycle_reason` set when `reason` provided.
- **Response:** `RideTransitionResponse`.

### `POST /drivers/dismiss-ride/{ride_id}`

- **Auth:** Bearer, driver.
- **Body:** none.
- **Valid from:** `requested`, unassigned.
- **Result:** legacy alias for backend hide/dismissal. Creates or updates the driver's `ride_visibility` hide fields; the ride remains `requested` for other eligible drivers.
- **Response:** `RideTransitionResponse`.

### `POST /drivers/rides/{ride_id}/hide`

- **Auth:** Bearer, driver.
- **Body:** optional `{ "reason": "..." }`.
- **Valid from:** `requested`, unassigned.
- **Result:** creates or updates a backend `ride_visibility` record with `status == "hidden_by_driver"`, `dismissed_at`, `expires_at`, optional reason, and correlation ID. The ride remains `requested` for other eligible drivers.
- **Response:** `RideTransitionResponse`.

### `POST /drivers/arrive-pickup/{ride_id}`

- **Auth:** Bearer, driver.
- **Body:** none.
- **Valid from:** `accepted`.
- **Result:** `status` → `driver_arrived`, `arrived_pickup_at` set.
- **Response:** `RideTransitionResponse`.

### `POST /drivers/start-ride/{ride_id}`

- **Auth:** Bearer, driver.
- **Body:** none.
- **Valid from:** `driver_arrived`.
- **Result:** `status` → `in_progress`, `started_at` set.
- **Response:** `RideTransitionResponse`.

### `POST /drivers/complete-ride/{ride_id}`

- **Auth:** Bearer, driver.
- **Body:** none.
- **Valid from:** `in_progress` only.
- **Result:** `status` → `completed`, `completed_at` set; `fare_amount` updated using server **stored** `distance_km` and existing pricing constants (documented as internal settlement, not a map-derived quote).
- **Response:** `CompleteRideResponse` — `{ "message": string, "fare_earned": number, "ride": RideDriverView }`.

### `GET /drivers/earnings`

- **Auth:** Bearer, driver.
- **Response:** `DriverEarningsResponse` — `{ "driver_id": number, "driver_name": string, "earnings_summary": EarningsSummary, "recent_rides": EarningsRecentRide[] }`.

`EarningsSummary` fields (all numeric, server-computed from completed rides only):

| Field | Type | Notes |
|-------|------|-------|
| `total_earnings` | number | Sum of `fare_amount` on completed rides. |
| `weekly_earnings` | number | Sum over last 7 days (by `completed_at`). |
| `today_earnings` | number | Sum since UTC midnight today. |
| `total_rides_completed` | integer | |
| `weekly_rides` | integer | |
| `today_rides` | integer | |

`EarningsRecentRide` fields (capped to last 10 completed):

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | |
| `customer_name` | string | |
| `fare_amount` | number \| null | |
| `distance_km` | number \| null | Renamed from `distance` for contract consistency. |
| `completed_at` | string \| null | ISO 8601. |
| `rating` | integer \| null | When stored on the ride. |

**Frontend must not invent** monthly trend numbers, growth %, projections, or any field not on these models. The earnings screen shows an explicit "Not available yet" message for the monthly chart.

## Rider endpoints

Rider lifecycle is the minimum needed to honestly drive the `cancelled` state. There is no rider-side accept/arrive/start — those are driver-only.

### `POST /rides/`

- **Auth:** Bearer, customer.
- **Body:** `RiderRideCreate` — `{ "customer_name"?: string, "pickup_location"?: string, "destination"?: string, "pickup_latitude": number, "pickup_longitude": number, "dropoff_latitude": number, "dropoff_longitude": number, "distance_km"?: number, "duration_minutes"?: integer }`. Coordinate fields are required; `customer_name` falls back to the customer's profile name.
- **Result:** new ride, `status="requested"`, `customer_id=current user`, `driver_id=null`.
- **Response:** `RiderRideResponse` — `{ "message": string, "ride": RideDriverView }`.

### `POST /rides/{ride_id}/cancel`

- **Auth:** Bearer, customer. **Must own** the ride (`customer_id` matches).
- **Body (optional):** `RiderCancelBody` — `{ "reason"?: string }` (max 500 chars). `{}` and missing body are both accepted.
- **Valid from:** `requested` or `accepted` **only**. Any other state → HTTP 400.
- **Other customer:** HTTP 403.
- **Result:** `status` → `cancelled`, `cancelled_at` set, `lifecycle_reason` set when provided. `driver_id` is **preserved** when set so the driver's `my-rides` reflects the cancel.
- **Response:** `RiderRideResponse`.

## Driver-side handling of cancelled rides

- `GET /drivers/available-rides` filters `status == "requested"` — cancelled rides do **not** appear.
- `GET /drivers/my-rides` includes cancelled rides previously accepted by the driver (so the driver sees why the trip ended).
- All driver transitions (`accept`, `decline`, `arrive-pickup`, `start-ride`, `complete-ride`) reject `cancelled` rides with HTTP 400 — they are terminal.
- Frontend `RideList.jsx` does **not** show action buttons on cancelled rides (status is not in `ACTIVE_TRIP_STATUSES`).

## Audit records

- `driver_presence` records backend-owned requested/effective presence state, state-change time, heartbeat time, and stale/disconnected reason.
- `ride_visibility` records which driver saw which requested ride, first/last seen time, dismissal time, hide expiry, reason, ordering rank, policy version, and correlation ID.
- `ride_claim_attempts` records accept attempts with `won`, `conflict`, `not_found`, or `unavailable` outcomes plus competing driver when known.
- `events` records key ride, claim, presence, and earning actions (`ride.created`, `ride.accepted`, `ride.declined`, `ride.arrived_pickup`, `ride.started`, `ride.completed`, `ride.cancelled`, `ride.hidden`, `presence.changed`, `presence.heartbeat`, `claim.attempted`, `claim.won`, `claim.lost`, `earning.calculated`).
- `marketplace_ledger_events` is the append-only event stream for consequential marketplace facts. It records ride creation, visibility exposure, hide actions, claim attempts/wins/losses/releases, cancellations, completions, presence changes/heartbeats, and earning calculations with hash-chain links, correlation IDs, and idempotency keys where practical.

## Not in contract yet

These remain documented but unimplemented. Adding them later requires a model/contract change first, never UI invention.

- **`en_route_to_pickup`** — legacy storage alias only. Public API responses normalize it to `accepted`.
- **`arrived_at_pickup`** — legacy storage alias only. Public API responses normalize it to `driver_arrived`.
- **`waiting_for_rider`** — legacy storage alias only. Public API responses normalize it to `driver_arrived`.
- **`expired`** — would mark stale `requested` rides nobody accepts. **Out of scope for Stage 3 because the project has no scheduled job runtime** (no Celery, APScheduler, or similar). Implementing this requires (a) a scheduler, (b) an explicit TTL on `Ride`, and (c) a defined notification path back to the rider. None of these exist yet, so the status string remains reserved without an emitter.
- **`declined` (terminal)** — would be a true ledger row for a driver-rejected ride (vs current driver "decline" which returns the ride to the pool). No product decision yet on whether declines should be terminal or rebroadcast.
- **Geocoding / ETA / route geometry / confidence scores / map tiles.** Not on `RideDriverView`, not on rider create body, not derived in frontend. Ride pickup/dropoff coordinates are explicit backend payload and response fields; the backend does not geocode text addresses.

## Frontend alignment

`driver-app/src/utils/rideModel.js` maps **only** `RideDriverView` fields (plus formatting). Legacy keys (`fare`, `passenger_name`, `estimated_time`, `distance` without `_km`, etc.) are **not** part of the contract and must not drive UI labels except where offline mock is explicitly documented as non-contract.

`driver-app/src/components/MapHome.jsx` may render only backend-provided `pickup_latitude`, `pickup_longitude`, `dropoff_latitude`, and `dropoff_longitude`. It must not substitute hardcoded city coordinates, fake driver locations, live ETA, or route geometry.

`driver-app/src/components/Earnings.jsx` consumes only the documented `DriverEarningsResponse` fields (`earnings_summary.total_earnings | weekly_earnings | today_earnings`, plus `recent_rides[].id | customer_name | fare_amount | completed_at`). The monthly trend tile is intentionally a "Not available yet" placeholder until a backend chart endpoint exists.

## Proof commands

List registered FastAPI routes (filter driver ride paths):

```bash
cd backend
py -3.11 -c "from main import app; print(sorted({getattr(r,'path','') for r in app.routes if getattr(r,'path','').startswith('/drivers')}))" 
```

Inspect OpenAPI path keys and `RideDriverView` field list:

```bash
cd backend
py -3.11 scripts/print_openapi_driver_rides.py
```

Full OpenAPI JSON (includes all paths/schemas):

```bash
cd backend
py -3.11 -c "import json; from main import app; print(json.dumps(app.openapi(), indent=2))"
```

Lifecycle tests:

```bash
cd backend
py -3.11 -m pytest tests/test_ride_lifecycle.py -q
```

Optional: write a trimmed snippet file (gitignored by default):

```bash
cd backend
set WRITE_OPENAPI_SNIPPET=1
py -3.11 scripts/print_openapi_driver_rides.py
```
