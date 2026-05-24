# Dormant Routers Inventory

Date: 2026-05-20  
Order: `HALFAPP_STAGE0_TRUTH_BOUNDARY_LOCK_01`  
Source of truth for mounting: `backend/main.py`

Verify active paths anytime:

```powershell
cd c:\Users\him\Desktop\halfapp-driver
py -3.11 scripts/print_active_routes.py
```

---

## How routers are registered

`backend/main.py` calls `app.include_router(...)` only for:

| Module | Variable | Prefix | Tags |
|--------|----------|--------|------|
| `routes/auth.py` | `auth_router` | `/auth` | auth |
| `routes/drivers.py` | `drivers_router` | `/drivers` | drivers |
| `routes/internal.py` | `internal_router` | `/internal` | internal |
| `routes/notifications.py` | `notifications_router` | `/notifications` | notifications |
| `routes/rider_rides.py` | `rider_rides_router` | `/rides` | rider-rides |

Plus app-level route:

- `GET /health`

---

## Mounted routers (active product)

### `routes/auth.py` → `/auth`

| Method | Path |
|--------|------|
| POST | `/auth/register` |
| POST | `/auth/login` |
| GET | `/auth/me` |

### `routes/drivers.py` → `/drivers`

| Method | Path |
|--------|------|
| GET | `/drivers/` |
| GET | `/drivers/presence` |
| PUT | `/drivers/presence` |
| POST | `/drivers/heartbeat` |
| GET | `/drivers/my-rides` |
| GET | `/drivers/rides/{ride_id}/transparency` |
| GET | `/drivers/available-rides` |
| POST | `/drivers/simulate-ride` |
| POST | `/drivers/accept-ride/{ride_id}` |
| POST | `/drivers/decline-ride/{ride_id}` |
| POST | `/drivers/dismiss-ride/{ride_id}` |
| POST | `/drivers/rides/{ride_id}/hide` |
| POST | `/drivers/arrive-pickup/{ride_id}` |
| POST | `/drivers/start-ride/{ride_id}` |
| POST | `/drivers/complete-ride/{ride_id}` |
| GET | `/drivers/earnings` |
| GET | `/drivers/performance` |
| GET | `/drivers/insights` |
| PUT | `/drivers/profile` |
| GET | `/drivers/status` |
| POST | `/drivers/update-location` |
| GET | `/drivers/statistics` |

### `routes/internal.py` → `/internal`

| Method | Path |
|--------|------|
| GET | `/internal/system-health` |

### `routes/notifications.py` → `/notifications`

| Method | Path |
|--------|------|
| GET | `/notifications/` |
| POST | `/notifications/send` |
| POST | `/notifications/{notification_id}/read` |
| DELETE | `/notifications/{notification_id}` |
| POST | `/notifications/driver/ride-alert` |

### `routes/rider_rides.py` → `/rides` (active rider contract)

| Method | Path |
|--------|------|
| POST | `/rides/` |
| POST | `/rides/{ride_id}/cancel` |
| POST | `/rides/{ride_id}/action` |

> **Note:** `POST /rides/{ride_id}/action` exists in code; confirm contract in `docs/RIDE_LIFECYCLE_CONTRACT.md` before UI claims.

---

## Unmounted routers (dormant — not active product)

These files exist under `backend/routes/` but are **not** imported or `include_router`'d in `main.py`.

### `routes/admin.py` → would be `/admin`

| Method | Path (if mounted) |
|--------|-------------------|
| GET | `/admin/users` |
| GET | `/admin/drivers` |
| GET | `/admin/rides` |
| POST | `/admin/users/{user_id}/toggle-active` |
| GET | `/admin/analytics/overview` |
| GET | `/admin/analytics/driver-performance` |
| GET | `/admin/analytics/earnings-report` |

### `routes/admin_access.py` → would be `/admin-access`

| Method | Path (if mounted) |
|--------|-------------------|
| POST | `/admin-access/generate-code` |
| POST | `/admin-access/validate-code` |
| POST | `/admin-access/register-admin` |
| GET | `/admin-access/list-codes` |

### `routes/rides.py` → would be `/rides` (legacy)

| Method | Path (if mounted) |
|--------|-------------------|
| POST | `/rides/` |
| GET | `/rides/` |

**Conflict risk:** Same `/rides` prefix as `rider_rides.py`. Must not mount both without a deliberate merge order.

### `routes/users.py` → would be `/users`

| Method | Path (if mounted) |
|--------|-------------------|
| GET | `/users/` |

### `routes/test.py` → would be `/test`

| Method | Path (if mounted) |
|--------|-------------------|
| GET | `/test/db-connection` |
| POST | `/test/driver-data` |
| GET | `/test/driver-logs` |

---

## Risks if dormant routers are mistaken as active

| Risk | Detail |
|------|--------|
| **False admin readiness** | Legacy `frontend` calls `/admin/*`; those return 404 on the active app — dashboards look built but are not live. |
| **False rider product** | Legacy `frontend` may call `/rides/request` or legacy list routes not on active `rider_rides` contract. |
| **OpenAPI / doc drift** | Reading `admin.py` or `rides.py` without checking `main.py` overstates shipped API surface. |
| **Security exposure** | Mounting `test.py` or `admin_access.py` without hardening exposes debug or bootstrap endpoints. |
| **Prefix collision** | Mounting legacy `rides.py` alongside `rider_rides.py` duplicates `/rides/` handlers. |
| **Investor/demo fraud** | Screenshots from unmounted code imply payouts, fleet analytics, or ops consoles that do not run. |

Enforced by: `backend/tests/test_active_route_surface.py` (no `/admin`, `/admin-access`, `/test`, `/users` prefixes on live app).

---

## Files in `backend/routes/` summary

| File | Mounted? |
|------|----------|
| `auth.py` | Yes |
| `drivers.py` | Yes |
| `internal.py` | Yes |
| `notifications.py` | Yes |
| `rider_rides.py` | Yes |
| `admin.py` | **No** |
| `admin_access.py` | **No** |
| `rides.py` | **No** |
| `users.py` | **No** |
| `test.py` | **No** |
| `__init__.py` | N/A |
