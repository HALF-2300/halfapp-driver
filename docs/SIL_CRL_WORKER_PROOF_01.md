# SIL/CRL background worker proof (P1.5)

**Date:** 2026-05-25  
**Alembic:** `0034_sil_crl_snapshots` (indexes on existing snapshot tables from `0030` / `0031`)

## What changed

- **Compute split:** `gather_sil_cell_scratches` / `persist_sil_bucket` in `services/sil_compute.py`; `gather_crl_cell_scratches` / `persist_crl_bucket` in `services/crl_compute.py`; attribution stays in `services/crl_attribution.py`.
- **Worker:** `jobs/sil_crl_worker.py` — SIL every 60s, CRL every 5m (`run_sil_recompute_once`, `run_crl_recompute_once`). Optional in-process loop when `HALFAPP_SIL_CRL_WORKER_ENABLED=1`.
- **Read path:** `services/sil_snapshot.py` and `services/crl_snapshot.py` serve map/explain from precomputed rows when the current bucket exists; otherwise one live recompute.
- **Headers:** `GET /v1/sil/map` and `/suggest` set `X-SIL-Source: snapshot|live`. CRL routes set `X-CRL-Source`.

## Snapshot tables (canonical names)

| Spec alias | Actual table | Migration |
|------------|--------------|-----------|
| `sil_cell_snapshot` | `sil_cell_aggregate` | `0030_sil_foundation` |
| `crl_label_snapshot` | `crl_cell_explanation` (+ `crl_cell_snapshot`) | `0031_crl_foundation` |

## Latency note

Before P1.5, `GET /v1/sil/map` called `compute_sil_bucket` on every request (rides + telemetry scan + H3 aggregation + DB write). After P1.5, a warm bucket is a single indexed read on `sil_cell_aggregate` — request path avoids re-aggregation when the worker (or a prior request) has populated the current bucket.

Measured informally in local SQLite tests: map handler drops from full recompute to snapshot read when `X-SIL-Source: snapshot` (see `backend/tests/test_sil_crl_worker.py`).

## Verification

```bash
cd backend && pytest tests/test_sil_crl_worker.py tests/test_sil_v01.py tests/test_crl_v01.py -q
cd backend && alembic current   # expect 0036_driver_readiness_fields after full upgrade
```

## Tests

- `test_worker_populates_sil_snapshot_table`
- `test_sil_map_header_snapshot_after_worker` → `X-SIL-Source: snapshot`
- `test_sil_map_header_live_when_snapshot_empty` → `X-SIL-Source: live`
