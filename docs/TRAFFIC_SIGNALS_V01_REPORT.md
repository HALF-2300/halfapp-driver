# Traffic Signals v0.1 — Implementation Report

Date: 2026-05-22

## Map decision (unchanged)

- In-app map remains **Leaflet + OpenStreetMap** (`MapView.jsx`, `mapProvider.js`).
- No Google Maps embed, tiles, traffic layers, or Routes API inside the app.
- **External navigation** opens Google Maps in browser/app only (`ExternalNavigationButtons.jsx`).

## Traffic decision (new)

- **Free official signals only**: ODOT TripCheck (Oregon) and WSDOT Traveler Information (Washington).
- `traffic_aware` stays **false** (no route-level live traffic timing).
- `traffic_signal_aware` is **true** when incident/flow warnings are present near the route or map bbox.
- `traffic_provider`: `odot_tripcheck` | `wsdot` | `none` by geography.
- `route_confidence`: `medium` or `low` based on feed quality / signal presence.
- ETA uses base route estimate + optional buffer (`+2 min` per nearby incident, max `+10 min`); labeled via API disclaimer.

## Configuration

Backend (`backend/.env`):

```env
TRAFFIC_SIGNALS_ENABLED=false
ODOT_TRIPCHECK_SUBSCRIPTION_KEY=
WSDOT_ACCESS_CODE=
```

Driver app (`driver-app/.env`):

```env
VITE_TRAFFIC_SIGNALS_ENABLED=false
```

Register keys at [TripCheck API](https://www.tripcheck.com/Pages/API) and [WSDOT Traveler Information API](https://wsdot.wa.gov/traffic/api/).

## Failure safety

- Traffic fetch is isolated in `traffic_signals_service.py` / `trafficSignalsService.js`.
- Exceptions return empty signals; ride booking is never blocked.
- Traffic data is not used for pricing.

## API

`GET /drivers/traffic-signals` — query by route (`origin_lat/lng`, `destination_lat/lng`) or map bbox.

## Verdict criteria

See agent final report for GO / PARTIAL_GO / NO_GO after test run.
