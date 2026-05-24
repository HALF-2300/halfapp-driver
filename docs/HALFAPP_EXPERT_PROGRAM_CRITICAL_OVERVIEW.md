# HalfApp Expert Program Critical Overview

Date: 2026-05-18

Purpose: To deliver an expert, candid, and highly efficient architectural overview of the HalfApp program's current state, its structural vulnerabilities, and the exact engineering roadmap required for completion. This analysis is intentionally direct and uncompromising. It is designed to help engineering teams, product managers, and reviewers distinguish superficial demonstration behavior from cryptographically verifiable, production-grade marketplace capability.

## 1. Executive Verdict

The HalfApp program, in its current iteration, is strictly a driver-only ride-hailing minimum viable product. It is not yet a functional, finished marketplace platform.

The strongest aspect of the current program is the establishment of a real, shared ride lifecycle between the active backend and the driver application. Drivers can authenticate, observe backend-generated ride requests, accept those requests, transition them through pickup and transit states, finalize the trip, and view earnings computed by the backend. This is a credible functional baseline.

The paramount weakness is the discrepancy between the ambitious product goal and the implemented architectural truth. The codebase still carries legacy surfaces, dormant demonstration concepts, localized UI state, mock pathways, incomplete transparency architecture, and missing production-level database and security foundations. If these components are not systematically separated from the active build path, the platform can project an illusion of completeness that masks critical operational vulnerabilities.

The correct strategic direction is not to expand the user interface surface area to mimic a larger application. The immediate directive should be to transform the active driver MVP into a system that is truthful, auditable, and capable of withstanding production concurrency and security demands.

## 2. What The Program Is Today

The active product spine currently relies on a constrained technical stack:

- `backend`: FastAPI service handling JWT authentication, driver profile management, the driver ride lifecycle state machine, rider ride creation and cancellation endpoints, notifications, and basic earnings summaries.
- `driver-app`: React/Vite driver application with login flows, a primary operational cockpit, trip history, earnings dashboards, notifications, and profile management screens.
- `docs/RIDE_LIFECYCLE_CONTRACT.md`: the current contract for ride lifecycle state transitions.
- `docs/HALFAPP_TRANSPARENCY_ARCHITECTURE.md`: the target architecture for dispatch truth, routing auditability, presence management, and financial transparency.

Given these parameters, the current product is most accurately classified as a backend-backed driver MVP designed to test ride lifecycle state transitions.

Stakeholders should not classify the current iteration as a full rider-driver marketplace. It does not yet function as a transparent dispatch platform, a production-grade payment or payout engine, a real-time geospatial routing system, a secure administrative operations platform, or a production-ready mobile driver platform.

## 3. Current Implemented Strengths

Despite its MVP status, the program has meaningful architectural value because it has established a narrow working spine.

Driver authentication is backed by the backend service, and driver registration and login are restricted to drivers within the active app path. Ride lifecycle transitions are owned and enforced by backend state. When a trip concludes, displayed earnings are computed from backend ride records instead of frontend-submitted fare totals. The backend also supports rider-side ride creation and cancellation endpoints, which allows lifecycle testing without a dedicated rider application.

The active driver app is moving away from local fake ride state in favor of server-driven data. Foundational tests cover backend lifecycle progression, earnings calculations, rider cancellation scenarios, and driver application behavior. Simulation can generate backend ride rows when explicitly enabled. The documentation has also begun separating active product truth from legacy or demonstration code.

Slice 01 adds the first marketplace-truth improvement: driver presence is backend-owned through `GET /drivers/presence`, `PUT /drivers/presence`, and `POST /drivers/heartbeat`; temporary ride hide/dismissal is backend-owned through `POST /drivers/rides/{ride_id}/hide`; and available ride exposure writes `ride_visibility` records.

This is an effective MVP base. The core issue is not a lack of functional code. The challenge is that the trustworthy, backend-verified part of the platform is much narrower than the broader product promise.

## 4. Main Weaknesses And Vulnerabilities

### 4.1 Product Truth Is Still Too Easy To Misread

The repository contains multiple code surfaces that mimic product-like behavior but do not represent active, verifiable product truth:

- Legacy `frontend` exists but does not have a current `frontend/package.json`.
- Dormant backend routers remain in the codebase but are not mounted by `backend/main.py`.
- Dormant driver-app components exist but are not routed by `driver-app/src/App.jsx`.
- Demo messaging, mock local storage implementations, and local UI helpers remain in the tree.

