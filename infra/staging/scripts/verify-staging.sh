#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck disable=SC1091
source "$STAGING_DIR/staging.env"

SSH_KEY="${HALFAPP_SSH_KEY:-$HOME/.ssh/halfapp_staging_ed25519}"
TARGET="${VPS_USER}@${VPS_IP}"

if [[ "$VPS_IP" == "0.0.0.0" || "${PROVISION_STATUS:-}" == "PROVISION_PENDING" ]]; then
  echo "FAIL: staging not provisioned (VPS_IP=$VPS_IP). Run provision-hetzner.ps1 first." >&2
  exit 1
fi

echo "SSH -> $TARGET"
ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15 "$TARGET" 'docker ps && echo STAGING_ACCEPTANCE_OK'
