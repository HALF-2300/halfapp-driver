#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-https://staging.halfapp.app}"

echo "1. API healthz..."
curl -fsS "$BASE/api/healthz" | jq .

echo "2. API version..."
curl -fsS "$BASE/api/version" | jq .

echo "3. OSRM route (PDX downtown -> airport)..."
curl -fsS "$BASE/osrm/route/v1/driving/-122.6765,45.5152;-122.5968,45.5887?overview=false" \
  | jq '.code, .routes[0].distance, .routes[0].duration'

echo "4. Public CORS preflight..."
curl -fsS -X OPTIONS "$BASE/api/drivers/available-rides" \
  -H "Origin: https://rider-stub.halfapp.app" \
  -H "Access-Control-Request-Method: GET" -i | head -20

echo "All staging checks passed."
