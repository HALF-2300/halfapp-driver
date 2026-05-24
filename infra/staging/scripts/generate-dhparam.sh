#!/usr/bin/env bash
# Generate nginx DH params for TLS (run once on the VPS or dev machine).
set -euo pipefail

OUT="$(cd "$(dirname "$0")/.." && pwd)/nginx/dhparam.pem"
openssl dhparam -out "$OUT" 2048
chmod 644 "$OUT"
echo "Wrote $OUT"
