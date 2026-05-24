#!/usr/bin/env bash
# Run HalfApp driver stack in DEV (backend + driver-app).
# Usage: bash scripts/run_dev.sh [--real-backend]
#
# Ports: backend 127.0.0.1:8000, frontend 127.0.0.1:3022

set -euo pipefail

REAL_BACKEND=0
if [[ "${1:-}" == "--real-backend" ]]; then
  REAL_BACKEND=1
fi

BACKEND_PORT=8000
FRONTEND_PORT=3022
BACKEND_HOST="127.0.0.1"
API_BASE="http://${BACKEND_HOST}:${BACKEND_PORT}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Repo root: $ROOT"

BACKEND="$ROOT/backend"
FRONTEND="$ROOT/driver-app"

command -v python3 >/dev/null || { echo "python3 required"; exit 1; }
command -v npm >/dev/null || { echo "npm required"; exit 1; }

echo "== Backend: alembic upgrade head + uvicorn =="
cd "$BACKEND"
python3 -m alembic upgrade head
python3 -m uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload &
BACK_PID=$!

echo "== Driver app: npm run dev =="
cd "$FRONTEND"
export VITE_API_BASE="$API_BASE"
if [[ "$REAL_BACKEND" -eq 1 ]]; then
  export VITE_ALLOW_OFFLINE_MOCK=false
  echo "Real backend: VITE_ALLOW_OFFLINE_MOCK=false"
fi
if [[ ! -d node_modules ]]; then
  npm install
fi
npm run dev &
FRONT_PID=$!

echo ""
echo "DEV started:"
echo "- Backend:  $API_BASE"
echo "- Driver app: http://${BACKEND_HOST}:${FRONTEND_PORT}/"
echo "Press Ctrl+C to stop both."

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null || true' INT TERM
wait $BACK_PID $FRONT_PID
