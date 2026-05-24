# OSRM self-hosted routing — Portland metro proof (v0.1)

HalfApp uses **OSRM** (not Valhalla) for the v0.1 proof: single HTTP `route` endpoint, minimal ops, and a direct fit for point-to-point car estimates fed into the pricing ledger.

## Prerequisites

- Docker
- ~500MB+ disk for Oregon extract (covers Portland metro)

## One-time data prep

From this directory (`docker/osrm-portland/`):

```bash
bash prepare-data.sh
```

Manual equivalent (image `osrm/osrm-backend`, car profile):

```bash
mkdir -p data
curl -L -o data/oregon-latest.osm.pbf https://download.geofabrik.de/north-america/us/oregon-latest.osm.pbf
docker run --rm -t -v "${PWD}/data:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/oregon-latest.osm.pbf
docker run --rm -t -v "${PWD}/data:/data" osrm/osrm-backend osrm-partition /data/oregon-latest.osrm
docker run --rm -t -v "${PWD}/data:/data" osrm/osrm-backend osrm-customize /data/oregon-latest.osrm
```

VPS one-shot: `bash ../../infra/staging/scripts/deploy-osrm-vps.sh` — see `docs/OSRM_RUNTIME_PROOF_V0_2.md`.

## Run OSRM

**Order matters** — see `docs/RUNTIME_PROOF_PROCEDURE.md`.

1. Confirm Docker daemon: `docker info`
2. Confirm `data/` is not empty (processed `.osrm` files exist after prep)
3. Start service:

```bash
docker compose up -d
```

4. Health check (must succeed before HalfApp proof script):

```bash
export OSRM_BASE_URL=http://127.0.0.1:5000
bash ../../scripts/osrm_healthcheck.sh
```

Windows (from repo root):

```powershell
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
powershell -ExecutionPolicy Bypass -File scripts\osrm_healthcheck.ps1
```

Or manual curl:

```bash
curl "http://127.0.0.1:5000/route/v1/driving/-122.5951,45.5898;-122.6784,45.5152?overview=false"
```

Expect HTTP 200 and JSON `"code":"Ok"`. If not → `BLOCKED_DEPENDENCY_NOT_RUNNING`; do not run the proof script yet.

`docker compose` also runs an in-container healthcheck on the same Route API (see `healthcheck` in `docker-compose.yml`). If the container stays unhealthy but host scripts pass, the image may lack `curl`/`grep` — rely on host scripts from `docs/HALFAPP_OSRM_OPS_ONLY_SLICE_05.md`.

### Windows (PowerShell)

```powershell
New-Item -ItemType Directory -Force data
```

## Backend env

```env
ROUTING_PROVIDER=osrm_self_hosted
OSRM_BASE_URL=http://127.0.0.1:5000
ROUTING_FALLBACK_ENABLED=true
TRAFFIC_PROVIDER=none
```

## Proof script (step 4 only — after curl health check passes)

```bash
cd backend
python scripts/proof_osrm_portland_routes.py
```

Vancouver WA route in the script is **test-only**; not enabled for production launch.
