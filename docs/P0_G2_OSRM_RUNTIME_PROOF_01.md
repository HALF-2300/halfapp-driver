# P0-G2 — OSRM Runtime Proof Report

**Task:** P0-G2  
**Date:** 2026-05-25  
**STATUS:** **GO** (runtime proof + backend integration tests)

**Calibration:** G2 proves this host can route Portland jobs through self-hosted OSRM with `used_fallback=false`. It does not remove fallback honesty when OSRM is unavailable.

---

## Standard report

```
TASK: P0-G2
STATUS: GO
COMMAND RUN:
  py -3.11 scripts/prove_osrm_runtime.py
  cd backend && py -3.11 -m pytest tests/test_osrm_self_hosted_routing.py tests/test_routing_service_real_osrm.py -q
PROOF:
  prove_osrm_runtime.py -> exit 0, three PDX routes used provider=osrm_self_hosted and used_fallback=False
  Backend routing tests -> 7 passed, including real OSRM integration test
  docker/osrm-portland/data/ -> prepared Oregon OSRM extract present
DOCS UPDATED:
  docs/P0_G2_OSRM_RUNTIME_PROOF_01.md
  docs/SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md
  docs/CURRENT_TRUTH.md
GOVERNANCE CHECK: N/A (no product copy changes)
NEXT TASK: G3 owner courier day.
```

---

## Runtime proof

```powershell
cd C:\Users\him\Desktop\halfapp-driver
py -3.11 scripts\prove_osrm_runtime.py
```

Result:

```text
HALFAPP prove_osrm_runtime — OSRM_BASE_URL=http://127.0.0.1:5000
  [OK] Downtown -> PDX: provider=osrm_self_hosted used_fallback=False distance_km=20.189 duration_min=22
         osrm_raw: 20188.6m 1335.1s
  [OK] Pearl -> Hawthorne: provider=osrm_self_hosted used_fallback=False distance_km=4.817 duration_min=10
         osrm_raw: 4817.3m 616.2s
  [OK] OHSU -> Downtown: provider=osrm_self_hosted used_fallback=False distance_km=3.695 duration_min=9
         osrm_raw: 3694.6m 562.2s
GO: used_fallback=false provider=osrm_self_hosted (3 PDX routes)
```

**Acceptance met:** exit **0** with `GO: used_fallback=false provider=osrm_self_hosted (3 PDX routes)`.

---

## Backend tests

```powershell
cd C:\Users\him\Desktop\halfapp-driver\backend
$env:OSRM_BASE_URL='http://127.0.0.1:5000'
$env:ROUTING_PROVIDER='osrm_self_hosted'
$env:ROUTING_FALLBACK_ENABLED='true'
py -3.11 -m pytest -q tests/test_osrm_self_hosted_routing.py tests/test_routing_service_real_osrm.py
```

Result:

```text
7 passed, 4 warnings in 9.42s
```

The real OSRM integration test did not skip; `OSRM_BASE_URL=http://127.0.0.1:5000` was reachable.

---

## Host preflight

| Check | Result |
|-------|--------|
| `docker/osrm-portland/data/` | **Prepared** — Oregon `.osrm` extract files present |
| `OSRM_BASE_URL=http://127.0.0.1:5000` | **Reachable** — proof script and pytest both passed |
| Docker CLI | Full-path Docker CLI exists, but Docker Desktop API access is restricted in this session; not required for the proof because OSRM was already reachable |

---

## Reproduce G2

```powershell
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
cd C:\Users\him\Desktop\halfapp-driver
py -3.11 scripts\prove_osrm_runtime.py

cd backend
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
$env:ROUTING_PROVIDER = "osrm_self_hosted"
$env:ROUTING_FALLBACK_ENABLED = "true"
py -3.11 -m pytest tests/test_routing_service_real_osrm.py -q
```

Expected success line:

```text
GO: used_fallback=false provider=osrm_self_hosted (3 PDX routes)
```

---

## Scaffold already in repo

| Artifact | Path |
|----------|------|
| Proof script | `scripts/prove_osrm_runtime.py` |
| Root compose OSRM service | `docker-compose.yml` -> `osrm` on `:5000` |
| Real OSRM pytest | `backend/tests/test_routing_service_real_osrm.py` |
| Haversine fallback | Unchanged — honest when OSRM down |

---

## Honesty when OSRM is down

With `ROUTING_FALLBACK_ENABLED=true`, rides must still show `route_provider=haversine_fallback` and `used_fallback=true` when OSRM is down. G2 **GO** means this host proved the OSRM runtime path; it does not remove fallback honesty.

---

## Related gates

| Gate | Status |
|------|--------|
| G1 PostgreSQL claim-race | **GO** |
| G7 Alembic PG compatibility | **GO** |
| G3 owner courier day | **PENDING_OWNER** |
| P1.1+ | **NOT STARTED** |
