# COCKPIT_SESSION_RECOVERY_V0_1

Status: GO (v0.1)

## What shipped

- `GET /drivers/me/active-ride` — source of truth for cockpit session recovery.
  - Active statuses: `accepted`, `driver_arrived`, `in_progress`
  - Full `RideDriverView` (pricing, route metadata, dispatch fields)
  - `lifecycle` block: `current`, `available_actions`, `history` (last 10 events)
  - `route` truth block (provider, snapshots summary)
  - `customer` block (`name`, `phone_masked` when present)
  - `navigation` bundle for in-trip panels
- Structured lifecycle ledger payloads on accept / arrive / start / complete / rider cancel (`from_state`, `to_state`, `reason`, `actor`, `server_timestamp`)
- `useActiveRide` hook — `undefined` loading, `null` idle, object active
- `CockpitSkeleton` — no empty-cockpit flash while active-ride loads
- `MapHome` hydrates from active-ride before marketplace refresh; `recoverActiveRideOnOnline` on network return (including customer-cancel notice)
- `data-cockpit-state` + `data-ride-id` on active-trip sheets for tests and diagnostics

## Recovery behavior

On load:

1. `GET /drivers/me/status`
2. `GET /drivers/profile` (approval)
3. `GET /drivers/me/active-ride` (skeleton until resolved)
4. If active ride exists → hydrate `activeRide`, driver state, resume banner
5. Normal truth refresh (`my-rides`, pool, earnings)

On `navigator.online` / network retry:

1. Refetch `/drivers/me/active-ride`
2. Silently advance UI if server lifecycle moved ahead while offline
3. If ride gone while driver was on-trip → show: *This ride was cancelled by the customer while you were offline.*

## Acceptance proof

| Scenario | Expected UI |
|----------|-------------|
| Refresh @ accepted | `sheet-accepted_to_pickup`, `data-cockpit-state="accepted"`, same `data-ride-id` |
| Refresh @ driver_arrived | `sheet-arrived_pickup`, `data-cockpit-state="driver_arrived"` |
| Refresh @ in_progress | `sheet-in_progress`, `data-cockpit-state="in_progress"` |
| Slow active-ride | `cockpit-skeleton` then correct sheet |
| Customer cancel while offline | `backend-hide-notice` with cancel copy |

## Tests

### Backend

```text
cd backend
python -m pytest tests/test_active_ride_recovery.py -q
# 2 passed
```

### Playwright (ride-flow stack, ports 3024 + 8011)

```text
cd driver-app
npm run test:e2e:ride-flow -- tests/session-recovery.spec.ts
```

Also covered by `tests/sse-session-recovery.spec.ts` (hard-refresh through all three active stages).

## Files

| Area | Path |
|------|------|
| API | `backend/routes/drivers.py` |
| Recovery builder | `backend/services/active_ride_recovery.py` |
| Lifecycle payloads | `backend/services/ride_lifecycle_events.py`, `backend/services/lifecycle.py` |
| Hook | `driver-app/src/hooks/useActiveRide.js` |
| Shell | `driver-app/src/components/MapHome.jsx`, `cockpit/CockpitSkeleton.jsx` |
| E2E | `driver-app/tests/session-recovery.spec.ts` |
