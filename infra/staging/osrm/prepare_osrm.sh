#!/usr/bin/env bash
# Agent 2 entrypoint — delegates to staging OSRM prep (volume + compose).
# Run on VPS: cd /opt/halfapp/halfapp-driver && ./infra/staging/osrm/prepare_osrm.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${HALFAPP_REPO:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
export HALFAPP_REPO="$REPO_ROOT"

exec bash "$REPO_ROOT/infra/staging/scripts/prepare-osrm-oregon.sh"