The risk is that a reviewer, newly onboarded developer, or future automated agent may interpret old or mock code as production behavior. That can lead directly to compromised architectural decisions.

The required outcome is one singular, unambiguous active product path. All legacy, experimental, or archival code should be removed, quarantined, or flagged with strong deprecation warnings to prevent accidental integration.

### 4.2 Dispatch Is Honest But Not Yet Transparent

The current dispatch mechanism functions as an open board. Available rides are broadcast in a `requested` and unassigned state, allowing multiple eligible drivers to view the same shared pool. The system operates on a first-successful-claim-wins model.

This architecture is honest for a prototype because it does not falsely claim closest-driver matching. The active open-board implementation now records which drivers actually viewed a request, which deterministic rule ordered the ride board, which claim attempts won or lost, and which dispatch policy version governed the decision.

It still is not a production-grade dispatch system because it does not yet record full candidate eligibility rounds, service-area membership, geospatial eligibility, or why every non-viewing driver was excluded. To reach production-grade transparency, the system needs richer dispatch-round records and candidate evaluation events built on top of the current visibility, claim, ledger, and conflict proof records.

### 4.3 Driver Autonomy Has A First Backend Slice, But Is Still Incomplete

The driver application now reads and writes online/offline marketplace state through backend presence endpoints, and temporary ride hiding writes backend visibility records. Local cockpit state should be treated only as display/cache.

The remaining weakness is that this is still a minimal presence, hide, and open-board proof foundation, not a complete real-time marketplace autonomy system. It records requested/effective state, heartbeat timestamps, stale/disconnected derivation, visibility exposure, active hide TTL, deterministic open-board ordering, claim attempts, claim wins, and claim losses, but it does not yet provide full gateway/WebSocket presence, rich dispatch rounds, or complete driver audit projections.

The next evolution is richer presence events, dispatch-round records, and driver-facing audit views built from backend records rather than frontend explanations.

### 4.4 Money Is A Summary, Not A Ledger

The current earnings mechanism is sufficient for MVP demonstration: completed rides generate a stored `fare_amount`, and `GET /drivers/earnings` summarizes completed ride fare amounts.

This is not sufficient for a production financial system. Aggregate summaries instead of discrete transactional ledgers expose the platform to financial drift, reconciliation failures, and ambiguous historical correction. The current program lacks individual rider charge records, platform fee extraction, precise driver payout allocation, taxes, tolls, adjustments, refunds, settlement statuses, pricing rate-card versions, and auditable calculation bases.

A marketplace handles real capital, and the infrastructure must reflect that. The required outcome is a strict financial ledger using integer cents, rate-card version tracking, auditable calculation bases, explicit payout statuses, and transparent fare breakdowns visible to drivers.

### 4.5 Spatial Truth Is Not Complete

The current spatial architecture is underdeveloped. The system can store pickup/dropoff labels, raw coordinates, distance, and duration, but it cannot yet prove:

- Geocoding source.
- Routing engine.
- Route geometry.
- ETA calculation basis.
- Traffic assumptions.
- Distance calculation method.
- Location freshness.

High-fidelity map visuals can create the impression of real-time routing even when the backend has not persisted enough proof to substantiate the display. If a platform bills a rider or explains a driver earning from a route it cannot later verify, it invites legal, financial, and trust risk.

The required outcome is route snapshots, routing provider metadata, explicit distance and duration source tracking, geometry hashing, and UI behavior that only displays geographic claims the backend has persisted.

### 4.6 Production Readiness Is Not There Yet

The move from local development to public deployment is blocked by several infrastructure gaps:

- Development `SECRET_KEY` must be replaced with secure, environment-injected secrets.
- Startup-time `create_all` is not enough for production schema evolution.
- Migration discipline, such as Alembic, is absent.
- Foreign key constraints and indexes are incomplete.
- CORS must be restricted to authorized origins.
- Token revocation and refresh-token rotation are undefined.
- Structured logging, request IDs, and operational telemetry are missing.
- SQLite behavior must not be assumed to match production database locking behavior.
- Production pipelines must guarantee that mock configurations and guard-bypass pathways cannot be enabled in live builds.

Deployment hardening is required before public or money-bearing usage.

## 5. Program Goal And Marketplace Philosophy

The uncompromising future goal of HalfApp is to build a driver-first marketplace where every significant fact, metric, or status presented to a driver is backed by a durable backend record.

The backend should be able to answer high-stakes operational questions:

