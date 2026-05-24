#!/usr/bin/env bash
# OSRM healthcheck (ops-only, Slice 05). Exits non-zero on failure.
# Requires: OSRM_BASE_URL (e.g. http://127.0.0.1:5000)

set -euo pipefail

if [[ -z "${OSRM_BASE_URL:-}" ]]; then
  echo "FAIL: OSRM_BASE_URL not set"
  exit 2
fi

BASE="${OSRM_BASE_URL%/}"
# Portland metro leg (matches docker/osrm-portland README)
URL="${BASE}/route/v1/driving/-122.5951,45.5898;-122.6784,45.5152?overview=false&steps=false"

RESP="$(curl -fsS --max-time 10 "$URL")" || {
  echo "FAIL: curl request failed"
  exit 1
}

CODE="$(printf '%s' "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("code",""))')"
if [[ "$CODE" != "Ok" ]]; then
  echo "FAIL: code=$CODE"
  exit 1
fi

DIST="$(printf '%s' "$RESP" | python3 -c 'import json,sys; j=json.load(sys.stdin); r=j.get("routes") or []; print(int(r[0].get("distance",0)) if r else 0)')"
if [[ "$DIST" -le 0 ]]; then
  echo "FAIL: distance=$DIST"
  exit 1
fi

echo "OK: routes[0].distance=$DIST"
