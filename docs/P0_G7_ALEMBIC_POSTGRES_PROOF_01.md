# P0-G7 — Alembic PostgreSQL compatibility proof

**Task:** P0-G7  
**Date:** 2026-05-25  
**STATUS:** **PARTIAL_GO** — code path + CI wiring **GO**; **fresh PostgreSQL `alembic upgrade head` not executed on this host** (Docker not on PATH)

---

## Goal

`alembic upgrade head` succeeds on a fresh PostgreSQL 16 database. CI claim-race job uses the real migration chain (not ORM `create_all`). Closed lanes (claim lock SQL, lifecycle state machine, pricing lock-on-complete) were not modified.

---

## Revisions changed (this G7 pass)

| Revision | Change |
|----------|--------|
| `0001_alembic_hardened_schema` | PG `_create_schema`: map first `INTEGER PRIMARY KEY` per `CREATE TABLE` → `SERIAL PRIMARY KEY` (autoincrement on greenfield PG) |
| `0014_dispatch_cascade` | PG: `op.add_column` / `op.drop_column`; SQLite: retain `batch_alter_table` |

Prior G7/G1 work (unchanged this pass): `db_migration_helpers.py`; dual-dialect guards in `0002`–`0008`, `0015`, `0020`; CI job already runs `alembic upgrade head`.

Full audit: `docs/ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md`.

---

## COMMAND RUN

```powershell
# Agent host — SQLite regression (PASS, head 0035):
cd backend
$env:DATABASE_URL = "sqlite:///./g7_test_fresh2.db"
py -3.11 -m alembic upgrade head
py -3.11 -m alembic current   # 0035_telemetry_retention_index (head)

# Owner / CI — PostgreSQL (required for G7 GO):
docker compose up -d postgres
$env:DATABASE_URL = "postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test"
cd backend
alembic upgrade head
pytest tests/test_alembic_postgres_upgrade_head.py tests/test_postgres_claim_race_proof_01.py -q
```

**Blocker on agent host:** `docker` not recognized (Docker not installed or not on PATH).

---

## Latest local attempt (2026-05-25)

```powershell
cd backend
py -3.11 -m pytest -q tests/test_alembic_postgres_upgrade_head.py
# Result: 1 skipped in 0.16s
```

**Interpretation:** G7 remains **PARTIAL_GO** on this workstation. The PG-specific pytest is present and skips when no PostgreSQL `DATABASE_URL` is available; a fresh PostgreSQL service or CI run is still required for GO.

---

## PROOF

| Item | Status |
|------|--------|
| Audit doc per revision | `docs/ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md` |
| No history rewrite / no squash | Yes |
| Closed lanes untouched | Yes |
| SQLite `alembic upgrade head` → `0035_telemetry_retention_index` | **PASS** (this run) |
| PostgreSQL `alembic upgrade head` on fresh DB | **Not run locally** |
| CI job uses migrations | **Yes** — see snippet below |
| `test_alembic_postgres_upgrade_head` on PG | Runs in CI when `DATABASE_URL` is postgresql |
| Claim-race on migrated schema | `test_postgres_claim_race_proof_01.py` in same CI job (no `create_all`) |

---

## CI job snippet (authoritative PG proof)

From `.github/workflows/halfapp-driver-ci.yml` job `postgres-claim-race`:

```yaml
      - name: Alembic upgrade head on PostgreSQL
        working-directory: backend
        env:
          DATABASE_URL: postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test
        run: alembic upgrade head

      - name: Verify Alembic head on PostgreSQL (pytest)
        env:
          DATABASE_URL: postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test
          PYTHONPATH: backend
        run: python -m pytest backend/tests/test_alembic_postgres_upgrade_head.py -q

      - name: Run Postgres claim race proof (10 concurrent accepts → 1×200, 9×409)
        env:
          DATABASE_URL: postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test
          ...
        run: python -m pytest backend/tests/test_postgres_claim_race_proof_01.py -q
```

`backend/scripts/prepare_postgres_claim_race_schema.py` is a deprecated thin wrapper around `alembic upgrade head`.

---

## G1 interaction (stronger claim-race proof)

When G7 is **GO**, G1 claim-race runs against the **Alembic migration chain** on PostgreSQL, not interim `create_all`. See `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md`. Promote G1 to **GO** when CI `postgres-claim-race` is green (or owner reproduces locally).

---

## GO criteria (G7)

1. `alembic upgrade head` exit 0 on fresh PostgreSQL 16 (empty DB).
2. `test_alembic_postgres_upgrade_head` pass.
3. CI `postgres-claim-race` green on the branch that includes this G7 pass.

Until (1) is confirmed locally or (3) is green on CI, G7 remains **PARTIAL_GO**.

---

## DOCS UPDATED

- `docs/ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md`
- `docs/P0_G7_ALEMBIC_POSTGRES_PROOF_01.md`
- `docs/CURRENT_TRUTH.md` (G7 row)
- `backend/alembic/versions/0001_alembic_hardened_schema.py`
- `backend/alembic/versions/0014_dispatch_cascade_and_terminal_status.py`

---

## NEXT TASK

**Owner:** G1/G2/G3 runtime (Docker, OSRM, courier day).  
**Agent:** None for G7 until PG proof fails in CI — then fix failing revision only.  
**Do not start P1.1** until P0 gates owner-closed + G7 **GO**.
