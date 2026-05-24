# Driver-app ↔ backend alignment report

Status: **GO** (baseline) + **CLEANUP GO** (this pass).

Earlier passes proved the alignment baseline (real API for register/login,
`PUT /drivers/profile`, `POST /drivers/update-location`, pytest + Playwright).
This document folds in the deprecation-warning cleanup.

---

## Cleanup pass: deprecated `datetime.utcnow()` removal

`datetime.utcnow()` is deprecated in Python 3.12+. Goal of this pass: clear
every warning emitted in the live import graph **without** changing API
contracts, JWT semantics, or DB column shapes (SQLAlchemy `DateTime` columns
stay naive; comparison sites stay naive).

### Strategy

Added `backend/services/datetime_utils.py` with a single helper:

```python
def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

This is a *behavioral* drop-in for `datetime.utcnow()`: same wall time, no
`tzinfo`, no deprecation warning. Existing SQLAlchemy `DateTime` columns and
already-stored naive UTC values keep working unchanged. JWT `exp` payload still
encodes the identical UTC timestamp (no token-semantic change).

### Files touched (cleanup)

- `backend/services/datetime_utils.py` — **new**, shared helper.
- `backend/services/auth.py` — JWT `exp` uses `utc_now_naive()`.
- `backend/models/ride.py` — `Column(default=utc_now_naive)`.
- `backend/routes/drivers.py` — all lifecycle timestamps + earnings windows.
- `backend/routes/notifications.py` — `created_at` default, `expires_at`
  computation, expiry filter.
- `backend/routes/rider_rides.py` — `cancelled_at`.
- `backend/routes/admin.py` — analytics time windows.
- `backend/routes/admin_access.py` — code-generation timestamp.
- `backend/tests/test_earnings_contract.py` — `completed_at` fixture.
- `backend/tests/conftest.py` — also adds `backend/` to `sys.path` so the
  user’s proof command works from repo root.
- `backend/tests/test_smoke.py` — **(re)created**; aligned with the new
  `conftest.py` (env-driven temp SQLite) and the new `/health` shape.

### Files **not** touched (deliberate)

- `backend/services/auth_optimized.py` — still contains four
  `dt.datetime.utcnow()` calls. This file is **not imported anywhere** (its
  own dep `database_optimized` does not exist in the tree). Because it never
  runs, no warning is emitted in tests or at startup. Patching it would force
  changes to a dead module whose surface is undefined. Documented here; if it
  is ever revived, it must be migrated then.

### Warnings status

- pytest run (15 tests, smoke + lifecycle + earnings + rider-cancel):
  **0 warnings**.
- Trust-lane Playwright (7 tests): server emits unrelated
  `InsecureKeyLengthWarning` from `PyJWT` (SECRET_KEY too short for SHA256);
  **no `datetime.utcnow` warnings**.

---

## Boundary harden: CORS union

`backend/main.py` previously did `os.getenv("CORS_ORIGINS", DEFAULT)`. When
`CORS_ORIGINS` was set in a parent shell to a partial list (e.g. only
`:3000`/`:3001`), driver-app/preview origins (`:3022`, `:3023`) were silently
dropped → browser fetch became “Failed to fetch”.

Replaced with a **union**:

- Built-in dev origins (`:3022`, `:3023`, `:5173` for IPv4 + localhost).
- Plus anything the env contributes.
- De-duplicated, order-preserving.

**Production tightening (explicit)**: when deploying, the unioned dev defaults
above SHOULD be removed and `CORS_ORIGINS` set to ONLY the real public
origin(s). The merge logic is a dev-only convenience.

---

## Confirmation: real-API E2E, mock fallback gated

`driver-app/src/utils/api.js`:

```js
const ALLOW_OFFLINE_MOCK = import.meta.env.VITE_ALLOW_OFFLINE_MOCK === 'true'
```

All offline branches are wrapped in `if (!ALLOW_OFFLINE_MOCK) { throw error }`.

Two Playwright configs by design:

- `playwright.config.js` — fast lane. Default test command. Builds with
  `VITE_ALLOW_OFFLINE_MOCK=true` so failed API calls fall through to local
  mock data for navigation tests. **Mock fallback is explicit, not silent.**
- `playwright.trust.config.js` — trust lane. Builds with
  `VITE_ALLOW_OFFLINE_MOCK=false`, boots its own uvicorn on `:8010` (CORS in
  unioned defaults), and runs `tests/trust-mock-off/`. Asserts: no mock
  banner, register → empty pool from API, earnings $0.00 from API, inbox
  empty from API, accept-ride failure surfaces a visible error.

Both lanes were exercised in this pass; both green.

---

## Proof commands and results (this run)

### 1. Backend pytest smoke (user's exact command, from repo root)

```
.\.venv\Scripts\python.exe -m pytest backend\tests\test_smoke.py -v
```

Result:
```
collected 2 items
backend/tests/test_smoke.py::test_health PASSED                          [ 50%]
backend/tests/test_smoke.py::test_register_login_profile_location PASSED [100%]
2 passed in 1.27s
```

### 2. Full backend test suite (from `backend/`)

```
..\.venv\Scripts\python.exe -m pytest tests -v
```

Result: **15 passed in 4.40s** (no warnings).

### 3. Driver-app production build

```
cd driver-app
npm run build
```

Result: **built in 1.24s** (`dist/assets/...`). Browserslist note unrelated to
this pass.

### 4. Default Playwright lane (auth + nav)

```
cd driver-app
npx playwright test tests/auth-flow.spec.ts tests/nav-flow.spec.ts
```

Backend on `127.0.0.1:8000` (real) for auth-flow’s register/login; nav-flow
seeds a mock driver because `VITE_ALLOW_OFFLINE_MOCK=true` is set explicitly
by this config.

Result: **2 passed (7.8s)**.

### 5. Trust lane Playwright (real API only, mocks **off**)

```
cd driver-app
npx playwright test --config playwright.trust.config.js
```

Brings up a dedicated uvicorn on `:8010` (SQLite) and a Vite dev server on
`:3023` built with `VITE_ALLOW_OFFLINE_MOCK=false`.

Result: **7 passed (8.2s)**.

### 6. Frontend production build

```
cd frontend
npm run build
```

Result: **FAIL — `frontend/package.json` does not exist on disk** (only
`dist/`, `node_modules/`, `src/` survive). This is unrelated to the cleanup
pass; the tree was already in this state before the datetime work started and
remains pre-existing project state. Other surfaces (driver-app, backend) are
unaffected. Flagged for the next pass.

---

## Git / artifact hygiene

`.git/` is currently absent from the working tree (pre-existing). Therefore
nothing was committed in this pass. `.gitignore` retains driver-app
auth-snapshot exclusions for whenever the repo is re-initialized.

`driver-app/tests/.auth/driver.json` is regenerated by `global-setup.ts` per
run and continues to be excluded by `.gitignore` rules; not present in
working tree after this run.

---

## Honest status

- **datetime.utcnow warnings**: cleared in the entire live import graph.
  Remaining occurrences only in `backend/services/auth_optimized.py`, which is
  dead code (no importers, missing dep). Documented.
- **JWT semantics**: unchanged. `exp` encodes the same UTC instant.
- **DB shape**: unchanged. All `DateTime` columns remain naive; all comparisons
  remain naive-vs-naive.
- **CORS**: dev-default union restored; production tightening documented.
- **Mock fallback**: gated on `VITE_ALLOW_OFFLINE_MOCK=true`; trust lane proves
  real-API behavior with mocks off.
- **Frontend build**: blocked by missing `frontend/package.json` — out of
  scope for this pass.

## Verdict

`DRIVER_APP_BACKEND_ALIGNMENT_CLEANUP: GO`
