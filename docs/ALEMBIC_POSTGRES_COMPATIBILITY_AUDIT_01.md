# Alembic PostgreSQL compatibility audit (P0-G1)

**Date:** 2026-05-25 (updated P0-G7 pass)  
**Goal:** `alembic upgrade head` on a **fresh** PostgreSQL 16 database with zero errors.  
**Helpers:** `backend/db_migration_helpers.py` (import from revisions; not the `alembic` package).

---

## Summary

| Category | Revisions | PostgreSQL handling |
|----------|-----------|---------------------|
| SQLite-only (guarded) | 0001, 0002, 0003 | PG branch or early-return; no PRAGMA/sqlite_master on PG |
| SQLite triggers only | 0001, 0002, 0005, 0006 | Triggers skipped on PG; append-only enforced in app |
| `INSERT OR IGNORE` | 0006, 0008 | `ON CONFLICT DO NOTHING` on PG via `insert_seed_ignore()` |
| PostGIS optional | 0006 | `pg_available_extensions` check; lat/lng index fallback |
| Portable `exec_driver_sql` DDL | 0010–0035 (most) | `CREATE TABLE IF NOT EXISTS` / indexes — runs on PG |
| Portable Alembic ops | 0009, 0014, 0015+ | `op.create_table`, `op.add_column`, dialect branches |
| Already dual-dialect | 0009 | BOOLEAN vs INTEGER for `traffic_signal_aware` |

---

## Revision inventory

### 0001_alembic_hardened_schema

| Issue | SQLite | PostgreSQL fix |
|-------|--------|----------------|
| `PRAGMA foreign_keys`, `PRAGMA foreign_key_check` | upgrade/downgrade | **PG path:** `_upgrade_postgresql_fresh()` — `_create_schema()` DDL only, no PRAGMA |
| `sqlite_master` / `PRAGMA table_info` | introspection | PG uses `db_migration_helpers.table_exists` only on sqlite branch |
| `CHECK (col IN (0,1))` on BOOLEAN | valid | Stripped on PG; `DEFAULT true/false` |
| `INTEGER PRIMARY KEY` (no autoincrement on PG) | sqlite autoincrement | **PG:** first `INTEGER PRIMARY KEY` per `CREATE TABLE` → `SERIAL PRIMARY KEY` in `_create_schema()` |
| `RAISE(ABORT)` triggers on `marketplace_ledger` | append-only | **Skipped on PG** |

### 0002_canonical_ride_status_contract

| Issue | SQLite | PostgreSQL fix |
|-------|--------|----------------|
| `sqlite_master`, `PRAGMA legacy_alter_table`, table rebuild | legacy migration | **PG early-return** when `rides` exists (0001 already canonical) |
| SQLite triggers in `_rebuild_ride_dependents` | sqlite only | Not executed on PG |

### 0003_driver_presence_and_visibility_hide

| Issue | SQLite | PostgreSQL fix |
|-------|--------|----------------|
| `PRAGMA table_info` | column check | `db_migration_helpers.add_column_if_missing` |

### 0004_restore_schema_indexes

| Issue | PostgreSQL |
|-------|------------|
| Index DDL only | **OK** — portable |

### 0005_marketplace_ledger_events_foundation

| Issue | SQLite | PostgreSQL fix |
|-------|--------|----------------|
| `RAISE(ABORT)` triggers | append-only | `create_sqlite_append_only_triggers()` — sqlite only |

### 0006_dossier_dispatch_ledger_foundation

| Issue | SQLite | PostgreSQL fix |
|-------|--------|----------------|
| `CREATE EXTENSION postgis` | optional | `try_create_postgis_extension()` — skip geometry if unavailable |
| Four `RAISE(ABORT)` triggers | append-only | sqlite-only helpers |
| `INSERT OR IGNORE` seed | seed rows | `ON CONFLICT (id) DO NOTHING` on PG |
| PG balance trigger | `EXECUTE FUNCTION` | Runs only when `is_postgres` |

### 0007_v01_pricing_map_foundation

| Issue | PostgreSQL fix |
|-------|----------------|
| `ALTER TABLE rides ADD COLUMN` | `ADD COLUMN IF NOT EXISTS` on PG |

### 0008_pricing_policy_and_ledger_columns

| Issue | PostgreSQL fix |
|-------|----------------|
| `INSERT OR IGNORE` | `ON CONFLICT (id) DO NOTHING` |
| `ride_pricing` columns | `IF NOT EXISTS` on PG |

### 0009_traffic_signal_aware

| Issue | PostgreSQL |
|-------|------------|
| Column type | **Already branched** (INTEGER sqlite / BOOLEAN pg) |

### 0010–0013, 0016–0019, 0021–0035

| Issue | PostgreSQL |
|-------|------------|
| `exec_driver_sql` CREATE/INDEX | **OK** on PG (no PRAGMA) |

### 0014_dispatch_cascade

| Issue | Lines | PostgreSQL fix |
|-------|-------|----------------|
| `batch_alter_table("rides")` | `upgrade`/`downgrade` | **PG:** `op.add_column` / `op.drop_column`; **SQLite:** `batch_alter_table` (legacy rebuild path) |

### 0015_dispatch_log_reason

| Issue | PostgreSQL fix |
|-------|----------------|
| `batch_alter_table` for NOT NULL | `op.alter_column` on PG |

### 0020_payment_execution_charge_id

| Issue | PostgreSQL fix |
|-------|----------------|
| `ADD COLUMN` | `IF NOT EXISTS` on PG |

---

## Production schema path

| Environment | Schema source |
|-------------|---------------|
| **PostgreSQL (staging/prod target)** | `alembic upgrade head` — **required** after this audit |
| **SQLite (local fast dev)** | `alembic upgrade head` (verified) or app startup `run_migrations()` |
| ~~ORM `create_all` bypass~~ | **Removed** from claim-race proof (was interim only) |

Append-only tables without PG triggers: enforced in `services/ledger.py` and related writers (unchanged).

---

## Verification commands

```bash
docker compose up -d postgres
export DATABASE_URL=postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test
cd backend && alembic upgrade head
pytest tests/test_alembic_postgres_upgrade_head.py tests/test_postgres_claim_race_proof_01.py -q
```

CI: `.github/workflows/halfapp-driver-ci.yml` → job `postgres-claim-race`.

---

## Known limitations

- **PostGIS:** Geometry column on `active_drivers` only when extension is installed; CI `postgres:16` image typically has no PostGIS — migration falls back to lat/lng index.
- **Revision chain gap:** `0032_ride_payments_foundation` → `0034_sil_crl_snapshots` (no `0033` file; reserved for P1.1 push). Head: `0035_telemetry_retention_index`.
