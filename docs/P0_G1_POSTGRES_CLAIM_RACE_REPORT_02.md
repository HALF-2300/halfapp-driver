# P0-G1 — PostgreSQL claim-race (supersedes REPORT_01)

**Task:** P0-G1  
**Date:** 2026-05-25  
**STATUS:** **GO** (fresh PostgreSQL 16 Alembic chain + claim-race proof passed locally on temporary user-space cluster)

**Supersedes:** `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_01.md` (premature GO with `create_all` bypass)

---

## Owner finding (accepted)

Report 01 marked GO while noting `alembic upgrade head` failed on PostgreSQL. That meant:

- Claim-race CI used ORM `create_all`, not the migration chain.
- No proven deploy path for PostgreSQL staging/production.

**Remediation:** cross-dialect migration fixes + CI must run `alembic upgrade head` before claim-race tests.

---

## COMMAND RUN

```bash
# SQLite regression (this agent run — PASS):
cd backend && DATABASE_URL=sqlite:///./alembic_pg_test.db alembic upgrade head

# PostgreSQL proof (PASS on temporary local PostgreSQL 16 cluster):
& 'C:\Program Files\PostgreSQL\16\bin\initdb.exe' -D '<codex-workspace>\pgdata-g1b' -U halfapp --auth=trust --encoding=UTF8
& 'C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe' -D '<codex-workspace>\pgdata-g1b' -o '-p 55432' -l '<codex-workspace>\pgdata-g1b.log' start
& 'C:\Program Files\PostgreSQL\16\bin\createdb.exe' -h 127.0.0.1 -p 55432 -U halfapp halfapp_test
cd backend
$env:DATABASE_URL='postgresql+psycopg2://halfapp@127.0.0.1:55432/halfapp_test'
py -3.11 -m alembic upgrade head
py -3.11 -m pytest -q tests/test_alembic_postgres_upgrade_head.py tests/test_postgres_claim_race_proof_01.py
```

**CI (authoritative when green):** job `postgres-claim-race` → `alembic upgrade head` → `test_alembic_postgres_upgrade_head` → `test_postgres_ten_driver_claim_race_proof_01`.

---

## PROOF

| Item | Status |
|------|--------|
| `docs/ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md` | Written |
| Revisions 0001–0008, 0014, 0015, 0020, 0007 PG guards | Fixed in place (G7: `P0_G7_ALEMBIC_POSTGRES_PROOF_01.md`) |
| `db_migration_helpers.py` | Added |
| `create_all` bypass removed from claim-race test | Done |
| CI uses `alembic upgrade head` | Done |
| Claim lock SQL | **Unchanged** |
| Local `alembic upgrade head` on PostgreSQL 16 | **PASS** — temporary user-space PG cluster on `127.0.0.1:55432` |
| Claim-race on migrated PostgreSQL schema | **PASS** — `test_postgres_claim_race_proof_01.py` |
| Prior 1×200 / 9×409 on PG (`HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01_REPORT`) | Historical — must re-run on migrated schema |

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
# Result: upgraded through 0036_driver_readiness_fields on the latest re-run

py -3.11 -m pytest -q tests/test_alembic_postgres_upgrade_head.py tests/test_postgres_claim_race_proof_01.py
# Result: 2 passed, 4 warnings in 9.32s
```

**Interpretation:** G1 is **GO** for local PostgreSQL proof. The claim-race test now runs against the real Alembic-migrated PostgreSQL schema, not an ORM `create_all` bypass. Docker remains unavailable through the Docker Desktop API on this host, but it is no longer blocking the PostgreSQL proof because a real local PostgreSQL 16 cluster was used.

---

## DOCS UPDATED

- `docs/ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md`
- `docs/P0_G7_ALEMBIC_POSTGRES_PROOF_01.md`
- `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md`
- `docs/CURRENT_TRUTH.md` (G1 → GO)
- `backend/db_migration_helpers.py`, multiple `alembic/versions/*.py`
- `.github/workflows/halfapp-driver-ci.yml`
- `backend/tests/test_alembic_postgres_upgrade_head.py`
- `backend/tests/test_postgres_claim_race_proof_01.py`

---

## GO criteria

1. `alembic upgrade head` exit 0 on fresh PostgreSQL 16. **MET**
2. `test_alembic_postgres_upgrade_head` pass. **MET**
3. `test_postgres_ten_driver_claim_race_proof_01` pass (1 winner, 9×409) **without** `create_all`. **MET**

Claim-race on migrated schema is a **stronger** proof than the interim `create_all` path in REPORT_01.

---

## NEXT TASK

**G2/G3:** Independent runtime / human gates — see `P0_G2_OSRM_RUNTIME_PROOF_01.md`, `OWNER_COURIER_DAY_REPORT_01.md`.
