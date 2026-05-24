# Ride app foundation v0.1

Scope: backend-owned ride state, integer-cent pricing ledger, in-app OSM/Leaflet map, external Google Maps navigation only. No surge, Stripe Connect, embedded Google Maps, or paid traffic APIs.

## Lifecycle (storage vs v0.1 label)

| Storage `status` (transitions) | `v01_lifecycle_status` (display/ops) |
|--------------------------------|--------------------------------------|
| `requested` (no quote) | `requested` |
| `requested` + pricing row | `priced` |
| `accepted` | `driver_assigned` |
| `driver_arrived` | `driver_arriving` |
| `in_progress` | `in_progress` |
| `completed` | `completed` |
| `cancelled` | `cancelled` |

Transitions use storage statuses (`POST /drivers/accept-ride`, etc.). Refresh reloads the same storage status and pricing row from the database.

## Pricing (integer cents)

```
driverShareableRideFareCents = base + distance + time + wait (min fare applied)
platformCommissionCents = 20% of driverShareableRideFareCents
driverRidePayoutCents = 80% of driverShareableRideFareCents
platformServiceFeeCents = 150 (not commissioned)
platformRevenueCents = platformCommissionCents + platformServiceFeeCents
customerTotalCents = shareable + serviceFee + passThroughFees + tipCents
```

Tips and pass-through fees (city, airport, tolls, accessibility, taxes) are excluded from commission.

Completion sets `financial_locked` on `ride_pricing`; cancelled rides do not produce a completed payout lock.

## Map / navigation

- In-app: Leaflet + OSM tiles (`route_provider=leaflet_osm`, `traffic_provider=disabled`).
- External: `Open in Google Maps` opens `https://www.google.com/maps/dir/?api=1&destination=…` (no embed, no API key).
- Route evidence: `route_snapshots` rows (`quote` on create, `complete` on driver complete) with `route_provider`, `used_fallback`, distance/duration, and stable hashes. Read via `GET /drivers/rides/{ride_id}/route-snapshots`. Snapshots record backend truth; `haversine_fallback` is not road-network proof; production OSRM requires separate runtime proof.

## Active surfaces

- `backend` — rides, pricing, driver presence, admin ops list
- `driver-app` — cockpit map, marketplace sheet, external nav buttons
