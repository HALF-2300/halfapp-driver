# Run HalfApp driver stack locally

**Layout:** `backend/` (FastAPI) + `driver-app/` (Vite/React)  
**Alembic head:** `0026` (run `alembic upgrade head` before boot)  
**Entry:** `main:app` from `backend/` (not `backend.main:app`)

---

## Ports (repo defaults)

| Service | URL | Notes |
|---------|-----|--------|
| Backend | `http://127.0.0.1:8000` | `uvicorn main:app` |
| Driver app (dev) | `http://127.0.0.1:3022` | `vite.config.js` `server.port` + `strictPort` |
| Driver app (preview) | `http://127.0.0.1:3022` | Same port after `npm run build` |
| Playwright E2E | `3024` / `8011` | Isolated; do not use for daily dev |

**API base:** `VITE_API_BASE=http://127.0.0.1:8000` (`driver-app/.env.example`)

---

## One-shot scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_dev.ps1` | Windows: migrate + backend reload + Vite dev (new windows) |
| `scripts/run_dev.sh` | Linux/macOS: same stack in one terminal |
| `scripts/run_prod.sh` | Linux/macOS: workers + build + `vite preview` |
| `scripts/verify_all.ps1` | pytest + npm test + build + ride-flow E2E |

### Dev (Windows)

```powershell
cd c:\Users\him\Desktop\halfapp-driver
powershell -ExecutionPolicy Bypass -File scripts\run_dev.ps1
# Live API (no offline mock):
powershell -ExecutionPolicy Bypass -File scripts\run_dev.ps1 -RealBackend
```

### Dev (Linux/macOS)

```bash
cd /path/to/halfapp-driver
bash scripts/run_dev.sh
bash scripts/run_dev.sh --real-backend
```

### Prod-style preview (Linux/macOS)

```bash
bash scripts/run_prod.sh
```

`vite preview` is for local staging only; production should serve `driver-app/dist/` via nginx or equivalent.

### Verify everything green

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_all.ps1
powershell -ExecutionPolicy Bypass -File scripts\verify_all.ps1 -SkipE2e
```

---

## Manual (two terminals)

**Backend:**

```powershell
cd backend
copy .env.example .env   # first time
py -3.11 -m alembic upgrade head
py -3.11 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Driver app:**

```powershell
cd driver-app
$env:VITE_API_BASE = "http://127.0.0.1:8000"
$env:VITE_ALLOW_OFFLINE_MOCK = "false"   # optional: force live API
npm run dev
```

Open: **http://127.0.0.1:3022**

Health check: **http://127.0.0.1:8000/health**

---

## Environment

**SQLite (default dev):** `DATABASE_URL=sqlite:///./halfapp.db` in `backend/.env`

**Postgres:**

```env
DATABASE_URL=postgresql+psycopg2://halfapp:halfapp@localhost:5432/halfapp
```

**CORS:** `backend/.env.example` includes `http://127.0.0.1:3022` for the driver app.

**Offline mock:** `driver-app/.env.development` sets `VITE_ALLOW_OFFLINE_MOCK=true` so `npm run dev` works without a backend. Use `-RealBackend` / `--real-backend` or set `VITE_ALLOW_OFFLINE_MOCK=false` when testing against the API.

---

## OSRM (optional)

```powershell
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
powershell -ExecutionPolicy Bypass -File scripts\osrm_healthcheck.ps1
```

See `docker/osrm-portland/README.md` and `docs/HALFAPP_OSRM_OPS_ONLY_SLICE_05.md`.

---

## Related

- `docs/BUSINESS_DEMO_READINESS_NO_SCHEMA_01.md` — demo env vars
- `backend/main.py` — uvicorn one-liner in module docstring
- `docs/HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01.md` — slice verification rituals
