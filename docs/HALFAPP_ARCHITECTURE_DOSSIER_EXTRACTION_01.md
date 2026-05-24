# HalfApp Architecture Dossier Extraction (01)

Date: 2026-05-22  
Scope: Apply useful concepts from the deep architecture dossier to the **current** `backend` + `driver-app` slice without hyperscale overbuild.

## Concepts extracted from dossier

| Concept | Intent |
|---------|--------|
| Backend-truth doctrine | Marketplace facts come from durable backend APIs, not client inference |
| Passive presentation layer | UI renders backend state; local state is UI-only (loading, drawers, map viewport) |
| Trip lifecycle FSM | Deterministic server-side transitions; client maps labels/actions to backend `ride.status` |
| Dispatch concurrency | First-claim-wins; losers get HTTP 409; no double-booking |
| Immutable marketplace audit | Append-only events for visibility, hide, claims, presence, completion |
| Financial ledger (future) | Integer cents, double-entry later — not MVP payments |
| Location integrity (honest UI) | Device GPS is map-only; dev fallback clearly labeled |
| Agent Brief Generator | Dev-only prompt scaffold for planning slices — no execution |

## Implemented now

### Driver app (`driver-app`)

- **Map-first cockpit shell** — `DriverMapShell`, full-screen `MapView`, floating header, compact bottom sheet, floating `BottomNavDock`.
- **Backend-truth loading** — `MapHome.jsx` loads presence, available/my rides, and earnings from APIs; refresh does not reset presence truth.
- **Compact availability card** — `DriverAvailabilityCard` with Sync control; no giant dashboard slab.
- **Diagnostics drawer** — noisy proof labels, sync, dev simulation, Agent Brief Generator (dev only).
- **Dev simulation** — `DevActionDock` + diagnostics actions labeled `DEV · Create ride`; not a primary CTA.
- **Location honesty** — `useDriverGeolocation`, `locationTruth.js`, `DriverLocationChip` with device/fallback labels.
- **Claim conflict UX** — accept handles HTTP 409 and refreshes backend pool.

### Backend (`backend`)

- **Lifecycle FSM** — documented in `docs/RIDE_LIFECYCLE_CONTRACT.md`; enforced in ride routes.
- **First-claim-wins** — atomic accept with 409 for losers; tests in `test_ride_lifecycle.py`, `test_dispatch_auditability.py`.
- **Marketplace audit** — `Event`, `MarketplaceLedgerEntry`, claim visibility/hide events (append-only spirit).

### Tests & docs

- Playwright: `tests/cockpit-identity.spec.ts`, `tests/map-cockpit-truth.spec.ts`
- Unit: `tests/unit/locationTruth.test.js`
- This document

## Deferred (intentional)

| Item | Notes |
|------|--------|
| `FOR UPDATE SKIP LOCKED` on Postgres | SQLite/dev DB uses transactional atomic updates today; Postgres pattern documented for future |
| WebSocket / SSE state stream | Polling and manual sync acceptable for this slice |
| Kafka, Redis dispatch queues | Not repo-ready |
| H3/S2, PostGIS, heat maps | Not in active product boundary |
| Full DISCO dispatch engine | Ranked open board only |
| Route snapshots / ETA engine | No backend proof — UI must not invent |
| Double-entry financial ledger | Stub below |
| Real payments / payouts | Backend earnings summary only |
| GPS fraud detection / high-frequency telemetry | Honest labels only |
| Rider app, admin dashboard, SOS | Out of scope |

## Rejected for now (do not force)

- localStorage as marketplace truth (mock mode is explicit dev/E2E only)
- Frontend-derived availability, nearest-driver, or fare quotes
- Agent Brief Generator executing code or claiming GO without review
- Premature PostGIS/Kafka/ledger migrations “because the dossier says so”

## Future backend slices

### FSM hardening

- Align any legacy storage aliases; add `expired` / `declined` only with jobs and ledger rules.
- Reference: `docs/RIDE_LIFECYCLE_CONTRACT.md`

### Conflict-safe dispatch (Postgres-ready)

See `docs/DISPATCH_CONCURRENCY_CONTRACT.md`.

### Route snapshots

- Persist backend route geometry and ETA only when computed server-side; expose in `RideDriverView`.

### Integer-cents financial ledger

See `docs/FINANCIAL_LEDGER_FUTURE.md`.

### Agent Brief Generator

- Remains dev-only under Diagnostics; copies structured prompts for Sonnet 4.6 planning.

## Related files

- `docs/CURRENT_TRUTH.md`
- `docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md`
- `docs/RIDE_LIFECYCLE_CONTRACT.md`
- `docs/DISPATCH_CONCURRENCY_CONTRACT.md`
- `docs/FINANCIAL_LEDGER_FUTURE.md`
- `driver-app/src/components/MapHome.jsx`
