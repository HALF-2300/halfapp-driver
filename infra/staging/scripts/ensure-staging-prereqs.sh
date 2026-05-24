#!/usr/bin/env bash
# One-time host prep before staging compose up (dhparam, env file path).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DHPARAM="$ROOT/nginx/dhparam.pem"
ENV_FILE="${HALFAPP_STAGING_ENV:-/etc/halfapp/staging.env}"

if [[ ! -f "$DHPARAM" ]]; then
  echo "Generating DH parameters at $DHPARAM ..."
  bash "$ROOT/scripts/generate-dhparam.sh"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  echo "Copy infra/staging/etc/halfapp.staging.env.example and fill secrets." >&2
  exit 1
fi

echo "Prerequisites OK (dhparam + $ENV_FILE)"
