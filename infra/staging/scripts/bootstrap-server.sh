#!/usr/bin/env bash
# Idempotent re-run on an existing Ubuntu VPS (if cloud-init was skipped).
set -euo pipefail

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

HALFAPP_USER="${HALFAPP_USER:-halfapp}"
PUB_KEY_FILE="${PUB_KEY_FILE:-}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg ufw nginx certbot python3-certbot-nginx fail2ban

if ! id "$HALFAPP_USER" &>/dev/null; then
  useradd -m -s /bin/bash -G sudo,docker "$HALFAPP_USER" 2>/dev/null || useradd -m -s /bin/bash -G sudo "$HALFAPP_USER"
  usermod -aG sudo "$HALFAPP_USER"
fi

if [[ -n "$PUB_KEY_FILE" && -f "$PUB_KEY_FILE" ]]; then
  install -d -m 700 -o "$HALFAPP_USER" -g "$HALFAPP_USER" "/home/$HALFAPP_USER/.ssh"
  grep -qF "$(cat "$PUB_KEY_FILE")" "/home/$HALFAPP_USER/.ssh/authorized_keys" 2>/dev/null \
    || cat "$PUB_KEY_FILE" >> "/home/$HALFAPP_USER/.ssh/authorized_keys"
  chown -R "$HALFAPP_USER:$HALFAPP_USER" "/home/$HALFAPP_USER/.ssh"
  chmod 600 "/home/$HALFAPP_USER/.ssh/authorized_keys"
fi

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
usermod -aG docker "$HALFAPP_USER"

cat >/etc/ssh/sshd_config.d/99-halfapp-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
MaxAuthTries 3
EOF
systemctl restart ssh

ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

install -D -m 644 "$(dirname "$0")/../nginx/halfapp-staging.conf" /etc/nginx/sites-available/halfapp-staging
ln -sf /etc/nginx/sites-available/halfapp-staging /etc/nginx/sites-enabled/halfapp-staging
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl enable --now nginx

mkdir -p /opt/halfapp
chown -R "$HALFAPP_USER:$HALFAPP_USER" /opt/halfapp

echo "Bootstrap complete. Verify: docker ps (as $HALFAPP_USER after re-login)."
