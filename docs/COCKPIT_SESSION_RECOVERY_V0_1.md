# COCKPIT_SESSION_RECOVERY_V0_1

Status: GO (v0.1)

## What shipped

- New backend endpoint: `GET /drivers/me/active-ride`.
  - Returns the driver's current active ride in status:
    - `accepted`
    - `driver_arrived`
    - `in_progress`
  - Includes full `RideDriverView` payload (route metadata, pricing quote, rider/customer fields, lifecycle data).
  - Includes `lifecycle_stage` and navigation bundle.
- Cockpit startup (`MapHome`) now calls active-ride recovery during initial load and hydrates state before normal refresh.
- Browser hard refresh during active trip restores cockpit panel for the correct lifecycle stage.
- `CockpitNetworkBanner` now supports explicit retry action and online-recovery retry callback.

## Recovery behavior

On load:
1. fetch `/drivers/me/status`
2. fetch `/drivers/profile`
3. fetch `/drivers/me/active-ride`
4. if active ride exists, hydrate `activeRide`, driver state, and resume notice
5. run normal truth refresh to sync remaining fields

## Acceptance proof path

1. Driver claims a ride.
2. Hard refresh at:
   - accepted → sees `sheet-accepted_to_pickup`
   - driver_arrived → sees `sheet-arrived_pickup`
   - in_progress → sees `sheet-in_progress`
3. No manual state repair required.

## Test coverage

- Playwright: `driver-app/tests/sse-session-recovery.spec.ts`
  - test A: two windows receive ride pool update quickly (SSE path)
  - test B: hard-refresh stage recovery through active lifecycle phases
