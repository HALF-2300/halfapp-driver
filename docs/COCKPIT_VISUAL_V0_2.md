# Cockpit Visual v0.2

## What changed

- Switched map tiles to CARTO Voyager (distinct from default OSM look, still free/low-volume friendly).
- Added smoother ride-state transitions in the bottom sheet with Framer Motion.
- Tightened cockpit typography/spacing consistency using shared `--ha-*` tokens.
- Upgraded 409 conflict UI to a compact proof panel (`ClaimConflictNotice`) rather than a plain banner/toast style.
- Improved incoming-offer urgency with a stronger countdown style under 8 seconds.

## Before / after screenshots

> Capture these from staging cockpit after deployment and attach in this doc.

### Before

- `driver-app` cockpit with default OSM + prior conflict card

### After

- `driver-app` cockpit with CARTO Voyager + animated state transitions
- Conflict proof panel visible after a forced 409 claim race
- Incoming request card showing urgent countdown styling (<8s)

## Validation notes

- Frontend build passes (`npm run build` in `driver-app`).
- Visual changes are isolated to cockpit components and styles; no dispatch/truth logic changes.
