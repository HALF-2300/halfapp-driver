# SELF_HOSTED_ROUTING_PROOF_V0_1 — Status (frozen)

**Date:** 2026-05-22 (re-checked for `HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01`)  
**Lane:** Infrastructure/runtime only — runtime GO requires Docker-capable host + Oregon OSRM data.

**Superseded for runtime tracking by:** `docs/SELF_HOSTED_ROUTING_PROOF_V0_2_STATUS.md` (staging script `infra/staging/scripts/prepare-osrm-oregon.sh`).

**Latest runtime attempt:** `docs/OSRM_RUNTIME_PROOF_V0_2.md` — **NO_GO** / `BLOCKED_NO_STAGING_VPS` (2026-05-24; no `infra/staging/staging.env`, laptop has no Docker). Prior: `docs/HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01_REPORT.md`.

## Verdict

| Layer | Status |
|--------|--------|
| Code path | **GO** |
| Runtime OSRM proof | **NO_GO** — `BLOCKED_RUNTIME_DOCKER_UNAVAILABLE` |

## Summary

```
SELF_HOSTED_ROUTING_PROOF_V0_1:
  Code:    GO
  Runtime: NO_GO
  Block:   Docker daemon unavailable; nothing on http://127.0.0.1:5000
```

- Implementation accepted (OSRM provider, honest `haversine_fallback`, tests).
- Proof script `backend/scripts/proof_osrm_portland_routes.py` ran; all three Portland legs returned `haversine_fallback` because OSRM was unreachable.
- Unit tests (`tests/test_osrm_self_hosted_routing.py`) pass with mocked OSRM.

## Blocker

- `docker info` / `docker ps` fail: Docker API pipe not available on Windows dev machine.
- OSRM container not started; port 5000 not listening.

## Runtime proof order (mandatory for agents)

See **`docs/RUNTIME_PROOF_PROCEDURE.md`**. Summary:

1. `docker info` (+ confirm `data/` has processed OSRM files)
2. `docker compose up -d` and wait for healthy container
3. `curl` OSRM route URL — must return `"code":"Ok"`
4. **Only then** `python scripts/verify_osrm_health.py` (must print `OSRM_HEALTH_OK`)
5. **Then** `python scripts/proof_osrm_portland_routes.py --strict --snapshot-proof --write-evidence`

If step 1 or 3 fails: report **`BLOCKED_DEPENDENCY_NOT_RUNNING`** and **do not** run the proof script (fallback-only output is not valid runtime proof).

## Next action (infrastructure only)

1. **Option A:** Fix Docker Desktop locally, then follow `docker/osrm-portland/README.md`.
2. **Option B (preferred):** `docs/OSRM_RUNTIME_PROOF_V0_2.md` — provision VPS (Agent 1), then `bash infra/staging/scripts/run-osrm-remote.sh`.

Follow `RUNTIME_PROOF_PROCEDURE.md` end-to-end before claiming runtime GO.

**GO runtime condition:** PDX→Downtown, Downtown→Beaverton, Downtown→Gresham each show `route_provider=osrm_self_hosted`, `used_fallback=False`, `traffic_provider=none`, `traffic_aware=false`.

## Out of scope until runtime GO

- Pricing, routing, map, Google/Mapbox, payments, insurance, compliance changes on this lane.

## Windows note (docs only)

PowerShell: prefer `New-Item -ItemType Directory -Force data` over `mkdir -p data` in `docker/osrm-portland/`.
