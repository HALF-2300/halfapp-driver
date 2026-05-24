#!/usr/bin/env bash
# Install daily logrotate for HalfApp staging host logs (idempotent).
set -euo pipefail

if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

install -d -m 0755 /var/log/halfapp

cat >/etc/logrotate.d/halfapp-staging <<'EOF'
/var/log/halfapp/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    sharedscripts
    postrotate
        docker compose -f /opt/halfapp-driver/infra/staging/docker-compose.yml kill -s USR1 nginx 2>/dev/null || true
    endscript
}
EOF

logrotate -d /etc/logrotate.d/halfapp-staging >/dev/null 2>&1 || true
echo "Installed /etc/logrotate.d/halfapp-staging (daily, 14 rotations)."