- Why was this driver exposed to this ride?
- Why was another nearby driver excluded?
- Who claimed the ride first under concurrent load?
- Which dispatch policy version ordered the board?
- Which route, distance, and ETA were used to quote the fare?
- What did the rider pay?
- What did the platform retain?
- What was allocated to the driver's payout ledger?
- What changed after cancellation, refund, adjustment, or dispute resolution?

If the explanation for a marketplace event is that the frontend inferred it from local state, the program has failed its transparency mandate. True marketplace architecture is defined by backend-enforced, durable truth.

## 6. Efficient Completion Strategy

The engineering strategy should prioritize stabilization and fortification of the trustworthy backend spine before expanding application surface area. Premature feature expansion will multiply the cost of foundational debt.

Explicitly de-prioritize:

- Comprehensive administrative dashboards.
- Full-featured rider applications.
- Complex payment UI.
- Advanced nearest-driver matching.
- High-fidelity mapping integrations.
- Multi-role legacy frontend revival.
- Large visual redesigns.

Prioritize:

- Backend truth.
- Active driver app alignment with backend state.
- Exhaustive audit records.
- Production database discipline through migrations.
- Tests for critical state transitions.
- Clear documentation of active system boundaries.

## 7. Recommended Next Work: Implementation Roadmap

### Phase 1: Clean Product Boundary Execution

Goal: eliminate ambiguity and operational risk from legacy or demo behavior.

Complete:

- Enforce `backend` and `driver-app` as the singular active product path.
- Archive, quarantine, or mark legacy `frontend` as inactive unless it is revived intentionally.
- Keep dormant backend routers unmounted unless a roadmap item explicitly revives and tests them.
- Remove or strongly label dormant driver-app diagnostic and demo entrypoints.
- Update documentation to state which surfaces are actively maintained.
- Configure production builds to fail if mock mode or auth bypass guards are enabled.

Definition of done:

- A newly onboarded developer can identify the active application path within five minutes.
- Active documentation never treats unmounted or legacy routes as viable product behavior.
- No production-facing screen relies on browser `localStorage` as marketplace truth.

### Phase 2: Backend Presence And State Synchronization

Goal: keep driver availability and request dismissal as backend-owned facts.

A ride-hailing architecture fails if it dispatches requests to drivers who appear available in stale client state but are disconnected in backend reality. The program should introduce server-owned presence first through REST endpoints and heartbeat, then evolve toward persistent connections such as WebSockets when real-time scale requires it.

Implemented foundation:

- `GET /drivers/presence`.
- `PUT /drivers/presence`.
- `POST /drivers/heartbeat`.
- Backend stale/disconnected derivation from heartbeat timestamps.
- `POST /drivers/rides/{ride_id}/hide`.
- Durable presence rows.
- Durable visibility and dismissal records.
- Active cockpit online/offline state reads from and writes to backend presence.

Remaining:

- Richer append-only presence event projections.
- Production-grade real-time transport if polling/heartbeat is insufficient.
- Driver-facing audit views explaining presence and visibility history.

Definition of done:

- Refreshing the browser does not alter marketplace truth.
- The backend can explain when a driver was available, stale, hidden, paused, or offline.
- A hidden ride does not reappear to the same driver unless a backend-defined contract permits it.

### Phase 3: Dispatch Auditability And Concurrency Control

Goal: make open-board dispatch explainable and safe under concurrent claim attempts.

The dispatch system should expose deterministic policy metadata while preserving the simplicity of the open board. When production database behavior is selected, claim operations must be protected by transaction semantics appropriate to that database. For PostgreSQL, this can be conditional updates, row-level locking, or another reviewed atomic claim strategy.

Complete:

- Add dispatch policy metadata to available ride responses.
- Return deterministic ordering information.
- Record ride visibility events.
- Record every claim attempt, success, and failure.
- Return deterministic `409 Conflict` responses when another driver wins.
- Add a driver-authorized dispatch proof endpoint for visible, attempted, or assigned rides.
- Validate claim safety against the selected production database, not just SQLite.

Definition of done:

- The system can explain why a ride appeared to a specific driver.
- The system can explain why a claim failed.
- The system can identify which dispatch policy was active at the time.
- Concurrent claims cannot double-book a ride.

### Phase 4: Event Sourcing And Marketplace Ledger

Goal: create an append-only source of transparency without turning every current table into an event store prematurely.

The backend now includes `marketplace_ledger_events` as the durable audit trail for consequential marketplace facts in the active product spine. Mutable projection tables, such as `rides`, still exist for efficient reads, but important marketplace state changes are also appended as immutable events.

Complete:

