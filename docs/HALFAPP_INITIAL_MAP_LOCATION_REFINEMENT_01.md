# HalfApp initial map location refinement (01)

**Directive:** `HALFAPP_INITIAL_MAP_LOCATION_REFINEMENT_01`  
**Scope:** `driver-app` cockpit first-load map only.

## Problem

Opening the cockpit briefly centered the map on an unrelated default (Montreal demo basin) before device geolocation resolved, then jumped to the real position.

## Solution

Pure presentation layer in `mapCenterPresentation.js` + `mapLocationSurface.js`, wired from `MapHome.jsx` into `MapView.jsx` and `useDriverGeolocation.js`.

### Before geolocation resolves

1. `useDriverGeolocation` starts in `requesting_location`.
2. `resolveMapCenterPresentation` returns `mapCenter: null`, `showMapCanvas: false`, `showLocatingOverlay: true`.
3. `resolveMapSurfaceState` returns `mode: locating`, `canMountLeaflet: false`.
4. `MapView` shows neutral backdrop + `map-locating-state` overlay (“Requesting device location…”).
5. Legacy Montreal coordinates are never used as an active center while requesting (`isLegacyUnrelatedDefaultCenter`).

### After geolocation succeeds

- Map mounts Leaflet centered on device lat/lng (`centerSource: device_location`).
- Device marker via `buildExperimentalMapMarkers` (`device-driver`).
- Labels: “Device location on map only — not backend dispatch truth”.

### Fallback (denied / unavailable / timeout)

- Dev: `using_dev_fallback_location` → Montreal coords with `DEV FALLBACK LOCATION — not real driver GPS` (chip + map banner).
- Production: neutral shell without fake GPS center when no position.
- Dev fixture pin (`includeDevDriver`) is not shown while `requesting_location`.

## Truth rule

Device/browser coordinates are **map visualization only**. No backend location persistence, dispatch truth, ETA, route, fare, or nearest-driver claims from this path.

## Tests

| Layer | File |
|-------|------|
| Unit | `tests/unit/initialMapLocation.test.js`, `mapCenterPresentation.test.js`, `locationTruth.test.js` |
| E2E | `tests/map-cockpit-truth.spec.ts` (delayed geo, denied, dev fallback label) |

## Commands

```bash
cd driver-app
npm run test
npm run build
npm run test:e2e:cockpit
```

## Not touched

Backend, landing page, app shell routing, ride transparency, 409 conflict, legacy `frontend/`, payments, booking, customer app.
