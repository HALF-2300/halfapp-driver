# HalfApp Ops Console

Internal operator control plane for HalfApp — **live backend data only**.

## Port

**3024** (`http://127.0.0.1:3024`)

## Features (Phase 4)

- Ride list with status, rider/driver IDs, payment status (5s polling)
- Ride detail with lifecycle events, payment state, cancel + force-assign
- Driver list with online/presence and active ride

## Auth

Uses `POST /auth/admin/login` with an **admin** user in the database.

For local dev, seed an admin via test helper or DB:

```bash
# With ALLOW_TEST_USER_SEED=true in backend .env:
curl -X POST http://127.0.0.1:8000/internal/test-users -H "Content-Type: application/json" -d '{"role":"admin","email":"ops@local.test","password":"pw12345","name":"Ops"}'
```

## Run

```bash
cd ops-app
npm install
npm run dev
```

Backend must be running on `:8000`. CORS includes `:3024` in development automatically.

## Truth

- Simulated payments — not bank payouts
- No analytics dashboards or RBAC beyond admin JWT
- All actions mutate real backend state
