#!/usr/bin/env bash
# One-time Oregon OSM → OSRM MLD data prep (car profile).
# Run from docker/osrm-portland/ on a Linux host with Docker.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OSRM_IMAGE="${OSRM_IMAGE:-osrm/osrm-backend}"
PBF_URL="${PBF_URL:-https://download.geofabrik.de/north-america/us/oregon-latest.osm.pbf}"
PBF_FILE="${PBF_FILE:-data/oregon-latest.osm.pbf}"
TIMING_LOG="${TIMING_LOG:-data/prepare-timing.log}"

mkdir -p data
: >"$TIMING_LOG"

log_step() {
  local name="$1"
  shift
  local start end elapsed
  start="$(date +%s)"
  echo ""
  echo "=== ${name} ===" | tee -a "$TIMING_LOG"
  echo "started: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$TIMING_LOG"
  "$@" 2>&1 | tee -a "$TIMING_LOG"
  end="$(date +%s)"
  elapsed=$((end - start))
  echo "finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$TIMING_LOG"
  echo "duration_seconds: ${elapsed}" | tee -a "$TIMING_LOG"
  echo "STEP_${name}_SECONDS=${elapsed}" >>"$TIMING_LOG"
}

if [[ ! -f "$PBF_FILE" ]]; then
  log_step download_pbf curl -L -o "$PBF_FILE" "$PBF_URL"
else
  echo "=== download_pbf ===" | tee -a "$TIMING_LOG"
  echo "skipped: $PBF_FILE already exists ($(du -h "$PBF_FILE" | cut -f1))" | tee -a "$TIMING_LOG"
  echo "duration_seconds: 0" | tee -a "$TIMING_LOG"
fi

log_step extract docker run --rm -t \
  -v "${PWD}/data:/data" "$OSRM_IMAGE" \
  osrm-extract -p /opt/car.lua "/data/$(basename "$PBF_FILE")"

log_step partition docker run --rm -t \
  -v "${PWD}/data:/data" "$OSRM_IMAGE" \
  osrm-partition "/data/oregon-latest.osrm"

log_step customize docker run --rm -t \
  -v "${PWD}/data:/data" "$OSRM_IMAGE" \
  osrm-customize "/data/oregon-latest.osrm"

echo ""
echo "Data prep complete. Processed files:" | tee -a "$TIMING_LOG"
ls -lh data/*.osrm* 2>/dev/null | tee -a "$TIMING_LOG" || ls -lh data/ | tee -a "$TIMING_LOG"
