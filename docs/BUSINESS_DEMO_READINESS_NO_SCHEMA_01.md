# HalfApp Business Demo Readiness

Date: 2026-05-18

Verdict: `GO_FOR_BUSINESS_DEMO_PREP_NO_SCHEMA`

This runbook prepares a truthful business-facing MVP demo from the already-proven HalfApp spine. It does not add database schema, migrations, product surfaces, or unsupported claims.

## Demo Story

HalfApp already has a truthful driver marketplace core. It is not just a mock screen.

The current demo proves:

- Driver availability is backend-owned through `/drivers/presence`.
- Driver heartbeat is backend-owned through `/drivers/heartbeat`.
- Available rides come from backend records.
- Hidden/dismissed rides are stored as backend visibility records and remain hidden after refresh.
- Ride lifecycle transitions are canonical and backend-enforced.
- Production builds block offline mock and simulation truth bypasses.

This is a driver-side marketplace proof, not a full production launch.

## Do Not Claim

Do not present these as implemented business capabilities:

- Payments, payouts, refunds, taxes, fees, or platform settlement.
- Route ETA, live traffic, real route geometry, or nearest-driver matching.
- Full rider app, full admin dashboard, or marketplace operations console.
- Production secret hardening, token refresh/revocation, background jobs, or web sockets.
- Dispatch auditability beyond the records and transparency already present.

## Active Demo Boundary

Use only:

- `backend`
- `driver-app`
- `docs`

Do not open or demo:

- `frontend`
- `video-gate`
- dormant admin/dashboard components
- dormant backend routers not mounted by `backend/main.py`

## Local Demo Setup

Terminal 1, backend:

```powershell
cd backend
$env:DATABASE_URL = "sqlite:///./business_demo.db"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, driver app:

```powershell
cd driver-app
$env:VITE_API_BASE = "http://127.0.0.1:8000"
$env:VITE_ALLOW_OFFLINE_MOCK = "false"
$env:VITE_ENABLE_RIDE_SIMULATION = "true"
npm run dev -- --host 127.0.0.1 --port 3022
```

Open:

```txt
http://127.0.0.1:3022
```

For a production truth check, do not enable simulation:

```powershell
cd driver-app
Remove-Item Env:\VITE_ALLOW_OFFLINE_MOCK -ErrorAction SilentlyContinue
Remove-Item Env:\VITE_ENABLE_RIDE_SIMULATION -ErrorAction SilentlyContinue
node scripts/assert-prod-truth.mjs
npm run build
```

## Demo Script

1. Register or log in as a driver.
   - Talk track: "This is the active driver app, not the legacy frontend."

2. Show the initial offline cockpit.
   - Backend fact: `GET /drivers/presence`.
   - Talk track: "The app reads driver presence from the backend. Browser refresh is not the source of marketplace truth."

3. Click `Go online`.
   - Backend fact: `PUT /drivers/presence`.
   - Talk track: "Online/offline state is persisted server-side."

4. Show heartbeat activity in the browser Network panel.
   - Backend fact: `POST /drivers/heartbeat`.
   - Talk track: "Heartbeat proves the driver is alive. The backend can derive stale and disconnected states from timestamps."

5. Create a backend simulation ride.
   - Button: `Create backend simulation ride`.
   - Backend fact: `POST /drivers/simulate-ride` creates a real `Ride` row in `requested` state.
   - Talk track: "Simulation is explicit and stored in the backend lifecycle. It is not local fake ride state."

6. Hide/dismiss the ride.
   - Button: `Dismiss ride`.
   - Backend fact: `POST /drivers/rides/{ride_id}/hide`.
   - Refresh backend rides.
   - Talk track: "Hidden rides are persisted as backend visibility records and remain hidden for this driver after refresh."

7. Create another backend simulation ride.
   - Accept the ride.
   - Advance through:
     - `accepted`
     - `driver_arrived`
     - `in_progress`
     - `completed`
   - Talk track: "The canonical ride lifecycle is enforced by the backend. The app only shows success after the backend confirms the transition."

8. Open Trips or Earnings.
   - Backend fact: completed rides and earnings are read from backend endpoints.
   - Talk track: "This is a completed-trip projection, not a payment or payout system."

9. Close with the boundary.
   - Talk track: "HalfApp is currently a truthful driver-side marketplace proof. The next engineering work is drift cleanup and dispatch auditability, not marketing claims."

## Evidence Commands

Backend:

```powershell
python -m pytest backend/tests
```

Driver app:

```powershell
cd driver-app
node scripts/assert-prod-truth.mjs
npm run build
```

Expected current proof:

- Backend tests pass.
- Driver app production build passes.
- Production truth guard rejects unsafe mock/simulation flags.

## Known Caveat

Do not add schema-heavy dispatch audit work until the Alembic drift lane is clean. A previous drift check generated real `op.*` operations, so Milestone 1.5 remains blocked until migration drift is resolved.
