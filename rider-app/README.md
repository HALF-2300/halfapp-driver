# HalfApp Rider App

Rider product surface (Downloads UI + HalfApp API adapter) — book, track, and receipt against the real backend.

**Not** `rider-stub/` (demo) · **Not** `frontend/` (archive).

Authoritative context: `docs/CURRENT_TRUTH.md` · Two-sided loop: `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md`

## Features

- Rider register / login (`POST /auth/rider/register`, `POST /auth/rider/login`)
- **BookRide** — pickup/dropoff geocode (Nominatim), `POST /rides/estimate`, request ride
- **TrackRide** — status banner mapped from backend (`requested` → UI `requesting`, etc.)
- **Receipt** — `GET /rides/{id}/payment` or ride pricing fallback
- Live updates via SSE (`GET /rides/{id}/stream?access_token=…`) with polling fallback
- `useRide` hook adapts Downloads field names to `pickup_latitude` / `dropoff_location` API

## Run locally

1. Start backend (from repo root):

```powershell
cd backend
py -3.11 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

2. Install and start rider app:

```powershell
cd rider-app
npm install
npm run dev
```

3. Open `http://127.0.0.1:3023` — register a rider account, request a ride.

4. In parallel, run the driver app (`driver-app`, port 3022) with an approved driver online to accept and complete the ride.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE` | `http://127.0.0.1:8000` | Backend origin |
| `VITE_API_PROXY_TARGET` | unset | When set, Vite proxies `/api` to backend (Playwright / same-origin dev) |

## Phase 1 done criteria

- Rider opens app → requests ride → sees status progress through completion
- Driver sees ride on open board → accepts → completes
- No manual API calls required for the happy path

## Tests

```powershell
cd rider-app
npm test
```

Backend rider auth + API loop:

```powershell
cd backend
py -3.11 -m pytest tests/test_rider_auth.py tests/test_ride_flow_ui_proof.py -q
```
