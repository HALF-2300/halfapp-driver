# Final Report: HALFAPP_POST_409_TRANSPARENCY_MEMORY_01

Date: 2026-05-22

## Verdict

**GO**

## Files Changed

**Backend**
- `backend/services/metrics.py` — `marketplace_ledger_events` on dispatch proof
- `backend/services/transparency.py` — merged audit ids, `claim.truth_status`
- `backend/tests/test_ride_transparency_and_claim_conflict.py`

**Driver app**
- `driver-app/src/components/MapHome.jsx`
- `driver-app/src/components/cockpit/ConflictTransparencyMemory.jsx` (new)
- `driver-app/src/components/cockpit/MarketplaceBottomSheet.jsx`
- `driver-app/src/utils/rideTransparency.js`
- `driver-app/tests/unit/conflictTransparencyMemory.test.js` (new)
- `driver-app/tests/ride-transparency-panel.spec.ts`

**Docs**
- `docs/HALFAPP_POST_409_TRANSPARENCY_MEMORY_01.md` (this file)

## Backend Changes

- `GET /drivers/rides/{ride_id}/transparency` `dispatch_proof` now includes `marketplace_ledger_events[]`.
- Driver-scoped `audit.ledger_event_ids` merges legacy ledger entry ids and marketplace event ids for this driver (`dispatch.ride_visible`, `dispatch.claim_attempted`, `dispatch.claim_lost`, `ride.hidden`).
- `claim.truth_status` is `backend_conflict` when `last_claim_result` is `lost`.

Non-breaking additive fields only.

## Driver-App Changes

- **`lastConflictRideId`** — React session state in `MapHome` (not localStorage).
- On **409**: store ride id, fetch transparency, show `ClaimConflictNotice` + `ConflictTransparencyMemory` on **online-idle** sheet.
- **Polling** excludes the conflict ride so it is not re-offered as claimable.
- **Unavailable fetch**: honest copy “Conflict recorded by backend · Transparency details unavailable”.
- Cleared on go-online (from offline), go-offline, successful accept.

## Conflict Memory Behavior

`lastConflictRideId` lives only in component state and a ref used by refresh polling. It survives the transition from incoming → online-idle after 409 so the idle sheet can show durable proof. It is not written to localStorage and is not marketplace truth — only a UI pointer to re-fetch `GET /drivers/rides/{id}/transparency`.

## Transparency After 409

1. `POST /drivers/accept-ride/{id}` returns 409.
2. Cockpit calls `GET /drivers/rides/{id}/transparency`.
3. Idle sheet shows: conflict notice, `last_claim_result: lost`, `truth_status: backend_conflict`, `CLAIM_CONFLICT_PROOF`, visibility/policy summary, audit event ids (when present).

## Tests Added

| Test | Result |
|------|--------|
| `conflictTransparencyMemory.test.js` | Pass |
| `ride-transparency-panel.spec.ts` (idle memory + 403 fallback) | Pass |
| `test_ride_transparency_and_claim_conflict.py` (audit + truth_status) | Pass |

Trust two-driver E2E remains optional; backend + mock Playwright cover the contract.

## Commands Run

```
pytest backend/tests/test_ride_transparency_and_claim_conflict.py backend/tests/test_dispatch_auditability.py -q
npm run test
npm run build
npx playwright test tests/ride-transparency-panel.spec.ts
```

## Evidence

- **409 conflict proof** — unchanged structured 409 body; mock Playwright asserts notice on idle sheet.
- **Transparency fetch** — `loadConflictTransparency(rideId)` after 409; stubbed in tests.
- **Lost claim on idle** — `last_claim_result` / `lost` / `backend_conflict` visible on `sheet-online-idle`.
- **No fake success** — 409 still rethrown in mock mode; ride excluded from available polling.
- **No ETA/route/fare invention** — conflict panel uses visibility/claim/audit fields only.

## Not Built

Public face, app shell, dispatch optimizer, routing, payments, rider/admin apps.

## Next Small Slice

Proceed to **`HALFAPP_PUBLIC_FACE_AND_APP_SHELL_01`** if product priority is outward-facing driver onboarding and shell polish. Otherwise add a lightweight “dismiss conflict memory” control on the idle sheet after the driver acknowledges the lost claim.
