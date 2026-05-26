# Dossier Path Decision — Path A vs Path B

**Task:** P0-G4  
**Date:** 2026-05-25  
**STATUS:** **GO** (decision doc complete — **execution deferred** until owner picks)

## Inventory

| Area | Paths |
|------|-------|
| Migration | `backend/alembic/versions/0006_dossier_dispatch_ledger_foundation.py` |
| Models | `backend/models/dossier_marketplace.py` |
| Routes | `backend/routes/dossier_marketplace.py` — `/supply/heartbeat`, `/demand/request`, `/trip/complete` |
| Services | `backend/services/dossier_dispatch.py`, `dossier_ledger.py` |
| Schemas | `backend/schemas/dossier_marketplace.py` |
| Tests | `backend/tests/test_dossier_dispatch_ledger_slice.py`, `test_dossier_mount_gate.py` |
| Mount gate | `HALFAPP_DOSSIER_SPINE_ENABLED` in `backend/main.py` (default **off** in production surface tests) |
| Driver app | **No references** — `driver-app/src/utils/api.js` uses `/drivers/*` only |

**Tables (dossier-only):** `active_drivers`, `trip_lifecycle_events`, `ledger_accounts`, `ledger_transactions`, `ledger_entries` — parallel to `rides`, `driver_presence`, `marketplace_ledger_events`.

## Path A — Remove parallel spine (recommended for delivery focus)

**Actions (future PR, not this task):**

1. Stop mounting `dossier_marketplace_router` in `main.py` (already default-off).
2. Delete or archive routes/services/schemas/tests that exist only for dossier.
3. Keep migration `0006` in history (no rewrite) — document tables as deprecated/unused.
4. Remove `HALFAPP_DOSSIER_SPINE_ENABLED` from conftest default if tests no longer need mount.
5. Update `HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md` → status **RETIRED**.

**Pros:** Single marketplace truth (`/drivers/*`); less agent confusion; smaller attack surface.  
**Cons:** Lose experimental double-entry / PostGIS experiments unless exported elsewhere.

## Path B — Merge into active spine (high cost)

**Actions (future program):**

1. Map dossier FSM (`trip_lifecycle_events`) to `rides.status` contract or replace lifecycle service.
2. Unify ledger: either migrate `ledger_*` to settlement obligations or drop double-entry.
3. Replace `active_drivers` geospatial rows with `driver_presence` + dispatch ranking.
4. Wire **nothing** to driver-app until OpenAPI + claim-lock tests pass on merged API.
5. Multi-migration sequence + data backfill plan.

**Pros:** Preserves architecture dossier investment.  
**Cons:** Large scope; risks reopening closed dispatch lanes; delays delivery-complete P1.

## Recommendation

**Path A** for HalfApp Driver’s stated product: **delivery execution car** on `/drivers/*`. The dossier spine was a foundation experiment; it is not on the courier critical path and creates dual-truth risk.

## Owner decision (fill in)

| Choice | Date | Owner initial |
|--------|------|---------------|
| ☐ Path A — retire dossier product surface | | |
| ☐ Path B — merge program (separate epic) | | |

**No code execution until one box is checked.**
