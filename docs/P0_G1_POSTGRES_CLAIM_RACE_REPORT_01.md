# P0-G1 — PostgreSQL Claim-Race Report

> **Superseded by** `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_02.md` (CI now uses `alembic upgrade head`, not `create_all`). YAML excerpt below is **stale**.

**Task:** P0-G1  
**Date:** 2026-05-25  
**STATUS:** **SUPERSEDED** — see REPORT_02

## COMMAND RUN

```bash
# Local (requires Docker):
docker compose up -d postgres
export DATABASE_URL=postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp
export SECRET_KEY=pytest-postgres-claim-race-secret-32chars-min
export HALFAPP_ENV=test
cd backend
python scripts/prepare_postgres_claim_race_schema.py
pytest tests -k claim_race -q

```

## CI YAML excerpt (`.github/workflows/halfapp-driver-ci.yml`)

The job **exists** — it is not only documented; it boots PostgreSQL and runs the claim-race test:

```yaml
  postgres-claim-race:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: halfapp
          POSTGRES_PASSWORD: halfapp
          POSTGRES_DB: halfapp_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U halfapp -d halfapp_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install backend deps
        run: pip install -r backend/requirements.txt
      - name: Prepare PostgreSQL schema (ORM create_all — Alembic PG blocked on SQLite PRAGMAs)
        env:
          DATABASE_URL: postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test
          PYTHONPATH: backend
        run: python backend/scripts/prepare_postgres_claim_race_schema.py
      - name: Run Postgres claim race proof (10 concurrent accepts → 1×200, 9×409)
        env:
          DATABASE_URL: postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp_test
          PYTHONPATH: backend
          SECRET_KEY: pytest-postgres-claim-race-secret-32chars-min
          HALFAPP_ENV: test
          HALFAPP_ENABLE_RIDE_SIMULATION: "1"
          ALLOW_TEST_USER_SEED: "true"
          HALFAPP_DOSSIER_SPINE_ENABLED: "0"
        run: python -m pytest backend/tests -k claim_race -q
```

Contrast: job `truth-and-drift` uses `DATABASE_URL: sqlite:///./backend/ci_test.db` — claim-race is **not** proven on SQLite in CI.

**Prior runtime proof:** `docs/HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01_REPORT.md` (2026-05-22, 1×200 / 9×409 on PostgreSQL 16).

## PROOF

| Acceptance item | Evidence |
|-----------------|----------|
| `docker-compose.yml` postgres:16 | Root `docker-compose.yml` service `postgres` |
| `backend/.env.example` PG default | `DATABASE_URL=postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp` |
| `backend/README.md` PG-first dev | PostgreSQL-first quick start + claim-race commands |
| CI job `postgres-claim-race` | Boots PG service, `prepare_postgres_claim_race_schema.py`, `pytest -k claim_race` |
| 10 concurrent accepts → 1 winner, 9×409 | `test_postgres_ten_driver_claim_race_proof_01` |
| Structured 409 body | `detail`, `claim_result=lost`, `truth_status=backend_conflict`, `reason=ride_already_claimed` |
| Claim lock SQL unchanged | No edits to atomic claim / `UPDATE … WHERE driver_id IS NULL` lane |

## Schema note

Full `alembic upgrade head` on PostgreSQL still fails on SQLite `PRAGMA` revisions. P0-G1 uses ORM `create_all` via `scripts/prepare_postgres_claim_race_schema.py` (same approach as the claim-race test module). Production DDL reconciliation remains a separate track.

## DOCS UPDATED

- `docker-compose.yml`, `backend/.env.example`, `backend/README.md`
- `backend/scripts/prepare_postgres_claim_race_schema.py`
- `.github/workflows/halfapp-driver-ci.yml`
- `backend/tests/test_postgres_claim_race_proof_01.py` (`claim_race` marker)
- `docs/P0_G1_POSTGRES_CLAIM_RACE_REPORT_01.md`, `docs/CURRENT_TRUTH.md`

## GOVERNANCE CHECK

Claim-lock SQL not modified. No money/AI/prod-truth copy changes in this lane.

## NEXT TASK

**P0-G2** — OSRM runtime proof (`scripts/prove_osrm_runtime.py`, `SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md`).
