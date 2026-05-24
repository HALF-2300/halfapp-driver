# HalfApp Review Checklist

Date: 2026-05-18

Status: pull request review checklist for the active HalfApp MVP.

Use this checklist when a PR changes `backend`, `driver-app`, lifecycle contracts, dispatch behavior, auth, mock/simulation behavior, spatial claims, or earnings.

## Required Truth Boundary

Before approving a PR, confirm:

- The changed behavior is reachable from `backend/main.py` or `driver-app/src/App.jsx`.
- Any lifecycle or payload claim is reflected in `docs/RIDE_LIFECYCLE_CONTRACT.md`.
- OpenAPI exposes the claimed endpoint, request body, response body, and status code.
- Tests cover the changed behavior.
- UI copy does not present mock, simulation, local-only, or dormant behavior as production truth.
- Dormant files are not treated as active product behavior unless the PR registers, routes, tests, and documents them.
- Measurable system behavior is captured in metrics, visibility records, claim attempts, events, or an explicit "not measured yet" contract note.

## If Lifecycle Changed

Required checks:

- Update `docs/RIDE_LIFECYCLE_CONTRACT.md`.
- Update backend schemas if payloads changed.
- Update OpenAPI expectations or snapshots if present.
- Add or update lifecycle tests.
- Confirm the driver app maps only contract fields.

Commands:

```bash
cd backend
py -3.11 scripts/print_openapi_driver_rides.py
py -3.11 -m pytest tests/test_ride_lifecycle.py -q
```

Also run the full backend suite before merge:

```bash
python -m pytest backend/tests -q
```

Reviewer question: can the changed lifecycle be proven from active endpoints, OpenAPI, and tests?

## If Metrics Or Observability Changed

Required checks:

- Any new metric has a stable name and clear unit.
- Any metric tied to a ride includes `ride_id` when available.
- Any metric tied to a driver includes `driver_id` when available.
- Available-ride behavior continues to write `ride_visibility` records.
- Accept attempts continue to write `ride_claim_attempts` rows for wins, conflicts, and unavailable/not-found attempts.
- System-health and driver-performance responses do not claim optimization or ranking behavior.

Commands:

```bash
python -m pytest backend/tests/test_metrics_observability.py -q
python -m pytest backend/tests/test_active_route_surface.py -q
```

Reviewer question: does this change introduce or affect measurable system behavior, and is that behavior captured in metrics or events?

## If Dispatch Changed

Required checks:

- `GET /drivers/available-rides` still returns only eligible backend rides.
- `POST /drivers/accept-ride/{ride_id}` still uses first-claim-wins behavior and returns HTTP 409 for conflicts.
- Any ordering, fairness, ranking, eligibility, visibility, or exclusion claim is backed by database records or explicitly marked future work.
- Claim conflicts are tested.

Commands:

```bash
python -m pytest backend/tests/test_ride_lifecycle.py -q
python -m pytest backend/tests/test_active_route_surface.py -q
```

Reviewer question: can the database answer who saw what, who tried to claim, who won or lost, and which dispatch policy applied? If not, the PR must not claim transparent dispatch.

## If Auth Or Role Enforcement Changed

Required checks:

- Driver-only registration/login remains intentional for the active `driver-app`.
- Backend role checks remain authoritative.
- Client-side route protection is not treated as security.
- `/auth/me` does not expose password hashes or secret material.
- Secret defaults are not weakened.

Commands:

```bash
python -m pytest backend/tests/test_smoke.py -q
cd driver-app
npm run test:e2e
```

Reviewer question: can a non-driver reach driver-only behavior through the active backend or driver app?

## If Mock, Simulation, Or Guard Behavior Changed

Required checks:

- `VITE_ALLOW_OFFLINE_MOCK=true` remains explicit and non-production.
- `VITE_ENABLE_RIDE_SIMULATION=true` creates backend rows when used as simulation.
- `disable_guard` or any route guard bypass remains test-only.
- UI visibly distinguishes mock-only behavior from backend truth.
- Trust-lane tests run with mock fallback disabled.

Commands:

```bash
cd driver-app
npm run build
npm run test:e2e:trust
```

Reviewer question: can production or trust-lane behavior accidentally pass through localStorage mock data or guard bypasses?

## If Spatial, ETA, Map, Or Route Claims Changed

Required checks:

- UI renders only backend-provided pickup/dropoff coordinates.
- ETA, route geometry, traffic, confidence, or nearest-driver copy is absent unless backed by a backend route snapshot or equivalent contract.
- Distance and duration remain described as stored backend values unless a route engine snapshot exists.
- Tests cover missing spatial data without fallback invention.

Commands:

```bash
cd backend
py -3.11 scripts/print_openapi_driver_rides.py
cd ../driver-app
npm run test:e2e:trust
```

Reviewer question: is every spatial claim traceable to an API field or database row?

## If Earnings Or Finance Changed

Required checks:

- `GET /drivers/earnings` remains a backend-computed completed-trip earnings summary.
- UI does not claim settled payouts, platform take, taxes, refunds, or adjustments without a ledger.
- Completion fare calculation changes are tested.
- Response fields still match `DriverEarningsResponse`.

Commands:

```bash
python -m pytest backend/tests/test_earnings_contract.py -q
cd driver-app
npm run test:e2e:trust
```

Reviewer question: does the PR distinguish computed earnings from settled payout truth?

## If Active Routes Changed

Required checks:

- `backend/main.py` intentionally mounts or unmounts the route.
- `docs/CURRENT_TRUTH.md` is updated when active surface changes.
- OpenAPI output shows the new route surface.
- Dormant routers are not mounted without auth, tests, and contract updates.

Commands:

```bash
python -m pytest backend/tests/test_active_route_surface.py -q
cd backend
py -3.11 -c "from main import app; print(sorted({getattr(r,'path','') for r in app.routes}))"
```

Reviewer question: is this route part of the active product spine, or is it legacy code being revived accidentally?

## Standard Merge Gate

Run these before merging a PR that touches active HalfApp behavior:

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

```bash
cd backend
py -3.11 scripts/print_openapi_driver_rides.py
```

## Review Signoff

Use this signoff language in PR review:

- Active entrypoint checked: yes/no.
- Contract updated when needed: yes/no/not applicable.
- OpenAPI checked: yes/no.
- Backend tests run: yes/no.
- Driver-app build/E2E run: yes/no.
- Mock/simulation behavior labeled: yes/no/not applicable.
- No unsupported ETA/route/finance/dispatch claims: yes/no.

