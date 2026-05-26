# P0-G1 — PostgreSQL claim-race (supersedes REPORT_01)

**Task:** P0-G1  
**Date:** 2026-05-25  
**STATUS:** **PARTIAL_GO** (code + CI path ready; **local PG proof blocked** — Docker not available on proof host)

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

# PostgreSQL (required for GO — not run locally; Docker daemon stopped):
docker compose up -d postgres
export DATABASE_URL=postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test
cd backend && alembic upgrade head
pytest tests/test_alembic_postgres_upgrade_head.py tests/test_postgres_claim_race_proof_01.py -q
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
| Local `alembic upgrade head` on PostgreSQL | **Not executed** (no PG server) |
| Prior 1×200 / 9×409 on PG (`HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01_REPORT`) | Historical — must re-run on migrated schema |

---

## Latest local attempt (2026-05-25)

```powershell
docker compose up -d postgres
# Result: docker is not recognized on this machine

cd backend
py -3.11 -m pytest -q tests/test_postgres_claim_race_proof_01.py
# Result: 1 skipped, 4 warnings
```

**Interpretation:** G1 remains **PARTIAL_GO**. The code path and CI-oriented proof test are present, but this workstation cannot run the local PostgreSQL container proof until Docker/Postgres is installed or a `DATABASE_URL` points at a reachable PostgreSQL instance.

---

## DOCS UPDATED

- `docs/ALEMBIC_POSTGRES_COMPATIBILITY_AUDIT_01.md`
- `docs/P0_G7_ALEMBIC_POSTGRES_PROOF_01.md`
- `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md`
- `docs/CURRENT_TRUTH.md` (G1 → PARTIAL_GO)
- `backend/db_migration_helpers.py`, multiple `alembic/versions/*.py`
- `.github/workflows/halfapp-driver-ci.yml`
- `backend/tests/test_alembic_postgres_upgrade_head.py`
- `backend/tests/test_postgres_claim_race_proof_01.py`

---

## GO criteria (not yet met locally)

1. `alembic upgrade head` exit 0 on fresh PostgreSQL 16.
2. `test_alembic_postgres_upgrade_head` pass.
3. `test_postgres_ten_driver_claim_race_proof_01` pass (1 winner, 9×409) **without** `create_all`.

When CI job `postgres-claim-race` is green (and G7 **GO**), owner may promote G1 to **GO**. Claim-race on migrated schema is a **stronger** proof than the interim `create_all` path in REPORT_01.

---

## NEXT TASK

**Owner:** Local PG proof (same commands as G7 proof doc) or confirm CI `postgres-claim-race` green.  
**G2/G3:** Independent owner runtime — see `P0_G2_OSRM_RUNTIME_PROOF_01.md`, `OWNER_COURIER_DAY_REPORT_01.md`.
