# Rider Stub (Demo)

Simple single-page rider surface for two-sided demos.

## What it does

- Geocodes pickup/dropoff with Nominatim (labeled in UI as demo geocoding).
- Sends `POST /rides/` to the configured backend.
- Subscribes to `GET /rides/{ride_id}/stream` (SSE), with polling fallback via `GET /rides/{ride_id}`.
- Shows lifecycle progression (`requested → accepted → in_progress → completed`) and completion summary.

## Usage

1. Serve the file (or open directly):
   - Open `rider-stub/index.html` in a mobile browser.
2. Set:
   - `API base URL` (your staging backend origin),
   - `Rider bearer token` (JWT for a rider role account).
3. Enter Portland pickup/dropoff addresses and tap **Request Ride**.
