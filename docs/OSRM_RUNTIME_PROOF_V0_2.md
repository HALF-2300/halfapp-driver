# OSRM Runtime Proof v0.2 — Portland / Oregon (P0)

**Document ID:** `OSRM_RUNTIME_PROOF_V0_2`  
**Date:** 2026-05-24  
**Depends on:** Agent 1 — `infra/staging/staging.env` + `ssh staging docker ps`  
**Image:** `osrm/osrm-backend` (car profile, MLD)  
**Compose:** `docker/osrm-portland/docker-compose.yml` + `infra/staging/docker/osrm-localhost.override.yml` (`restart: always`, `127.0.0.1:5000`)

## Verdict

| Check | Status |
|-------|--------|
| Oregon PBF download + extract/partition/customize on VPS | **BLOCKED** — no `staging.env` / VPS not provisioned in this session |
| `osrm-routed` via docker compose | **BLOCKED** |
| Acceptance curl (HTTP 200, `routes[0].geometry`) | **BLOCKED** |
| **P0 OSRM runtime** | **NO_GO** until evidence file is produced on VPS |

**Unblock:** set `HCLOUD_TOKEN`, run `bash infra/staging/scripts/provision-hetzner.sh`, then on the VPS `bash infra/staging/scripts/prepare-osrm-oregon.sh` (preferred) or `bash infra/staging/scripts/run-osrm-remote.sh` from laptop. Paste timings and curl output into `docs/SELF_HOSTED_ROUTING_PROOF_V0_2_STATUS.md` and change verdict to **GO**.

---

## Host environment (this session)

| Check | Result |
|-------|--------|
| Operator OS | Windows 10 (`win32 10.0.26200`) |
| `docker` on laptop | **Not on PATH** |
| `infra/staging/staging.env` | **Missing** (Agent 1 provision not completed) |
| `HCLOUD_TOKEN` | **Not set** |
| SSH key | `~/.ssh/halfapp_staging_ed25519` present |

---

## Prerequisites (VPS)

1. Agent 1 complete — Docker, compose plugin, UFW (22/80/443; OSRM **not** public).
2. Repo on VPS at `/opt/halfapp/halfapp-driver` **or** use `run-osrm-remote.sh` (rsync + remote deploy).
3. Disk: ~2–4 GB free for PBF + processed `.osrm` files.
4. RAM: CX22 (4 GB) sufficient for Oregon extract; first prep is CPU-heavy.

---

## Runbook — exact commands (run on VPS as `halfapp`)

### Preferred — one script (volume + self-test)

```bash
HALFAPP_REPO=/opt/halfapp/halfapp-driver \
  bash infra/staging/scripts/prepare-osrm-oregon.sh
```

Writes PBF/processed files under `/var/lib/halfapp/osrm-data`, copies into Docker volume `halfapp-osrm-data`, starts `infra/staging/docker-compose.yml` (`halfapp-osrm`, **127.0.0.1:5000**), and curls three Portland sample routes. On success prints `OSRM runtime: GO` — then update `docs/SELF_HOSTED_ROUTING_PROOF_V0_2_STATUS.md`.

### Alternate — repo-local `docker/osrm-portland/data`

### 0. Confirm Docker

```bash
docker info
docker compose version
```

### 1. Data directory

```bash
cd /opt/halfapp/halfapp-driver/docker/osrm-portland
mkdir -p data
```

### 2. One-shot prep + route (timed)

From `docker/osrm-portland/`:

```bash
export OSRM_IMAGE=osrm/osrm-backend
bash prepare-data.sh
```

`prepare-data.sh` logs step durations to `data/prepare-timing.log` (`STEP_*_SECONDS`).

**Manual steps (equivalent):**

```bash
cd /opt/halfapp/halfapp-driver/docker/osrm-portland
export OSRM_IMAGE=osrm/osrm-backend

# Download Oregon PBF
time curl -L -o data/oregon-latest.osm.pbf \
  https://download.geofabrik.de/north-america/us/oregon-latest.osm.pbf

# Extract (car profile)
time docker run --rm -t -v "${PWD}/data:/data" "$OSRM_IMAGE" \
  osrm-extract -p /opt/car.lua /data/oregon-latest.osm.pbf

# Partition (MLD)
time docker run --rm -t -v "${PWD}/data:/data" "$OSRM_IMAGE" \
  osrm-partition /data/oregon-latest.osrm

# Customize (MLD)
time docker run --rm -t -v "${PWD}/data:/data" "$OSRM_IMAGE" \
  osrm-customize /data/oregon-latest.osrm
```

