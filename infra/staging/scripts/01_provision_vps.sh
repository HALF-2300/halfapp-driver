#!/usr/bin/env bash
# Idempotent first-time setup on Ubuntu 24.04 staging VPS.
# Run as root: sudo bash infra/staging/scripts/01_provision_vps.sh
set -euo pipefail

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "ERROR: Run as root (sudo)." >&2
  exit 1
fi

HALFAPP_USER="${HALFAPP_USER:-halfapp}"
REPO_DIR="${REPO_DIR:-/opt/halfapp-driver}"
REPO_URL="${HALFAPP_REPO_URL:-https://github.com/halfapp/halfapp-driver.git}"
ENV_LOCAL="${REPO_DIR}/infra/staging/env/staging.env.local"
ENV_SYSTEM="/etc/halfapp/staging.env"

export DEBIAN_FRONTEND=noninteractive

echo "==> apt update && upgrade"
apt-get update
apt-get upgrade -y

echo "==> Install packages"
apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  docker.io \
  docker-compose-plugin \
  nginx \
  certbot \
  python3-certbot-nginx \
  ufw \
  fail2ban \
  htop \
  jq \
  git

echo "==> UFW"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable

echo "==> halfapp user"
if ! id "$HALFAPP_USER" &>/dev/null; then
  useradd -m -s /bin/bash "$HALFAPP_USER"
fi
usermod -aG docker "$HALFAPP_USER" 2>/dev/null || true

echo "==> Clone or update repo at ${REPO_DIR}"
install -d -m 0755 "$(dirname "$REPO_DIR")"
if [[ -d "${REPO_DIR}/.git" ]]; then
  sudo -u "$HALFAPP_USER" git -C "$REPO_DIR" fetch --all --prune
  sudo -u "$HALFAPP_USER" git -C "$REPO_DIR" pull --ff-only origin main || \
    sudo -u "$HALFAPP_USER" git -C "$REPO_DIR" pull --ff-only
else
  sudo -u "$HALFAPP_USER" git clone "$REPO_URL" "$REPO_DIR"
fi
chown -R "$HALFAPP_USER:$HALFAPP_USER" "$REPO_DIR"

echo "==> Staging env symlink"
if [[ ! -f "$ENV_LOCAL" ]]; then
  echo "ERROR: Missing ${ENV_LOCAL}" >&2
  echo "  Copy infra/staging/env/staging.env.template → staging.env.local on the VPS," >&2
  echo "  set DATABASE_URL, SECRET_KEY (≥32 chars), and Neon credentials, then re-run." >&2
  exit 1
fi
install -d -m 0750 /etc/halfapp
ln -sf "$ENV_LOCAL" "$ENV_SYSTEM"
chown root:"$HALFAPP_USER" /etc/halfapp "$ENV_SYSTEM" 2>/dev/null || true
chmod 640 "$ENV_SYSTEM" 2>/dev/null || true

echo "==> docker compose pull (public images)"
cd "$REPO_DIR"
docker compose -f infra/staging/docker-compose.yml pull osrm-routed nginx || true

echo ""
echo "Provision complete (idempotent — safe to re-run)."
echo ""
echo "Next steps (operator):"
echo "  1. GATE-VPS-1: ensure DNS staging.halfapp.app → this host."
echo "  2. Issue TLS (once DNS propagates):"
echo "       docker volume create halfapp-staging-certbot-www halfapp-staging-letsencrypt"
echo "       certbot certonly --webroot -w /var/lib/docker/volumes/halfapp-staging-certbot-www/_data \\"
echo "         -d staging.halfapp.app --agree-tos -m you@halfapp.app"
echo "     (or use certbot in README after nginx HTTP is up)"
echo "  3. Agent 2: prepare OSRM under docker/osrm-portland/data (see docker/osrm-portland/README.md)"
echo "  4. Start stack:  cd ${REPO_DIR} && docker compose -f infra/staging/docker-compose.yml up -d"
echo "  5. Deploy API:   sudo -u ${HALFAPP_USER} bash ${REPO_DIR}/infra/staging/scripts/02_deploy_api.sh"
echo "  6. Health:       BASE=https://staging.halfapp.app bash ${REPO_DIR}/infra/staging/scripts/03_health_check.sh"
