# HALFAPP_PRODUCTION_GUARDS_SECRET_SIMULATION_CORS_01

**Date:** 2026-05-22  
**Scope:** Security/truth-boundary hardening — no product features.

---

## Verdict

**GO** — see verification section in agent final report.

---

## Implemented

### 1. `SECRET_KEY` boot guard

- Module: `backend/production_guards.py` + `backend/config.py`
- **Production:** rejects empty, known defaults (`change_me`, `dev`, repo default), substrings `change_me`, and keys shorter than 32 characters.
- **Test:** requires explicit non-default secret (≥16 chars); pytest conftest sets `pytest-halfapp-test-secret-32chars-minimum`.
- **Development:** allows repository default for local work; rejects empty.
- Fails at **import** of `config` with clear `RuntimeError` message (no auto-generated secrets).

### 2. Simulation endpoint gating

- `POST /drivers/simulate-ride` requires `HALFAPP_ENABLE_RIDE_SIMULATION=1` (or `true`/`yes`).
- **Default:** disabled in all environments unless flag set.
- **403** with stable body:

```json
{
  "detail": "Ride simulation is disabled in this environment",
  "truth_status": "simulation_disabled",
  "code": "SIMULATION_DISABLED"
}
```

- Pytest and Playwright backends set `HALFAPP_ENABLE_RIDE_SIMULATION=1` explicitly.

### 3. CORS tightening

- Wildcard origins (`*` or `https://x.com/*`) rejected at boot.
- **Production:** `CORS_ORIGINS` must list at least one explicit origin; no localhost union.
- **Development/test:** unions configured origins with localhost Vite/Playwright ports (3020–3034).

### 4. Token policy sketch

- `docs/HALFAPP_TOKEN_POLICY_SKETCH_01.md` — current JWT, no revocation claim.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `HALFAPP_ENV` | `development` \| `test` \| `production` |
| `SECRET_KEY` | JWT signing secret |
| `CORS_ORIGINS` | Comma-separated allowed browser origins |
| `HALFAPP_ENABLE_RIDE_SIMULATION` | `1` to allow `POST /drivers/simulate-ride` |

---

## Verification

```powershell
cd backend
python -m pytest tests/test_production_guards.py -q
python -m pytest -q
```

---

## Not in scope

- Payments, payouts, route snapshots, dossier UI wiring, OSRM runtime GO claims, token revocation implementation.

---

## Next task

- `HALFAPP_TRUST_E2E_STABILITY_REPAIR_01` if trust lane still flaky  
- Else `HALFAPP_ROUTE_SNAPSHOTS_FOUNDATION_01`