- Add `marketplace_ledger_events`.
- Write events for ride creation, visibility exposure, hide actions, accept attempts, accept wins, accept conflicts, declines/releases, cancellations, completions, and earnings calculations.
- Add idempotency keys for critical writes.
- Add correlation IDs to trace related events.
- Add tests proving event creation.

Definition of done:

- Important marketplace state changes are not represented only as mutable fields on `rides`.
- A driver or admin audit view can be built from backend events instead of frontend-generated explanations.

### Phase 5: Financial Ledger Implementation

Goal: decouple earnings display from the source of financial truth.

The current earnings endpoint should eventually become a projection over financial records. The platform should store currency using integer cents and avoid floating-point arithmetic for money. The ledger should record immutable financial movements such as quotes, final fare, platform fee, driver earning, adjustment, refund, and payout execution.

Complete:

- Add financial ledger records using integer cents.
- Store quote, final fare, platform fee, driver earning, adjustment, refund, and payout events.
- Track rate-card ID and calculation basis.
- Track settlement and payout status.
- Convert `GET /drivers/earnings` into a projection over ledger records.

Definition of done:

- Driver earnings are explainable down to the cent.
- Platform retained amounts are explainable.
- Adjustments and refunds append new records instead of overwriting historical truth.

### Phase 6: Route Snapshots

Goal: stop inventing spatial truth in the UI.

The backend should become the authority for route, distance, duration, and ETA claims. It can use OSRM, Valhalla, GraphHopper, a commercial maps API, or another provider, but it must persist enough route metadata to explain what was shown and billed.

Complete:

- Add a route snapshot model.
- Add a routing service interface.
- Store provider, engine version, routing profile, origin, destination, distance, duration, calculation timestamp, and geometry hash.
- Link fare quotes and dispatch previews to route snapshots when route data is used.
- Display only server-backed ETA, route, and distance facts.

Definition of done:

- Any map visualization or ETA quote references a backend route snapshot when presented as real.
- Missing route data is displayed as unavailable instead of guessed.

### Phase 7: Production Hardening And Observability

Goal: prepare the active MVP for real deployment.

Complete:

- Replace all development secrets with runtime-injected environment variables.
- Add database migration tooling such as Alembic.
- Add foreign key constraints and performance indexes.
- Restrict CORS to authorized origins.
- Define token revocation and refresh-token rotation strategy.
- Add structured JSON logging.
- Add request/correlation IDs through ASGI middleware.
- Validate transaction behavior on the chosen production database.
- Add CI checks for backend tests, driver-app build, and critical end-to-end state transitions.

Definition of done:

- The MVP can deploy through automated pipelines without local-development shortcuts.
- Schema changes are repeatable and reviewable.
- Critical state transitions are tested against production-like database behavior.
- Engineers can trace failures across a complete request or transaction path.

## 8. The Most Important Product Rule

HalfApp must never claim transparency simply because the user interface displays appealing data.

HalfApp earns the right to claim transparency only when backend durability records prove the facts:

- Lifecycle facts.
- Dispatch facts.
- Visibility facts.
- Presence facts.
- Route facts.
- Pricing facts.
- Payout facts.
- Audit facts.

This is not merely a technical guideline. It is the core program principle that should dictate every architectural decision moving forward.

## 9. Near-Term Priority List

If the engineering organization wants the fastest path to a fundamentally stronger program, execute these priorities in order.

| Priority | Strategic objective | Technical implementation focus |
| --- | --- | --- |
| 1 | Lock the active product boundary | Isolate `backend` and `driver-app`; deprecate legacy frontends and unmounted routers; reject production bypass flags. |
| 2 | Make cockpit presence backend-owned | Replace UI-state toggles with backend presence, heartbeat, stale-state detection, and eventual persistent connection support. |
| 3 | Replace local `Hide for now` | Implement `POST /drivers/rides/{ride_id}/hide` and generate durable backend visibility/dismissal records. |
| 4 | Add dispatch visibility and claim events | Record visibility, deterministic ordering, claim attempts, claim wins, claim conflicts, and policy metadata. |
| 5 | Add marketplace ledger events | Append lifecycle and marketplace events with idempotency keys and correlation IDs. |
| 6 | Add migrations and structural constraints | Integrate Alembic or equivalent migration tooling; add foreign keys and performance indexes. |
| 7 | Add financial ledger | Store currency as integer cents and record quote, final fare, platform fee, driver earning, adjustment, refund, and payout events. |
| 8 | Add route snapshots | Persist route provider metadata, distance, duration, geometry hash, and calculation timestamp before displaying real ETA or route claims. |
| 9 | Expand operational surfaces | Build rider apps, admin dashboards, and advanced pricing only after priorities 1-8 are verified. |

