#!/usr/bin/env bash
# Build API, run Alembic migrations, restart api service, verify health.
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/halfapp-driver}"
COMPOSE_FILE="${REPO_DIR}/infra/staging/docker-compose.yml"
OSRM_DATA="${OSRM_DATA_DIR:-${REPO_DIR}/docker/osrm-portland/data}"

cd "$REPO_DIR"

if ! compgen -G "${OSRM_DATA}/*.osrm" >/dev/null 2>&1; then
  echo "WARN: OSRM graph not found under ${OSRM_DATA} (*.osrm missing)." >&2
  echo "WARN: Agent 2 can prepare data later; API deploy continues." >&2
fi

echo "==> git pull"
git pull origin main

echo "==> build api"
docker compose -f "$COMPOSE_FILE" build api

echo "==> alembic upgrade head"
docker compose -f "$COMPOSE_FILE" run --rm api alembic upgrade head

echo "==> up api"
docker compose -f "$COMPOSE_FILE" up -d api

echo "==> wait for API"
sleep 5

echo "==> health check"
if [[ -x "${REPO_DIR}/infra/staging/scripts/03_health_check.sh" ]]; then
  BASE="${BASE:-https://staging.halfapp.app}" \
    bash "${REPO_DIR}/infra/staging/scripts/03_health_check.sh"
else
  echo "WARN: 03_health_check.sh not executable; skipping remote checks." >&2
fi

echo "==> api logs (last 30 lines)"
docker compose -f "$COMPOSE_FILE" logs --tail=30 api
