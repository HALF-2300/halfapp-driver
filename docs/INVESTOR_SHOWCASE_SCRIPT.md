# HalfApp Investor Showcase Script

## Opening Pitch

HalfApp is starting with the driver-side marketplace core.

The current proof is important because the marketplace facts are backend-owned, not browser-owned. Driver availability, heartbeat presence, ride visibility, ride hiding, and ride lifecycle changes survive refresh and can be audited from backend state.

This is the base for dispatch, fleet operations, delivery, and local transportation workflows. It is early, but it is real.

## 3-Minute Walkthrough

1. Open the active driver app and sign in as a driver.
2. Point out the internal label: `Investor Showcase - Driver Marketplace Core`.
3. Show that the driver starts offline and that availability is read from backend presence.
4. Tap `Go online in backend` and explain that availability plus heartbeat are backend-owned.
5. Refresh marketplace truth and show requested rides coming from the backend pool.
6. Open a ride card and point to stored pickup, dropoff, fare, distance, duration, policy, and lifecycle state.
7. Hide a requested ride for this driver, refresh, and show that the dismissal persists for the driver instead of living in frontend localStorage.
8. Accept a backend ride and walk through the canonical lifecycle: accepted, arrived at pickup, in progress, completed.
9. Open trips/earnings after completion to show backend-recorded completed ride and fare summary.
10. Close by stating the boundary: this is driver marketplace core readiness, not production launch.

## What The Demo Proves

- Driver status is controlled by backend presence, not by a browser-only flag.
- Heartbeat/presence exists, so stale or disconnected drivers can be detected by backend logic.
- Available rides come from backend marketplace truth.
- Ride hiding is recorded server-side for the driver and survives refresh.
- Ride transitions follow the canonical lifecycle instead of arbitrary frontend state.
- The current MVP is enough to demonstrate driver-marketplace-core readiness.

## What The Demo Does Not Claim

- No AI dispatch claim.
- No nearest-driver claim.
- No live payment processing claim.
- No live ETA, distance, routing, or navigation claim.
- No production-readiness claim.
- No fully automated marketplace claim.
- No admin operator console claim.

## Revenue Path

HalfApp can grow from this driver marketplace core into operational revenue paths:

- Dispatch and delivery operations for local fleets.
- Driver availability and ride lifecycle tools for small operators.
- Per-ride marketplace ledger and audit products.
- Operator dashboards for dispatch visibility and quality control.
- Future payment ledger integration after backend auditability is hardened.

## Next Milestones

- Clean up Alembic drift before schema-heavy audit work.
- Add a stronger dispatch audit layer for ride visibility, hide, claim, and lifecycle decisions.
- Build an operator/admin console that reads the same backend marketplace truth.
- Add production-grade secrets, deployment configuration, monitoring, and data retention rules.
- Add payment ledger design without implying live payments before implementation.
- Add route/ETA engine only when there is a real routing source.

## Known Blockers

- Alembic drift must be resolved before future schema-heavy work.
- Production `SECRET_KEY` still needs replacement.
- Production hardening is pending.
- Full dispatch audit ledger is pending.
- Payments are not included.
- Route ETA and nearest-driver ranking are not included.

## Demo Data Setup

Preferred setup is backend-owned data:

1. Start the backend with the current schema.
2. Run `python backend/scripts/seed_investor_demo.py` from the repository root if the local database is ready.
3. Sign in with the seeded driver account.
4. Use the cockpit to go online, refresh marketplace truth, hide a ride, accept a ride, and complete the lifecycle.

Seeded demo credentials:

- Driver email: `investor.driver@halfapp.demo`
- Driver password: `InvestorDemo123!`

If the local schema is not ready, do not fake rides in the frontend. Use the existing backend `/drivers/simulate-ride` control only when explicitly enabled for development, because it stores the ride in the backend lifecycle.

