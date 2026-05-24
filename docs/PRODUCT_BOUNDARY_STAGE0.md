# Product Boundary — Stage 0 Truth Lock

Date: 2026-05-22  
Orders: `HALFAPP_STAGE0_TRUTH_BOUNDARY_LOCK_01`, `HALFAPP_TRUTH_SYNC_V0_1_DOC_RECONCILIATION_01`, `HALFAPP_TRUTH_SYNC_BACKLOG_RECONCILIATION_01`  
Status: **Active contract** for engineers, reviewers, agents, and investors.

This repository is **not** a complete mobility, routing, or city-scale ride-hailing operating system. The active product is a **driver lifecycle spine** with a minimal rider API, honest open-board dispatch proofs, and a **v0.1 foundation** (pricing ledger, map, routing metadata).

Companion docs:

- `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md` — **active** product-completion plan (internal owner-car testing only)
- `docs/HALFAPP_TRUSTED_NO_MONEY_BETA_BOUNDARY_PACK_01.md` — **DEFERRED** archive (external trusted-driver beta not in scope)
- `docs/CURRENT_TRUTH.md` — short operational truth (v0.1 synced; current-state table)
- `docs/BACKLOG.md` — reconciled ticket classification; **closed P0 lanes — do not reopen without rescope**
- `docs/RIDE_APP_FOUNDATION_V0_1.md` — v0.1 pricing, map, navigation scope
- `docs/DORMANT_ROUTERS_INVENTORY.md` — mounted vs unmounted backend routers
- `docs/RIDE_LIFECYCLE_CONTRACT.md` — ride API contract
- `docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md` — full program snapshot
- `frontend/README.md` — legacy frontend archive marker

Proof:

```powershell
py -3.11 scripts/print_active_routes.py
py -3.11 scripts/verify_current_truth_backlog.py
```

**Closed lanes (do not reopen without rescope):** AUTH-001, RIDE-001, RIDE-002, RIDE-003, DRIVER-001B, DRIVER-002, TEST-ISOLATION-01, HALFAPP_PRODUCTION_SECRET_KEY_GUARD_01, HALFAPP_ENGINEERING_INTELLIGENCE_SAFE_SHELL_01 — see `docs/BACKLOG.md`.

---

## Active product surfaces (only these)

| Surface | Path | Role |
|---------|------|------|
| Backend API | `backend/` | FastAPI: auth, driver lifecycle, presence, open-board dispatch audit, v0.1 pricing/routing metadata, rider create/cancel API, notifications, earnings **summaries** |
| Driver app | `driver-app/` | React/Vite driver cockpit — **only** active frontend; **`/drivers/*` path only** |

Entry points:

- `backend/main.py`
- `driver-app/src/App.jsx`

**Driver-app must not call** dossier endpoints `/supply/*`, `/demand/*`, `/trip/*` — see `docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md`.

---

## v0.1 nuance (read with Stage 0)

Stage 0 remains strict. v0.1 adds **real** pricing and map foundations without upgrading the program to payments or production routing.

**Pricing ledger truth is not payment truth.**  
Integer-cent `ride_pricing` proves quote/completion breakdown and `financial_locked` — not wallet balance, PSP capture, payout execution, or settlement.

**Route provider metadata is not production routing proof unless runtime proof is GO.**  
`osrm_self_hosted` in code/tests is not the same as live OSRM on port 5000. See `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md`.

**Leaflet/OSM visualization is not geocoding/ETA proof.**  
The in-app map shows coordinates and provider labels; it does not prove address geocoding or marketed live ETA product.

---

## What is real (may be claimed when backed by tests/OpenAPI)

- Driver JWT registration/login and profile.
- Backend-owned ride lifecycle: `requested → accepted → driver_arrived → in_progress → completed`.
- Rider API: `POST /rides/`, `POST /rides/{id}/cancel` (no rider app UI).
- Open-board dispatch: shared pool, first atomic claim wins, visibility and claim-attempt records, structured `409` conflicts.
- Backend-owned driver presence (`available` / `offline` / `paused` / stale / disconnected via heartbeat).
- Backend ride hide/dismiss with TTL visibility records.
- Append-only `marketplace_ledger_events` for key marketplace actions.
- **Integer-cent pricing quote/completion ledger** (`ride_pricing`, `pricing_policy`) with lock on complete.
- **Leaflet/OSM in-app map foundation** with backend route provider metadata on rides.
- **External Google Maps navigation** links (no Maps embed in active path).
- **Routing provider metadata** with honest fallback labels (`haversine_fallback` when OSRM unreachable).
- Completed-trip earnings **projection** from completed rides and pricing rows (not payout settlement).
- Explicit **simulation** rides (`lifecycle_reason=simulation`) when build flags allow.
- Internal health: `GET /internal/system-health`.
- End-to-end UI proof lane: `docs/RIDE_FLOW_UI_PROOF_V0_2_STATUS.md` (**GO**).

