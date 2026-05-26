# P0-G2 — OSRM Runtime Proof Report

**Task:** P0-G2  
**Date:** 2026-05-25  
**STATUS:** **NO_GO** (runtime on agent host) · **GO** (code path + harness)

**Calibration (owner):** G2 does **not** depend on G7 (Alembic-on-PG). G7 is a separate gate for staging deployment schema truth.

---

## Standard report

```
TASK: P0-G2
STATUS: NO_GO (runtime) | GO (code + script)
COMMAND RUN:
  py -3.11 scripts/prove_osrm_runtime.py
  cd backend && py -3.11 -m pytest tests/test_osrm_self_hosted_routing.py tests/test_routing_service_real_osrm.py -q
PROOF:
  prove_osrm_runtime.py → exit 1, WinError 10061 (nothing on :5000)
  Backend mocked routing → 6 passed, 1 skipped (test_routing_service_real_osrm skips without OSRM)
  docker/osrm-portland/data/ → empty (no prepared .osrm extract on this machine)
  docker CLI → not in PATH on proof host
DOCS UPDATED:
  docs/P0_G2_OSRM_RUNTIME_PROOF_01.md (this file)
  docs/SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md (prior pass — superseded for G2 status by this report)
GOVERNANCE CHECK: N/A (no product copy changes)
NEXT TASK: BLOCKED until owner runs steps below. G7 not started per owner order.
```

---

## COMMAND RUN (literal output)

### `scripts/prove_osrm_runtime.py`

```text
HALFAPP prove_osrm_runtime — OSRM_BASE_URL=http://127.0.0.1:5000
BLOCKED: OSRM not listening — [WinError 10061] No connection could be made because the target machine actively refused it
Start: cd docker/osrm-portland && docker compose up -d
exit code: 1
```

**Acceptance not met:** exit **0** with `GO: used_fallback=false provider=osrm_self_hosted (3 PDX routes)`.

### Backend tests (code path)

```powershell
cd backend
py -3.11 -m pytest tests/test_osrm_self_hosted_routing.py tests/test_routing_service_real_osrm.py -q
```

```text
6 passed, 1 skipped, 4 warnings in 4.64s
```

Skipped: `test_routing_service_real_osrm_no_fallback` (no reachable `OSRM_BASE_URL`).

### Docker / data preflight (this host)

| Check | Result |
|-------|--------|
| `docker` in PATH | **FAIL** — command not found |
| `docker/osrm-portland/data/` | **Empty** — `prepare-data.sh` not run here |
| `docker compose up -d osrm` | **Not executed** — blocked on Docker + data |

---

## Owner steps to close G2 → **GO**

```powershell
# 1. Install Docker; ensure daemon running
docker info

# 2. One-time OSRM data (large download — see docker/osrm-portland/README.md)
cd docker/osrm-portland
bash prepare-data.sh   # or manual steps in README

# 3. Start OSRM (repo root or osrm-portland)
docker compose up -d osrm
# Or: cd docker/osrm-portland && docker compose up -d

# 4. Health check
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
powershell -ExecutionPolicy Bypass -File scripts\osrm_healthcheck.ps1

# 5. Runtime proof (must exit 0)
cd <repo-root>
py -3.11 scripts/prove_osrm_runtime.py

# 6. Optional integration test
cd backend
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
py -3.11 -m pytest tests/test_routing_service_real_osrm.py -q
```

**Expected success lines:**

```text
  [OK] Downtown → PDX: provider=osrm_self_hosted used_fallback=False ...
  [OK] Pearl → Hawthorne: ...
  [OK] OHSU → Downtown: ...
GO: used_fallback=false provider=osrm_self_hosted (3 PDX routes)
```

Then update this report **STATUS** to **GO** and `docs/CURRENT_TRUTH.md` G2 row.

---

## Scaffold already in repo (agent pass)

| Artifact | Path |
|----------|------|
| Proof script | `scripts/prove_osrm_runtime.py` |
| Root compose OSRM service | `docker-compose.yml` → `osrm` on `:5000` |
| Real OSRM pytest | `backend/tests/test_routing_service_real_osrm.py` |
| Haversine fallback | Unchanged — honest when OSRM down |

---

## Honesty when OSRM is down

With `ROUTING_FALLBACK_ENABLED=true`, rides must show `route_provider=haversine_fallback` and `used_fallback=true`. Do not claim road-network routing without G2 **GO**.

---

## Related gates (not started)

| Gate | Status |
|------|--------|
| G7 Alembic PG compatibility | **NOT STARTED** — owner added; blocks staging deploy claims only |
| P1.1+ | **NOT STARTED** |
| G3 owner courier day | **PENDING_OWNER** |
