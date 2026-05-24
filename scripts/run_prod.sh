#!/usr/bin/env bash
# Production-style local run (not for real production hosting of the SPA).
# - Backend: uvicorn with multiple workers
# - Frontend: vite build + vite preview (preview is staging-only per Vite docs)
#
# Usage: bash scripts/run_prod.sh

set -euo pipefail

BACKEND_PORT=8000
PREVIEW_PORT=3022
BACKEND_HOST="0.0.0.0"
PREVIEW_HOST="127.0.0.1"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Repo root: $ROOT"

cd "$ROOT/backend"
python3 -m alembic upgrade head

echo "Starting backend (uvicorn --workers 4) on ${BACKEND_HOST}:${BACKEND_PORT}"
python3 -m uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --workers 4 &
BACK_PID=$!

cd "$ROOT/driver-app"
npm ci
npm run build

echo "Starting vite preview on http://${PREVIEW_HOST}:${PREVIEW_PORT} (not a production CDN/nginx)"
npm run preview -- --host "$PREVIEW_HOST" --port "$PREVIEW_PORT" &
FRONT_PID=$!

echo ""
echo "PROD-style local:"
echo "- Backend:  http://127.0.0.1:${BACKEND_PORT}"
echo "- Preview:  http://${PREVIEW_HOST}:${PREVIEW_PORT}"
echo "Serve driver-app/dist/ with nginx or static host for real production."

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null || true' INT TERM
wait $BACK_PID $FRONT_PID
