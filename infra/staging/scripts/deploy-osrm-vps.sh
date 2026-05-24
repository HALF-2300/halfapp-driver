#!/usr/bin/env bash
# OSRM runtime deploy for HalfApp staging VPS (Agent 2).
# Run ON the VPS after repo is at /opt/halfapp/halfapp-driver, or pipe via SSH:
#   ssh staging 'bash -s' < infra/staging/scripts/deploy-osrm-vps.sh
set -euo pipefail

REPO_ROOT="${HALFAPP_REPO:-/opt/halfapp/halfapp-driver}"
OSRM_DIR="$REPO_ROOT/docker/osrm-portland"
OVERRIDE="$REPO_ROOT/infra/staging/docker/osrm-localhost.override.yml"
ACCEPT_URL='http://127.0.0.1:5000/route/v1/driving/-122.6765,45.5152;-122.5968,45.5887?overview=full'
EVIDENCE_DIR="$REPO_ROOT/docs"
EVIDENCE_FILE="$EVIDENCE_DIR/OSRM_RUNTIME_PROOF_V0_2_EVIDENCE.txt"

if [[ ! -d "$OSRM_DIR" ]]; then
  echo "Missing $OSRM_DIR — clone repo to /opt/halfapp/halfapp-driver first." >&2
  exit 1
fi

cd "$OSRM_DIR"
export OSRM_IMAGE="${OSRM_IMAGE:-osrm/osrm-backend}"

echo "=== OSRM deploy (image=$OSRM_IMAGE) ==="
bash ./prepare-data.sh

COMPOSE_ARGS=(-f docker-compose.yml)
if [[ -f "$OVERRIDE" ]]; then
  COMPOSE_ARGS+=(-f "$OVERRIDE")
fi

docker compose "${COMPOSE_ARGS[@]}" pull
docker compose "${COMPOSE_ARGS[@]}" up -d

echo "Waiting for OSRM to accept routes..."
for i in $(seq 1 40); do
  if curl -fsS --max-time 5 "$ACCEPT_URL" >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

HTTP_CODE="$(curl -sS -o /tmp/osrm-accept.json -w '%{http_code}' --max-time 30 "$ACCEPT_URL")"
CURL_BODY="$(cat /tmp/osrm-accept.json)"

mkdir -p "$EVIDENCE_DIR"
{
  echo "host: $(hostname)"
  echo "deployed_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "http_code: $HTTP_CODE"
  echo "accept_url: $ACCEPT_URL"
  echo "--- timing log ---"
  cat data/prepare-timing.log 2>/dev/null || true
  echo "--- curl body ---"
  echo "$CURL_BODY"
} >"$EVIDENCE_FILE"

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "FAIL: HTTP $HTTP_CODE" >&2
  exit 1
fi

python3 - <<'PY'
import json
j = json.load(open("/tmp/osrm-accept.json"))
routes = j.get("routes") or []
assert j.get("code") == "Ok", j.get("code")
assert routes, "no routes"
assert "geometry" in routes[0], "routes[0] missing geometry"
print("OK: routes[0].geometry present, distance=", routes[0].get("distance"))
PY

docker compose "${COMPOSE_ARGS[@]}" ps
echo "Evidence written: $EVIDENCE_FILE"
