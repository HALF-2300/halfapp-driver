#!/usr/bin/env bash
# HalfApp Staging — OSRM Oregon extract → halfapp-osrm-data volume
# Prepares the routing graph from Oregon OSM data.
# Run as halfapp user on the staging VPS.
# Time: ~10-30 min depending on VPS CPU.
set -euo pipefail

HALFAPP_REPO="${HALFAPP_REPO:-/opt/halfapp/halfapp-driver}"
DATA_DIR="/var/lib/halfapp/osrm-data"
PBF_URL="https://download.geofabrik.de/north-america/us/oregon-latest.osm.pbf"
PBF_FILE="$DATA_DIR/oregon-latest.osm.pbf"
OSRM_IMAGE="osrm/osrm-backend:v5.27.1"
STAGING_COMPOSE="$HALFAPP_REPO/infra/staging/docker-compose.yml"
ACCEPT_URL='http://127.0.0.1:5000/route/v1/driving/-122.6765,45.5152;-122.5968,45.5887?overview=false'

log() { echo "[$(date -Iseconds)] $*"; }

# --- 1. Prepare data dir ---
sudo mkdir -p "$DATA_DIR"
sudo chown -R "$USER:$USER" "$DATA_DIR"
cd "$DATA_DIR"

# --- 2. Download PBF if missing or older than 14 days ---
NEEDS_DOWNLOAD=1
if [ -f "$PBF_FILE" ]; then
  AGE_DAYS=$(( ( $(date +%s) - $(stat -c %Y "$PBF_FILE") ) / 86400 ))
  if [ "$AGE_DAYS" -lt 14 ]; then
    log "PBF is $AGE_DAYS days old — reusing."
    NEEDS_DOWNLOAD=0
  fi
fi

if [ "$NEEDS_DOWNLOAD" -eq 1 ]; then
  log "Downloading Oregon PBF (~250MB)..."
  curl -fL -o "$PBF_FILE.tmp" "$PBF_URL"
  mv "$PBF_FILE.tmp" "$PBF_FILE"
fi

# --- 3. Extract car profile (~3-8 min) ---
log "Running osrm-extract..."
docker run --rm -v "$DATA_DIR:/data" "$OSRM_IMAGE" \
  osrm-extract -p /opt/car.lua /data/oregon-latest.osm.pbf

# --- 4. Partition (~2-5 min) ---
log "Running osrm-partition..."
docker run --rm -v "$DATA_DIR:/data" "$OSRM_IMAGE" \
  osrm-partition /data/oregon-latest.osrm

# --- 5. Customize (~1-3 min) ---
log "Running osrm-customize..."
docker run --rm -v "$DATA_DIR:/data" "$OSRM_IMAGE" \
  osrm-customize /data/oregon-latest.osrm

# --- 6. Move into docker volume ---
log "Copying into halfapp-osrm-data volume..."
docker volume create halfapp-osrm-data >/dev/null
docker run --rm \
  -v "$DATA_DIR:/src:ro" \
  -v halfapp-osrm-data:/dst \
  "$OSRM_IMAGE" \
  sh -c "cp /src/oregon-latest.osrm* /dst/"

# --- 7. Boot OSRM and self-test ---
if [[ ! -f "$STAGING_COMPOSE" ]]; then
  echo "Missing $STAGING_COMPOSE — clone repo to $HALFAPP_REPO first." >&2
  exit 1
fi

log "Starting OSRM container..."
cd "$HALFAPP_REPO/infra/staging"
docker compose -f docker-compose.yml up -d osrm-routed

log "Waiting for OSRM to become healthy..."
for i in $(seq 1 30); do
  if curl -fsS --max-time 5 "$ACCEPT_URL" >/dev/null 2>&1; then
    log "OSRM healthy."
    break
  fi
  if [ "$i" -eq 30 ]; then
    log "OSRM did not become healthy within 60s." >&2
    docker compose -f docker-compose.yml ps >&2 || true
    exit 1
  fi
  sleep 2
done

log ""
log "=== OSRM RUNTIME PROOF ==="
log ""

declare -a ROUTES=(
  "PDX_to_Downtown:-122.5968,45.5887;-122.6765,45.5152"
  "Pearl_to_OHSU:-122.6829,45.5288;-122.6862,45.4994"
  "Hawthorne_to_Airport:-122.6543,45.5125;-122.5968,45.5887"
)

for r in "${ROUTES[@]}"; do
  NAME="${r%%:*}"
  COORDS="${r#*:}"
  log "Route: $NAME"
  RESULT=$(curl -fsS "http://127.0.0.1:5000/route/v1/driving/$COORDS?overview=false")
  read -r CODE DIST DUR <<<"$(printf '%s' "$RESULT" | python3 -c "
import json, sys
j = json.load(sys.stdin)
r = (j.get('routes') or [{}])[0]
print(j.get('code', ''), r.get('distance', ''), r.get('duration', ''))
")"
  log "  code=$CODE  distance=${DIST}m  duration=${DUR}s"
  if [ "$CODE" != "Ok" ]; then
    log "  FAIL: expected code=Ok" >&2
    exit 1
  fi
done

log ""
log "=== Latency (100 requests, downtown -> airport) ==="
python3 - <<'PY'
import statistics
import time

import httpx

url = "http://127.0.0.1:5000/route/v1/driving/-122.6765,45.5152;-122.5968,45.5887?overview=false"
samples = []
with httpx.Client(timeout=10.0) as client:
    for _ in range(100):
        t0 = time.perf_counter()
        r = client.get(url)
        r.raise_for_status()
        if r.json().get("code") != "Ok":
            raise SystemExit("unexpected OSRM code during latency probe")
        samples.append((time.perf_counter() - t0) * 1000.0)
samples.sort()
p50 = statistics.median(samples)
p95 = samples[int(0.95 * len(samples)) - 1]
print(f"LATENCY|p50_ms={p50:.1f}|p95_ms={p95:.1f}")
PY

log ""
log "OSRM runtime: GO"
log "Update docs/SELF_HOSTED_ROUTING_PROOF_V0_2_STATUS.md and docs/CURRENT_TRUTH.md with VPS evidence."