## 10. Final Expert Summary

The HalfApp ecosystem has a credible MVP foundation, but it remains an early-stage prototype. The active, integrated system can prove fundamental driver lifecycle behavior and compute rudimentary completed-trip earnings. It cannot yet prove fair and deterministic dispatch, secure financial settlement, verifiable routing truth, complete driver autonomy, or production readiness.

The program should pivot toward computational honesty before visual expansion. The next successful version is not the one with the most screens or dashboards. It is the one where every important pixel, notification, and monetary value presented on a screen is backed by durable, auditable backend truth.

## References

1. [Solving the Double Spend: System Design Patterns for Bulletproof Fintech](https://medium.com/codetodeploy/solving-the-double-spend-system-design-patterns-for-bulletproof-fintech-ee5d73f33415)
2. [Double-entry accounting for software engineers](https://www.balanced.software/double-entry-bookkeeping-for-programmers/)
3. [Designing a Real-Time Ledger System with Double-Entry Logic](https://finlego.com/blog/designing-a-real-time-ledger-system-with-double-entry-logic)
4. [TigerBeetle Data Modeling](https://docs.tigerbeetle.com/coding/data-modeling/)
5. [Building a Double-Entry Payment System in Elixir](https://zarar.dev/building-a-double-entry-payment-system-in-elixir/)
6. [Bayesian Modeling of Travel Times on the Example of Food Delivery](https://www.mdpi.com/2079-9292/13/17/3387)
7. [OSRM Routing Scraper](https://apify.com/parseforge/osrm-routing-scraper)
8. [Revoking Tokens - JWTdown for FastAPI](https://jwtdown-fastapi.readthedocs.io/en/latest/sessions.html)
9. [FastAPI Nested JWT Authentication](https://github.com/BrunoTanabe/fastapi-nested-jwt-authentication)
10. [FastAPI JWT Patterns](https://medium.com/@bhagyarana80/10-fastapi-jwt-patterns-that-just-work-6adbdf8ef3a6)
11. [Production-Grade Logging for FastAPI Applications](https://medium.com/@laxsuryavanshi.dev/production-grade-logging-for-fastapi-applications-a-complete-guide-f384d4b8f43b)
12. [How to Add Structured Logging to FastAPI](https://oneuptime.com/blog/post/2026-02-02-fastapi-structured-logging/view)
13. [Testing Race Conditions In A Database](https://dba.stackexchange.com/questions/148/how-do-you-test-for-race-conditions-in-a-database)
14. [Uber's Real-Time Push Platform](https://www.uber.com/gb/en/blog/real-time-push-platform/)
15. [Redis-Powered Presence](https://medium.com/tilt-engineering/redis-powered-presence-from-heartbeat-to-persistent-websocket-0455c03487a8)
16. [Event Sourcing Pattern - AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/event-sourcing.html)
17. [Event Sourcing Database Architecture](https://www.redpanda.com/guides/event-stream-processing-event-sourcing-database)
18. [Event Sourcing Pattern - Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
19. [Double-Entry Bookkeeping Database Design](https://dba.stackexchange.com/questions/102370/double-entry-bookkeeping-database-design)
20. [Books: An Immutable Double-Entry Accounting Database Service](https://developer.squareup.com/blog/books-an-immutable-double-entry-accounting-database-service/)
21. [Getting Routes On OpenStreetMap Using OSRM](https://stackoverflow.com/questions/38007333/getting-routes-on-openstreetmaps-using-osrm)
22. [JWT In FastAPI: Refresh Tokens Explained](https://medium.com/@jagan_reddy/jwt-in-fastapi-the-secure-way-refresh-tokens-explained-f7d2d17b1d17)
23. [FastAPI JWT Auth Revoking Tokens](https://indominusbyte.github.io/fastapi-jwt-auth/usage/revoking/)
24. [How to Handle JWT Authentication Securely in Python](https://oneuptime.com/blog/post/2025-01-06-python-jwt-authentication/view)
25. [Structlog Context Variables](https://www.structlog.org/en/latest/contextvars.html)
26. [FastAPI, Uvicorn, and Structlog Logging Setup](https://gist.github.com/nymous/f138c7f06062b7c43c060bf03759c29e)
27. [Integrating FastAPI with Structlog](https://wazaari.dev/blog/fastapi-structlog-integration)
