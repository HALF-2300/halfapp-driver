# HalfApp Backend API

FastAPI service for the **delivery driver** execution spine, requester API (`/rides/*`), ops admin routes, and optional intelligence overlays.

## Quick start (SQLite — fastest)

```powershell
cd backend
py -3.11 -m pip install -r requirements.txt
copy .env.example .env
py -3.11 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## PostgreSQL-first dev (recommended for P0)

From repo root:

```powershell
docker compose up -d postgres
```

Set in `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp
SECRET_KEY=dev-secret-at-least-32-characters-long
HALFAPP_ENV=development
```

Run claim-race proof:

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp"
$env:SECRET_KEY = "pytest-halfapp-test-secret-32chars-minimum"
$env:HALFAPP_ENV = "test"
py -3.11 -m pytest tests/test_postgres_claim_race_proof_01.py -q
```

**Note:** Full `alembic upgrade head` on PostgreSQL may fail on SQLite-specific revisions; the claim-race lane uses ORM `create_all` (see test module). Production still needs Alembic/DDL reconciliation.

## OSRM routing (optional P0)

```powershell
cd docker/osrm-portland
# One-time: prepare Oregon extract — see README in that folder
docker compose up -d
```

In `backend/.env`:

```env
OSRM_BASE_URL=http://127.0.0.1:5000
ROUTING_PROVIDER=osrm_self_hosted
ROUTING_FALLBACK_ENABLED=true
```

Proof:

```powershell
py -3.11 scripts/prove_osrm_runtime.py
```

## Tests

```powershell
cd backend
py -3.11 -m pytest tests -q
py -3.11 scripts/owner_runbook_verify.py
```

CI: `.github/workflows/halfapp-driver-ci.yml` includes `postgres-claim-race` job.

## Active surface

Only routes registered in `main.py` are product truth. Regenerate path checklist:

```powershell
py -3.11 ../scripts/print_active_routes.py
```

Compare with `tests/test_active_route_surface.py` → `ACTIVE_PATHS`.