---

## What is demo-only (must be labeled, never sold as production)

| Item | How it appears | Rule |
|------|----------------|------|
| Offline mock | `VITE_ALLOW_OFFLINE_MOCK=true` | localStorage fake API; not marketplace truth |
| Ride simulation UI | `VITE_ENABLE_RIDE_SIMULATION=true` | Creates real DB rows but not real rider demand |
| `haversine_fallback` routing | Backend `route_provider` when OSRM down | Honest estimate; not road-network truth |
| Guard bypass | `VITE_ENABLE_GUARD_BYPASS` (non-prod only) | E2E only; not security |
| Dossier endpoints | `/supply`, `/demand`, `/trip` | Foundation/tests only; not cockpit truth |

---

## What is inactive (not product; do not cite in PRs or decks)

| Surface | Status |
|---------|--------|
| `frontend/` | Legacy multi-role UI; **not** mounted on active API; see `frontend/README.md` |
| `video-gate/` | Unrelated video QA tooling |
| `backend/routes/admin.py` | Dormant — not in `main.py` |
| `backend/routes/admin_access.py` | Dormant |
| `backend/routes/rides.py` | Dormant legacy rider router (superseded by `rider_rides.py`) |
| `backend/routes/users.py` | Dormant |
| `backend/routes/test.py` | Dormant |
| Dossier spine as driver UX | Mounted API only — **not** wired to `driver-app` |
| Dormant `driver-app` components | Not imported by `App.jsx` |

---

## Forbidden claims (do not put in README, UI, tests, or investor copy)

Until a separate implementation order explicitly ships and tests each capability:

- **No real payments** — no Stripe/wallet/capture/payout/settlement product.
- **No payout execution or settlement ledger as live product truth** — pricing rows are not money movement.
- **No production OSRM** — unless `SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS` runtime verdict is **GO**.
- **No live ETA product** marketed as shipped.
- **No commercial paid-traffic APIs** — experimental traffic signals only.
- **No nearest-driver auto-dispatch** — open board only; dossier geospatial auto-match is not driver-app truth.
- **No rider app UI** — API-only rider side.
- **No live admin ops UI** — dormant admin routers.
- **No city-scale marketplace / mobility OS** claims.
- **No geocoding proof** from address text alone.
- **No dossier `ledger_*` as driver-app earnings truth** — parallel foundation only.

Allowed honest framing: *"Driver-only MVP with backend lifecycle, open-board dispatch audit, integer-cent pricing ledger, Leaflet/OSM map foundation, and routing metadata with honest fallback; payments and production OSRM not shipped."*

---

## Must not be revived without a separate explicit order

| Item | Why gated |
|------|-----------|
| `frontend/` multi-role app | Calls unmounted `/admin/*`, legacy `/rides/*`; confuses product truth |
| Mounting `routes/admin.py` or `routes/admin_access.py` | Requires admin RBAC, auth tests, and ops contract |
| Mounting `routes/rides.py` | Conflicts with active `rider_rides` prefix; legacy contract |
| Mounting `routes/test.py` | Debug surface; security risk in production |
| Starting API with `SECRET_KEY=change_me` in production | Boot guard rejects with `Unsafe SECRET_KEY for production` (see `CURRENT_TRUTH.md`) |
| Wiring dossier endpoints to `driver-app` | Requires `HALFAPP_DOSSIER_SPINE_RECONCILIATION_01` merge plan |
| Payment UI or PSP integration | Requires settlement design beyond `ride_pricing` |
| Claiming production OSRM without runtime proof | Requires `RUNTIME_PROOF_PROCEDURE.md` GO |
| Nearest-driver or geo dispatch marketing | Requires dispatch engine order |

Revival checklist for any gated surface:

1. Registered in `backend/main.py`
2. Documented in `docs/CURRENT_TRUTH.md`
3. Backend tests + OpenAPI proof
4. No contradiction with forbidden claims until capability is actually implemented

---

## Reviewer checklist (PR approval)

- [ ] Behavior reachable from `backend/main.py` and/or `driver-app/src/App.jsx`
- [ ] Driver-app does not call `/supply`, `/demand`, or `/trip`
- [ ] No forbidden claim added to UI or docs
- [ ] Dormant/legacy code not described as shipped
- [ ] `py -3.11 scripts/print_active_routes.py` matches doc if routes changed
- [ ] Mock/simulation still blocked in production build when touched
- [ ] Pricing claims use `ride_pricing`; payment/settlement language absent unless shipped
- [ ] Routing claims respect OSRM runtime status doc
