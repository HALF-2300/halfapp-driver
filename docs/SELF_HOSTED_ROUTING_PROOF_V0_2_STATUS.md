# Self-Hosted Routing Proof v0.2 — STATUS: BLOCKED (staging VPS)

**Date:** 2026-05-24  
**Environment:** staging VPS (Hetzner CX22, Frankfurt) — **not provisioned in this workspace**  
**OSRM version:** `osrm/osrm-backend` (car profile, MLD)  
**Data:** Oregon OSM extract from Geofabrik (`oregon-latest.osm.pbf`)  
**Profile:** car.lua (default)

## Blocker

| Check | Result |
|-------|--------|
| `infra/staging/staging.env` `VPS_IP` | `0.0.0.0` / `PROVISION_PENDING` |
| `ssh halfapp@staging` | Host not resolved |
| Docker on dev laptop | Not installed |
| `HCLOUD_TOKEN` | Not set |

**Unblock:** `export HCLOUD_TOKEN=... && bash infra/staging/scripts/provision-hetzner.sh`, then on VPS:

```bash
cd /opt/halfapp/halfapp-driver
./infra/staging/osrm/prepare_osrm.sh
```

Paste route log lines and `LATENCY|p50_ms=...|p95_ms=...` from that script into the tables below, set verdict to **GO**, and update `docs/CURRENT_TRUTH.md` (`OSRM runtime` → **GO v0.2**).

## Verification (pending live run)

### 1. OSRM healthcheck

```bash
docker exec halfapp-osrm-portland wget -q --spider \
  "http://localhost:5000/route/v1/driving/-122.6765,45.5152;-122.5968,45.5887?overview=false"
echo $?
# Expected: 0
```

### 2. Three Portland routes

| Route | Code | Distance (m) | Duration (s) | Provider stamped |
|-------|------|--------------|--------------|------------------|
| PDX downtown → airport | _pending_ | _pending_ | _pending_ | `osrm_self_hosted` |
| Pearl District → OHSU | _pending_ | _pending_ | _pending_ | `osrm_self_hosted` |
| Hawthorne → Airport | _pending_ | _pending_ | _pending_ | `osrm_self_hosted` |

### 3. Latency

Measured p50/p95 over 100 requests from API container to OSRM container:

- p50: _pending_ ms
- p95: _pending_ ms

(`prepare_osrm.sh` prints `LATENCY|p50_ms=...|p95_ms=...`.)

### 4. Integration test result

```bash
export OSRM_RUNTIME_URL=http://127.0.0.1:5000   # or nginx path on staging
cd backend && python -m pytest tests/test_osrm_runtime_integration.py -v
# Expected when OSRM is up: 4 passed
```

## Code readiness (verified in repo)

- `routing_service.py`: OSRM success → `route_provider=osrm_self_hosted`, `used_fallback=False`; failure → `haversine_fallback` + `used_fallback=True`.
- `route_snapshots`: stamps `used_fallback` from `RouteEstimate` via `_fields_from_estimate`.
- Integration test: `backend/tests/test_osrm_runtime_integration.py` (skipped without `OSRM_RUNTIME_URL`).
- VPS prep script: `infra/staging/osrm/prepare_osrm.sh`.

## Honesty contract (code audit)

- Success path stamps `route_provider="osrm_self_hosted"`, `used_fallback=false` on `RouteEstimate` and route snapshots created from estimates.
- Failure path stamps `route_provider="haversine_fallback"`, `used_fallback=true`.
- Runtime fallback-without-stamp test: run after `docker compose stop osrm` on VPS (manual).

## Verdict

OSRM runtime: **NO_GO** (blocked on VPS + Docker; code path ready)

When live proof completes, change to **GO** and link from `docs/CURRENT_TRUTH.md`.
