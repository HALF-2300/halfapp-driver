# Rider Stub — DEMO ONLY

**Status:** Demo / engineering aid. **NOT** a rider product. **NOT** production.

Date: 2026-05-24

---

## Classification

| Label | Meaning |
|-------|---------|
| **DEMO ONLY** | For staging two-sided demos and manual API smoke tests |
| **NOT A RIDER PRODUCT** | HalfApp has no shipped rider app; this is not it |
| **NOT PRODUCTION** | No auth UX, no payments, no support tooling, no app store path |

Authoritative context: `docs/SYSTEM_TRUTH.md`.

---

## What it does (demo scope)

- Geocodes pickup/dropoff with Nominatim (labeled in UI as demo geocoding).
- Sends `POST /rides/` to the configured backend.
- Subscribes to `GET /rides/{ride_id}/stream` (SSE), with polling fallback via `GET /rides/{ride_id}`.
- Shows lifecycle progression (`requested → accepted → in_progress → completed`) and completion summary.

This proves the **API path** for demos. It does **not** constitute a rider product surface.

---

## Usage

1. Serve the file (or open directly):
   - Open `rider-stub/index.html` in a mobile browser.
2. Set:
   - `API base URL` (your staging backend origin),
   - `Rider bearer token` (JWT for a rider role account).
3. Enter Portland pickup/dropoff addresses and tap **Request Ride**.

---

## Do not

- Cite this directory in investor decks or PRs as "the rider app."
- Treat this as evidence that demand-side product exists.
- Extend this stub instead of building a real rider product when rider UX is required.
