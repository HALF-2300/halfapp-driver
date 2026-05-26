# Self-Hosted Routing Proof v0.3 — P0-G2

**Task:** P0-G2  
**Date:** 2026-05-25  
**STATUS:** **NO_GO** (runtime) · **GO** (code path + proof script)

## COMMAND RUN

```powershell
py -3.11 scripts/prove_osrm_runtime.py
# Exit 2 — OSRM not listening (expected on host without Docker/data)

cd backend
py -3.11 -m pytest tests/test_osrm_self_hosted_routing.py tests/test_ride_route_grounding.py -q
# passed (mocked)

OSRM_BASE_URL=http://127.0.0.1:5000 py -3.11 -m pytest tests/test_routing_service_real_osrm.py -q
# skipped without reachable OSRM
```

## PROOF

| Check | Result |
|-------|--------|
| `scripts/prove_osrm_runtime.py` | Added — 3 PDX pairs; prints `GO: used_fallback=false provider=osrm_self_hosted` on success |
| `docker-compose.yml` osrm service | Added (port 5000, `docker/osrm-portland/data`) |
| `tests/test_routing_service_real_osrm.py` | Added — skips unless OSRM reachable |
| Haversine fallback preserved | `ROUTING_FALLBACK_ENABLED` unchanged |
| Runtime on proof host | **BLOCKED** — connection refused `:5000` |

## Operator close to GO

```powershell
cd docker/osrm-portland
# prepare-data once — see README
docker compose up -d
cd ../..
py -3.11 scripts/prove_osrm_runtime.py
```

Expected: exit **0**, three lines `[OK]` with `used_fallback=False`.

## DOCS UPDATED

- `scripts/prove_osrm_runtime.py`
- `docker-compose.yml`
- `backend/tests/test_routing_service_real_osrm.py`
- `docs/SELF_HOSTED_ROUTING_PROOF_V0_3_REPORT.md`

## NEXT TASK

**BLOCKED:** Start OSRM container with prepared extract, then re-run proof script.
