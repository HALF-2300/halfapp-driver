# Final Report: HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01

**Date:** 2026-05-22  
**Verdict:** **GO**

---

## Postgres environment

| Item | Value |
|------|--------|
| Host | `localhost` |
| Port | `55432` (user-local `pg_ctl` instance; Windows service on `5432` was stopped / access denied) |
| Database | `halfapp_test` |
| User | `halfapp` (trust auth on temp cluster) |
| PostgreSQL | 16.x (`C:\Program Files\PostgreSQL\16\bin`) |
| Driver | `psycopg2-binary` (installed for this proof run) |

**DATABASE_URL shape (secrets redacted):**

`postgresql+psycopg2://halfapp:****@localhost:55432/halfapp_test`

---

## Schema notes

### `ride_claim_attempts`

Direct columns used by proof assertions:

| Column | Role |
|--------|------|
| `ride_id` | FK to `rides.id` |
| `driver_id` | Claiming driver |
| `outcome` | `won` (1 row) or `conflict` (9 rows) on losers — not the string `lost` |
| `competing_driver_id`, `reason`, `policy_version` | Audit metadata |

### `marketplace_ledger_events`

**Not JSON-only** — direct columns:

| Column | Role |
|--------|------|
| `ride_id` | Filter for per-ride dispatch proof |
| `event_type` | `dispatch.claim_won` (1), `dispatch.claim_lost` (9) |
| `driver_id`, `actor_id`, `payload_json` | Emitted via `record_ledger_entry` → `append_marketplace_event` |

Proof helper counts `event_type` on `ride_id`; no JSON metadata scan required.

---

## Migration output

`alembic upgrade head` against PostgreSQL **fails** (expected today):

```text
sqlalchemy.exc.ProgrammingError: syntax error at or near "PRAGMA"
[SQL: PRAGMA foreign_keys=OFF]
```

Alembic revision `0001_alembic_hardened_schema` is SQLite-oriented. For this proof lane only, schema was created with **ORM `Base.metadata.create_all`** after stripping SQLite `CHECK (col IN (0, 1))` constraints on BOOLEAN columns (see `tests/test_postgres_claim_race_proof_01.py` `_patch_run_migrations_for_postgres`).

**Implication:** Production Postgres still needs Alembic/DDL reconciliation; this GO proves **dispatch claim locking under Postgres concurrency**, not full migration portability.

---

## Focused proof output (observed)

Command:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://halfapp@localhost:55432/halfapp_test"
$env:SECRET_KEY = "pytest-halfapp-test-secret-32chars-minimum"
$env:HALFAPP_ENV = "test"
cd backend
py -3.11 -m pytest -q tests/test_postgres_claim_race_proof_01.py -s
```

```json
{
  "assigned_driver_count": 1,
  "claim_attempt_rows": 10,
  "claim_lost_rows": 9,
  "claim_won_rows": 1,
  "database_url_redacted": "postgresql+psycopg2://halfapp:****@localhost:55432/halfapp_test",
  "dispatch.claim_lost_events": 9,
  "dispatch.claim_won_events": 1,
  "duplicate_winners": 0,
  "ghost_assignment": false,
  "other_status_codes": [],
  "postgres_dialect": "postgresql",
  "structured_409_conflicts": 9,
  "successful_accepts": 1
}
```

**Result:** `1 passed in 2.98s`

All GO thresholds met:

| Metric | Required | Observed |
|--------|----------|----------|
| `successful_accepts` | 1 | 1 |
| `structured_409_conflicts` | 9 | 9 |
| `assigned_driver_count` | 1 | 1 |
| `duplicate_winners` | 0 | 0 |
| `ghost_assignment` | false | false |
| `claim_attempt_rows` | 10 | 10 |
| `claim_won_rows` | 1 | 1 |
| `claim_lost_rows` | 9 | 9 |
| `dispatch.claim_won_events` | 1 | 1 |
| `dispatch.claim_lost_events` | 9 | 9 |

---

## Representative 409 payload

```json
{
  "assigned_driver_id": 6,
  "claim_result": "lost",
  "current_status": "accepted",
  "detail": "Ride already claimed",
  "reason": "ride_already_claimed",
  "ride_id": 1,
  "state_changed": false,
  "truth_status": "backend_conflict"
}
```

Structured conflict contract matches SQLite concurrency proof (`test_ride_claim_lock_concurrency.py`).

---

## Claim / audit evidence

| Store | Evidence |
|-------|----------|
| `rides` | Single row `status=accepted`, one `driver_id` matching the 200 winner |
| `ride_claim_attempts` | 10 rows: 1× `outcome=won`, 9× `outcome=conflict` |
| `marketplace_ledger_events` | 1× `dispatch.claim_won`, 9× `dispatch.claim_lost` (direct `ride_id` + `event_type`) |
| HTTP | 1× 200, 9× 409, 0 other status codes |

No dispatch code changes were required for GO.

---

## Full backend suite result

After `Remove-Item Env:DATABASE_URL` (SQLite test isolation restored):

```text
265 passed, 2 skipped in 126.58s
```

The postgres proof test is **skipped** when `DATABASE_URL` is not PostgreSQL (2 skips include this lane and any other skip markers).

---

## Files touched

| File | Change |
|------|--------|
| `backend/tests/test_postgres_claim_race_proof_01.py` | **New** — 10-driver threaded race + observed JSON output |
| `backend/tests/conftest.py` | Preserve `DATABASE_URL` when PostgreSQL; dialect-aware reseed (`ON CONFLICT`, `NOW()`) |
| `docs/HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01_REPORT.md` | This report |

**Forbidden lanes respected:** no dispatch rewrite, dossier, pricing/settlement/payment, or cockpit/audit/route UI changes.

---

## How to re-run

1. Start PostgreSQL (service or local `pg_ctl` on a free port).  
2. Create DB/user if needed.  
3. Set `DATABASE_URL` to `postgresql+psycopg2://USER:PASS@HOST:PORT/halfapp_test`.  
4. `pip install psycopg2-binary` if missing.  
5. `cd backend && py -3.11 -m pytest -q tests/test_postgres_claim_race_proof_01.py -s`  
6. Clear `DATABASE_URL` before the default SQLite suite: `Remove-Item Env:DATABASE_URL`.

---

## Final verdict

**GO** — Ten concurrent `POST /drivers/accept-ride/{id}` calls on **real PostgreSQL** produced exactly one winner, nine structured 409 conflicts, one assigned driver, ten claim-attempt rows, matching `dispatch.claim_won` / `dispatch.claim_lost` ledger events, and a green full backend suite on SQLite afterward.

**Remaining gap (not blocking this lane):** Alembic migrations are not yet PostgreSQL-safe (`PRAGMA` in `0001`); production deploy must not rely on `create_all` from the proof patch.
