# Self-Hosted Routing Proof v0.3 — P0-G2

**Task:** P0-G2  
**Date:** 2026-05-25  
**STATUS:** **GO** (runtime + code path)

This report is aligned with `docs/P0_G2_OSRM_RUNTIME_PROOF_01.md`.

## Command Run

```powershell
cd C:\Users\him\Desktop\halfapp-driver
py -3.11 scripts\prove_osrm_runtime.py
```

Result:

```text
GO: used_fallback=false provider=osrm_self_hosted (3 PDX routes)
```

Detailed route evidence:

```text
[OK] Downtown -> PDX: provider=osrm_self_hosted used_fallback=False distance_km=20.189 duration_min=22
[OK] Pearl -> Hawthorne: provider=osrm_self_hosted used_fallback=False distance_km=4.817 duration_min=10
[OK] OHSU -> Downtown: provider=osrm_self_hosted used_fallback=False distance_km=3.695 duration_min=9
```

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

## Proof

| Check | Result |
|-------|--------|
| `scripts/prove_osrm_runtime.py` | **GO** — 3 PDX pairs returned `provider=osrm_self_hosted`, `used_fallback=False` |
| `docker/osrm-portland/data` | **Prepared** — Oregon `.osrm` extract files present |
| `tests/test_routing_service_real_osrm.py` | **GO** — ran against reachable `OSRM_BASE_URL`, did not skip |
| Haversine fallback preserved | `ROUTING_FALLBACK_ENABLED` unchanged |
| Runtime on proof host | **GO** — `http://127.0.0.1:5000` reachable |

## Reproduce

```powershell
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
cd C:\Users\him\Desktop\halfapp-driver
py -3.11 scripts\prove_osrm_runtime.py
```

Expected: exit **0**, three lines `[OK]` with `used_fallback=False`, and final line:

```text
GO: used_fallback=false provider=osrm_self_hosted (3 PDX routes)
```

## Docs Updated

- `scripts/prove_osrm_runtime.py`
- `docker-compose.yml`
- `backend/tests/test_routing_service_real_osrm.py`
- `docs/P0_G2_OSRM_RUNTIME_PROOF_01.md`
- `docs/SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md`
- `docs/CURRENT_TRUTH.md`

## Next Task

G3 owner courier day remains human-only. Agents must not mark G3 GO.
