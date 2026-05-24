# Self-Hosted Routing Proof v0.1 — Report

## Verdict: **PARTIAL_GO** (runtime flip blocked)

**Status code:** `BLOCKED_RUNTIME_DOCKER_UNAVAILABLE`

Code/tests remain **GO**. Runtime proof flip to **GO** was attempted on 2026-05-22: Docker client 29.4.0 is installed (`C:\Program Files\Docker\Docker\resources\bin\docker.exe`) but the Docker daemon never became reachable (`npipe:////./pipe/docker_engine` missing after starting Docker Desktop and polling 120s). OSRM on `127.0.0.1:5000` is not running; proof script used **haversine_fallback** for all three routes.

OSRM self-hosted routing is wired end-to-end in the backend (provider abstraction, env flags, haversine fallback, ride create + pricing handoff, tests). **GO** for code and tests; **PARTIAL** until a Docker-capable host runs OSRM with the Oregon extract and proof script returns `route_provider=osrm_self_hosted` (not `haversine_fallback`) for the three Portland metro routes.

---

## Engine chosen: **OSRM** (`osrm_self_hosted`)

| Criterion | OSRM | Valhalla |
| --- | --- | --- |
| Point-to-point car `route` API | Single HTTP GET | Heavier multi-tile setup |
| Docker proof footprint | One `osrm-routed` service | Not wired in v0.1 |
| Fit with existing stack | `httpx` + env URL | Would add second engine path |

Valhalla is explicitly rejected in v0.1 (`routing_service` raises if `ROUTING_PROVIDER=valhalla_self_hosted`).

---

## Files changed / added

| Path | Role |
| --- | --- |
| `backend/services/osrm_self_hosted_provider.py` | OSRM HTTP client + response parsing |
| `backend/services/routing_service.py` | Provider interface: `route`, `estimate_distance_miles`, `estimate_duration_minutes`, fallback |
| `backend/services/map_route_foundation.py` | Stamps route metadata on `Ride` |
| `backend/routes/rider_rides.py` | Ride create calls routing → pricing quote |
| `backend/config.py`, `backend/.env.example` | Env flags |
| `docker/osrm-portland/` | Docker Compose + README for Oregon extract |
| `backend/scripts/proof_osrm_portland_routes.py` | Local proof routes (PDX, Beaverton, Gresham; Vancouver optional) |
| `backend/tests/test_osrm_self_hosted_routing.py` | Parsing, pricing, fallback, no Google/Mapbox HTTP |
| `backend/tests/test_routing_service.py` | No paid providers by default |
| `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_REPORT.md` | This report |

---

## How to run local OSRM

From `docker/osrm-portland/` (one-time extract — see `README.md`):

```bash
mkdir -p data
cd data && curl -L -o oregon-latest.osm.pbf https://download.geofabrik.de/north-america/us/oregon-latest.osm.pbf
cd ..
docker run -t -v "${PWD}/data:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/oregon-latest.osm.pbf
docker run -t -v "${PWD}/data:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/oregon-latest.osrm
docker run -t -v "${PWD}/data:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/oregon-latest.osrm
docker compose up -d
```

Backend env:

```env
ROUTING_PROVIDER=osrm_self_hosted
OSRM_BASE_URL=http://127.0.0.1:5000
ROUTING_FALLBACK_ENABLED=true
TRAFFIC_PROVIDER=none
GOOGLE_MAPS_FALLBACK_ENABLED=false
MAPBOX_TRAFFIC_ENABLED=false
```

Proof script:

```bash
cd backend
python scripts/proof_osrm_portland_routes.py
# optional: PROOF_INCLUDE_VANCOUVER_WA=true python scripts/proof_osrm_portland_routes.py
```

---

## Env flags (verified)

| Variable | Default | Purpose |
| --- | --- | --- |
| `ROUTING_PROVIDER` | `osrm_self_hosted` | Active engine |
| `OSRM_BASE_URL` | `http://127.0.0.1:5000` | OSRM HTTP base |
| `ROUTING_FALLBACK_ENABLED` | `true` | Haversine when OSRM down |
| `TRAFFIC_PROVIDER` | `none` | No paid traffic |
| `GOOGLE_MAPS_FALLBACK_ENABLED` | `false` | No Google routing API |
| `MAPBOX_TRAFFIC_ENABLED` | `false` | No Mapbox traffic |

---

## Fallback behavior