### 3. Start `osrm-routed` (restart always, localhost only)

From repo root on VPS:

```bash
cd /opt/halfapp/halfapp-driver
docker compose \
  -f docker/osrm-portland/docker-compose.yml \
  -f infra/staging/docker/osrm-localhost.override.yml \
  up -d
docker compose -f docker/osrm-portland/docker-compose.yml ps
```

Or:

```bash
HALFAPP_REPO=/opt/halfapp/halfapp-driver \
  bash infra/staging/scripts/deploy-osrm-vps.sh
```

### 4. Acceptance test (mandatory)

From the **VPS**:

```bash
curl -sS -w '\nHTTP_CODE:%{http_code}\n' \
  'http://localhost:5000/route/v1/driving/-122.6765,45.5152;-122.5968,45.5887?overview=full'
```

**GO criteria:**

- HTTP **200**
- JSON `"code":"Ok"`
- `routes` array non-empty
- `routes[0].geometry` present (polyline with `overview=full`)

Quick check:

```bash
curl -fsS 'http://localhost:5000/route/v1/driving/-122.6765,45.5152;-122.5968,45.5887?overview=full' \
  | python3 -c "import json,sys; j=json.load(sys.stdin); r=j['routes'][0]; assert 'geometry' in r; print('OK', r['distance'], 'm')"
```

---

## Step timings (fill after VPS run)

Copy from `docker/osrm-portland/data/prepare-timing.log` or `docs/OSRM_RUNTIME_PROOF_V0_2_EVIDENCE.txt`.

| Step | Duration (seconds) | Notes |
|------|-------------------|--------|
| `download_pbf` | _pending_ | Geofabrik `oregon-latest.osm.pbf` |
| `extract` | _pending_ | `osrm-extract -p /opt/car.lua` |
| `partition` | _pending_ | MLD |
| `customize` | _pending_ | MLD |
| `docker compose up -d` | _pending_ | `restart: always` |

**Typical ranges (Linux CX22, first run):** download 1–5 min; extract 5–20 min; partition 1–5 min; customize 1–5 min. Varies with CPU and disk.

---

## Acceptance curl output (fill after VPS run)

_Pending — run acceptance curl on VPS and paste JSON excerpt here._

Expected shape:

```json
{
  "code": "Ok",
  "routes": [
    {
      "distance": <number>,
      "duration": <number>,
      "geometry": "<encoded polyline>"
    }
  ],
  "waypoints": [ ... ]
}
```

---

## Remote deploy from laptop (Git Bash)

```bash
export HCLOUD_TOKEN='...'   # Agent 1 once
bash infra/staging/scripts/provision-hetzner.sh

bash infra/staging/scripts/run-osrm-remote.sh
scp -i ~/.ssh/halfapp_staging_ed25519 \
  halfapp@$VPS_IP:/opt/halfapp/halfapp-driver/docs/OSRM_RUNTIME_PROOF_V0_2_EVIDENCE.txt \
  docs/
```

---

## After runtime GO (HalfApp backend)

Per `docs/RUNTIME_PROOF_PROCEDURE.md`:

```bash
export OSRM_BASE_URL=http://127.0.0.1:5000   # on VPS or SSH tunnel
bash scripts/osrm_healthcheck.sh
cd backend
export ROUTING_PROVIDER=osrm_self_hosted
python scripts/verify_osrm_health.py
python scripts/proof_osrm_portland_routes.py --strict --snapshot-proof --write-evidence
```

Update `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` when evidence is valid.

---

## Files touched (Agent 2)

| Path | Role |
|------|------|
| `docker/osrm-portland/docker-compose.yml` | `osrm/osrm-backend`, `restart: always` |
| `docker/osrm-portland/prepare-data.sh` | Timed download + MLD pipeline |
| `infra/staging/scripts/deploy-osrm-vps.sh` | VPS deploy + acceptance + evidence file |
| `infra/staging/scripts/run-osrm-remote.sh` | Rsync + remote deploy from laptop |
| `infra/staging/docker/osrm-localhost.override.yml` | Bind OSRM to localhost |

---

## P0 closure checklist

- [ ] `staging.env` exists; `ssh staging docker ps` works  
- [ ] `prepare-timing.log` recorded on VPS  
- [ ] `docker compose ps` shows `halfapp-osrm-portland` up  
- [ ] Acceptance curl HTTP 200 + `routes[0].geometry`  
- [ ] This doc updated to **GO** with real timings and curl excerpt  
- [ ] `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` runtime row → **GO**
