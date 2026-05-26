# P0-G7 — Alembic PostgreSQL compatibility proof

**Task:** P0-G7
**Date:** 2026-05-25
**STATUS:** **GO** — fresh PostgreSQL 16 `alembic upgrade head` passed locally on a temporary user-space cluster

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
# Agent host — SQLite regression (PASS, head 0036):
cd backend
$env:DATABASE_URL = "sqlite:///./g7_test_fresh2.db"
py -3.11 -m alembic upgrade head
py -3.11 -m alembic current   # 0036_driver_readiness_fields (head)

# Local PostgreSQL 16 proof (PASS):
& 'C:\Program Files\PostgreSQL\16\bin\initdb.exe' -D '<codex-workspace>\pgdata-g1b' -U halfapp --auth=trust --encoding=UTF8
& 'C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe' -D '<codex-workspace>\pgdata-g1b' -o '-p 55432' -l '<codex-workspace>\pgdata-g1b.log' start
& 'C:\Program Files\PostgreSQL\16\bin\createdb.exe' -h 127.0.0.1 -p 55432 -U halfapp halfapp_test
$env:DATABASE_URL = "postgresql+psycopg2://halfapp@127.0.0.1:55432/halfapp_test"
cd backend
py -3.11 -m alembic upgrade head
py -3.11 -m pytest -q tests/test_alembic_postgres_upgrade_head.py tests/test_postgres_claim_race_proof_01.py
```

**Note:** Docker Desktop API access remains blocked on this host, but G7 no longer depends on Docker because the proof ran on a real local PostgreSQL 16 cluster.

---

## Latest local proof (2026-05-25)

```powershell
& 'C:\Program Files\PostgreSQL\16\bin\initdb.exe' -D '<codex-workspace>\pgdata-g1b' -U halfapp --auth=trust --encoding=UTF8
# Result: Success

& 'C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe' -D '<codex-workspace>\pgdata-g1b' -o '-p 55432' -l '<codex-workspace>\pgdata-g1b.log' start
# Result: server started

& 'C:\Program Files\PostgreSQL\16\bin\createdb.exe' -h 127.0.0.1 -p 55432 -U halfapp halfapp_test
# Result: exit 0

$env:DATABASE_URL='postgresql+psycopg2://halfapp@127.0.0.1:55432/halfapp_test'
cd backend
py -3.11 -m alembic upgrade head
# Result: upgraded through 0036_driver_readiness_fields

py -3.11 -m pytest -q tests/test_alembic_postgres_upgrade_head.py tests/test_postgres_claim_race_proof_01.py
# Result: 2 passed, 4 warnings in 7.48s
```

**Interpretation:** G7 is **GO** on this workstation. The full Alembic chain reached `0036_driver_readiness_fields` on a fresh PostgreSQL 16 database.

---

## PROOF

| Item | Status |
|------|--------|
| Audit doc per revision | `docs/ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md` |
| No history rewrite / no squash | Yes |
| Closed lanes untouched | Yes |
| SQLite `alembic upgrade head` → `0036_driver_readiness_fields` | **PASS** (this run) |
| PostgreSQL `alembic upgrade head` on fresh DB | **PASS** |
| CI job uses migrations | **Yes** — see snippet below |
| `test_alembic_postgres_upgrade_head` on PG | **PASS** |
| Claim-race on migrated schema | **PASS** — `test_postgres_claim_race_proof_01.py` (no `create_all`) |

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

G1 claim-race now runs against the **Alembic migration chain** on PostgreSQL, not interim `create_all`. See `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md`.

---

## GO criteria (G7)

1. `alembic upgrade head` exit 0 on fresh PostgreSQL 16 (empty DB). **MET**
2. `test_alembic_postgres_upgrade_head` pass. **MET**
3. Claim-race proof on the Alembic-migrated PostgreSQL schema. **MET**

---

## DOCS UPDATED

- `docs/ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md`
- `docs/P0_G7_ALEMBIC_POSTGRES_PROOF_01.md`
- `docs/CURRENT_TRUTH.md` (G7 row)
- `backend/alembic/versions/0001_alembic_hardened_schema.py`
- `backend/alembic/versions/0014_dispatch_cascade_and_terminal_status.py`

---

## NEXT TASK

**Owner/Agent:** G2 OSRM runtime and G3 courier day remain.
**Agent:** None for G7 unless CI later fails this same proof path.
**Do not start P1.1** until remaining P0 gates are closed or explicitly waived.
