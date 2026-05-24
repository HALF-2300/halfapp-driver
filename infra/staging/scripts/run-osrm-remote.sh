#!/usr/bin/env bash
# Run OSRM deploy on staging VPS from your laptop (Git Bash / WSL / Linux).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGING_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$STAGING_DIR/../.." && pwd)"

ENV_FILE="$STAGING_DIR/staging.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — run infra/staging/scripts/provision-hetzner.sh first (Agent 1)." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$ENV_FILE"

SSH_KEY="${HALFAPP_SSH_KEY:-$HOME/.ssh/halfapp_staging_ed25519}"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -i "$SSH_KEY")

echo "Syncing docker/osrm-portland + infra/staging to $VPS_USER@$VPS_IP ..."
ssh "${SSH_OPTS[@]}" "$VPS_USER@$VPS_IP" "sudo mkdir -p /opt/halfapp/halfapp-driver && sudo chown -R $VPS_USER:$VPS_USER /opt/halfapp"

rsync -az --delete \
  -e "ssh ${SSH_OPTS[*]}" \
  "$REPO_ROOT/docker/osrm-portland/" \
  "$VPS_USER@$VPS_IP:/opt/halfapp/halfapp-driver/docker/osrm-portland/"

rsync -az \
  -e "ssh ${SSH_OPTS[*]}" \
  "$REPO_ROOT/infra/staging/" \
  "$VPS_USER@$VPS_IP:/opt/halfapp/halfapp-driver/infra/staging/"

rsync -az \
  -e "ssh ${SSH_OPTS[*]}" \
  "$REPO_ROOT/docs/" \
  "$VPS_USER@$VPS_IP:/opt/halfapp/halfapp-driver/docs/"

echo "Running deploy-osrm-vps.sh on VPS (30–60 min for first data prep) ..."
ssh "${SSH_OPTS[@]}" "$VPS_USER@$VPS_IP" \
  "HALFAPP_REPO=/opt/halfapp/halfapp-driver bash /opt/halfapp/halfapp-driver/infra/staging/scripts/deploy-osrm-vps.sh"

echo ""
echo "Fetch evidence:"
echo "  scp -i $SSH_KEY $VPS_USER@$VPS_IP:/opt/halfapp/halfapp-driver/docs/OSRM_RUNTIME_PROOF_V0_2_EVIDENCE.txt docs/"
