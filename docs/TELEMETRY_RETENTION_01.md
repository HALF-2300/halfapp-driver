# Telemetry retention (P1.6)

**Date:** 2026-05-25  
**Alembic:** `0035_telemetry_retention_index`  
**Config:** `HALFAPP_TELEMETRY_RETENTION_DAYS` (default `14`)

## Behavior

- Table: `driver_telemetry_points` (`created_at` indexed for range deletes).
- Job: `jobs/telemetry_retention.run_telemetry_retention_once` deletes rows older than the retention window.
- Heatmap (`build_fleet_traffic_heatmap`) is computed on read from recent points; there is no separate aggregate table to refresh before delete.

## Operations

Run daily via cron or external scheduler (not enabled automatically in tests):

```bash
cd backend
python -c "from database import SessionLocal; from jobs.telemetry_retention import run_telemetry_retention_once; db=SessionLocal(); print(run_telemetry_retention_once(db)); db.close()"
```

## Verification

```bash
cd backend && pytest tests/test_telemetry_retention.py -q
```

## Tests

- `test_telemetry_retention_deletes_old_points`
- `test_telemetry_retention_preserves_within_window`
