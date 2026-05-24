# HalfApp Expert Summary Extraction Report

Date: 2026-05-22

## Implement Now

| Concept | Why it matters | Files likely touched | Backend truth needed | Tests required |
|---|---|---|---|---|
| Full-screen map-first driver cockpit | Removes fake dashboard feel; map is primary canvas with floating controls | `driver-app/src/components/MapHome.jsx`, `MapView.jsx`, `globals.css` | None for map shell; ride pins use backend coords when ride active | Playwright: `map-home`, `map-view`, `experimental-map-panel` visible |
| Location permission flow (honest states) | Prevents device GPS from becoming marketplace truth | `useDriverGeolocation.js`, `locationTruth.js`, `MapHome.jsx` | None — device location is map-only | Unit: state resolution; E2E: denied shows honest copy |
| Dev fallback location (dev only, labeled) | Lets developers work without GPS without pretending production GPS | `useDriverGeolocation.js`, `experimentalMapMarkers.js`, `TruthLabel.jsx` | None | Unit + E2E: `DEV FALLBACK LOCATION`, `Not real driver GPS` |
| Backend-owned driver presence | Online/offline survives refresh | `backend/routes/drivers.py`, `services/presence.py`, `MapHome.jsx`, `api.js` | `GET/PUT /drivers/presence`, `POST /drivers/heartbeat` | `test_driver_marketplace_truth_slice.py`, trust E2E reload |
| Backend-backed ride hide/dismissal | Hide is durable marketplace fact | `backend/routes/drivers.py`, `services/metrics.py`, `MapHome.jsx` | `POST /drivers/rides/{id}/hide`, `ride_visibility` rows | Backend hide/reload tests; E2E hide notice |
| Ride visibility records | Explains why ride appeared to driver | `backend/services/metrics.py`, `models/metrics.py` | Written on `GET /drivers/available-rides` | `test_available_rides_records_visibility_metadata` |
| Truth-label system | Prevents fake ETA/route/dispatch claims | `TruthLabel.jsx`, `MapView.jsx`, `MapHome.jsx` | Fare/dispatch from API fields only | E2E: disclaimer + no invented ETA copy |
| Refresh/reload proof | Marketplace truth not in localStorage | `MapHome.jsx`, trust tests | Presence + hide persisted in DB | `test_simulated_reload_preserves_presence_and_hide_state` |

## Implement Soon

| Concept | Why later | Dependency |
|---|---|---|
| Dispatch policy metadata enrichment | Partially present (`policy_version`, ordering); needs fuller round records | Visibility + claim audit stable |
| Claim attempted / won / lost UI | Backend records exist; driver audit views not built | Transparency endpoint UX |
| Deterministic ride ordering UI | Backend orders; richer “why excluded” needs dispatch rounds | Dispatch round model |
| Ride lifecycle transition hardening | Core paths work; more 409/edge cases | Ledger + conflict tests |
| Route snapshot model | No routing provider yet | Routing service interface |
| Earnings ledger foundation (cents) | Summaries exist; not transactional ledger | Alembic + financial schema |
| `busy` presence state | Active ride could drive busy; not in `PRESENCE_STATES` yet | Lifecycle + presence coupling |
| Alembic migrations | `create_all` still used in dev | Production DB choice |

## Design Only

| Concept | Future role | Not building now because |
|---|---|---|
| Rider app | Demand-side marketplace | Out of active product boundary |
| Admin dashboard | Operations / disputes | No admin auth spine |
| Payment provider integration | Charges and settlements | No money movement |
| Payouts / taxes | Driver settlements | No financial ledger |
| Support / dispute system | Post-trip resolution | No case model |
| Full driver compliance | Docs / background checks | No compliance API |
| Push notifications | Real-time offers | No gateway |
| Advanced dispatch / heat zones | Geo eligibility | No routing/geo service |
| Promotions / quests / airport queues / scheduled rides | Growth features | MVP lifecycle only |

## Reject / Defer

| Concept | Reason |
|---|---|
| Frontend-generated ETA truth | Violates backend-truth doctrine |
| Frontend-calculated fare truth | Earnings must come from backend records |
| Fake nearest-driver logic | Open-board is honest; don’t fake matching |
| Fake earnings / routes as production | Labels must show experimental/unavailable |
| localStorage online/offline marketplace state | Auth token only; presence from API |
| Local-only hidden rides | Must use `POST /drivers/rides/{id}/hide` |
| Legacy `frontend` revival | Inactive surface |
| Production mock mode | Blocked by `assert-prod-truth.mjs` |

## Recommended First Coding Slice

1. Harden map-first cockpit layout (full viewport map, floating header/toggle/sheet/nav).
2. Complete geolocation state machine + dev fallback labeling.
3. Add reusable `TruthLabel` component wired into map cockpit.
4. Align Playwright smoke/trust tests with current cockpit copy.
5. Add Node unit tests for location state helpers.
6. Run `pytest` (backend) and `npm run build` + Playwright trust/smoke as available.
