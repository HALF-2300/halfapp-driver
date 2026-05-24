#!/usr/bin/env bash
# Copy processed Oregon OSRM files into the named Docker volume used by staging compose.
# Prerequisite: run docker/osrm-portland/prepare-data.sh on the VPS first.
set -euo pipefail

REPO_ROOT="${HALFAPP_REPO:-$(cd "$(dirname "$0")/../../.." && pwd)}"
SRC="$REPO_ROOT/docker/osrm-portland/data"
VOLUME="${OSRM_VOLUME_NAME:-halfapp-osrm-data}"

if [[ ! -f "$SRC/oregon-latest.osrm" && ! -f "$SRC/oregon-latest.osrm.hsgr" ]]; then
  echo "Missing processed OSRM data under $SRC" >&2
  echo "Run: cd $REPO_ROOT/docker/osrm-portland && bash ./prepare-data.sh" >&2
  exit 1
fi

docker volume inspect "$VOLUME" >/dev/null 2>&1 || docker volume create "$VOLUME" >/dev/null

echo "Seeding $VOLUME from $SRC ..."
docker run --rm \
  -v "${VOLUME}:/data" \
  -v "${SRC}:/src:ro" \
  alpine:3.20 \
  sh -c 'rm -rf /data/* && cp -a /src/. /data/ && ls -lh /data'

echo "OK: volume $VOLUME ready for osrm-routed"