When OSRM is unreachable and `ROUTING_FALLBACK_ENABLED=true`:

- `route_provider` = `haversine_fallback`
- `route_confidence` = `low`
- `traffic_provider` = `none`, `traffic_aware` = `false`
- `used_fallback` = `true`

When `ROUTING_FALLBACK_ENABLED=false`, routing raises instead of silently upgrading confidence.

---

## Pricing integration

On `POST /rides/` with coordinates:

1. `routing_service.route()` → distance/duration + route metadata on `Ride`
2. `quote_ride_pricing(distance_km, duration_minutes)` — **pricing math unchanged** (80/20, $1.50 platform fee, tips/pass-through separate)

Route metadata is on the ride record and API view (`route_provider`, `traffic_provider`, `traffic_aware`, `route_confidence`, `route_calculated_at`).

---

## No paid Google / Mapbox routing APIs

- OSRM client only calls `OSRM_BASE_URL` (`/route/v1/driving/...`).
- `GOOGLE_MAPS_FALLBACK_ENABLED` / `MAPBOX_TRAFFIC_ENABLED` raise if set true in routing path.
- Driver app **external** Google Maps dir links unchanged (navigation only, not embed/API).
- Tests assert URLs do not contain `google` or `mapbox`.

---

## Blockers

1. **OSRM container + Oregon PBF prep** not automated in CI; proof on a fresh machine requires Docker extract steps (~minutes + disk).
2. **Driver-app map** still uses client haversine for display polyline (`mapProvider.js`); backend authority is on ride create — MapLibre migration out of scope.
3. **Cross-border Vancouver** route is opt-in via `PROOF_INCLUDE_VANCOUVER_WA` only.

---

## Commands run (this session)

### Backend tests

```
cd backend
python -m pytest tests/test_osrm_self_hosted_routing.py tests/test_routing_service.py tests/test_pricing_ledger_v01.py tests/test_v01_foundation.py tests/test_ride_flow_ui_proof.py -q
28 passed in 12.82s
```

### Proof script (OSRM not running locally — fallback)

```
cd backend
python scripts/proof_osrm_portland_routes.py
```

Sample output (haversine fallback while `127.0.0.1:5000` unreachable):

| Route | route_provider | distance_km | duration_min | confidence |
| --- | --- | ---: | ---: | --- |
| PDX → Downtown | haversine_fallback | 13.162 | 26 | low |
| Downtown → Beaverton | haversine_fallback | 12.816 | 26 | low |
| Downtown → Gresham | haversine_fallback | 24.268 | 49 | low |

With OSRM up, expect `route_provider=osrm_self_hosted`, `route_confidence=medium`, `used_fallback=false`, and road-network distances (typically shorter than straight-line × 1.25).

### ROUTING_GO_FLIP attempt (2026-05-22)

- Docker client found; daemon **not** reachable after `Docker Desktop.exe` + 120s poll.
- `docker/osrm-portland/data/` — no Oregon extract prepared yet.
- Proof script: all three routes → `haversine_fallback`, `used_fallback=true`.

### Docker-capable host — exact commands to reach **GO**

Run on a machine/VPS where `docker info` succeeds:

```bash
cd docker/osrm-portland
mkdir -p data
cd data
curl -L -o oregon-latest.osm.pbf https://download.geofabrik.de/north-america/us/oregon-latest.osm.pbf
cd ..
docker run -t -v "${PWD}/data:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/oregon-latest.osm.pbf
docker run -t -v "${PWD}/data:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/oregon-latest.osrm
docker run -t -v "${PWD}/data:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/oregon-latest.osrm
docker compose up -d
curl "http://127.0.0.1:5000/route/v1/driving/-122.5951,45.5898;-122.6784,45.5152?overview=false"

cd ../../backend
export ROUTING_PROVIDER=osrm_self_hosted
export OSRM_BASE_URL=http://127.0.0.1:5000
export ROUTING_FALLBACK_ENABLED=true
python scripts/proof_osrm_portland_routes.py
```

**GO criteria:** each of PDX→Downtown, Downtown→Beaverton, Downtown→Gresham prints `route_provider=osrm_self_hosted`, `route_confidence=medium`, `used_fallback=false`.

Windows (Docker Desktop running, `docker` on PATH):

```powershell
cd docker\osrm-portland
# same extract/partition/customize/compose steps using docker.exe full path if needed
cd ..\..\backend
python scripts\proof_osrm_portland_routes.py
```
