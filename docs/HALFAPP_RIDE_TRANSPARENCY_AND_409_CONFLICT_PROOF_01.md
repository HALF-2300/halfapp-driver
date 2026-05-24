# HALFAPP_RIDE_TRANSPARENCY_AND_409_CONFLICT_PROOF_01

Date: 2026-05-22

## Verdict

**GO**

## Purpose

Let the active driver app explain why a ride appeared, which backend records prove visibility, and what happens when two drivers compete to claim the same open-board ride — without inventing ETA, route, fare, or nearest-driver truth.

## Endpoint contract

### `GET /drivers/rides/{ride_id}/transparency`

- **Auth:** Bearer (driver).
- **Access:** Driver must have a `ride_visibility` row, a `ride_claim_attempt`, or be the assigned driver. Otherwise **403**.
- **Response:** Driver-scoped view plus full dispatch proof:

| Field | Meaning |
| --- | --- |
| `ride_id`, `driver_id` | Scoped identifiers (strings). |
| `visibility` | `visible`, `visible_at`, `visibility_record_id`, `source`, policy fields, `reason_codes`. |
| `claim` | `claimable`, `current_status`, `claimed_by_driver_id`, `last_claim_attempt_id`, `last_claim_result`. |
| `dismissal` | `hidden_for_this_driver`, `hidden_at`, `expires_at`, `reason`. |
| `audit` | `ledger_event_ids`, `correlation_id`. |
| `truth_labels` | UI-safe labels (`BACKEND_OWNED`, `CLAIM_CONFLICT_PROOF`, …). |
| `dispatch_proof` | Full audit payload (visibility rows, claim attempts, ledger entries, conflict block). |

Visibility `source` values: `open_board`, `dispatch_policy`, `simulation`, `unknown`.

### `POST /drivers/accept-ride/{ride_id}` conflict

When another driver already claimed the ride:

```http
HTTP/1.1 409 Conflict
```

```json
{
  "detail": {
    "detail": "Ride already claimed",
    "ride_id": 42,
    "claim_result": "lost",
    "truth_status": "backend_conflict"
  }
}
```

FastAPI nests this under the standard `detail` key.

## Claim concurrency

- **Policy:** Ranked open board, first successful atomic claim wins (`policy.claim_ride`).
- **Dev DB:** SQLite via SQLAlchemy; sequential and threaded tests prove one winner + one 409 loser.
- **Limitation:** SQLite locking differs from Postgres production; do not assume identical race timing under high concurrency.
- **Future (Postgres):** Consider `SELECT … FOR UPDATE SKIP LOCKED` on ride rows when migrating; not required for this slice.

## Audit / ledger events

Verified on claim paths:

| Event | When |
| --- | --- |
| `claim_attempted` | Every accept attempt |
| `claim_won` | Successful claim |
| `claim_lost` | 409 / unavailable loser |
| `dispatch.ride_visible` | Available-rides exposure (marketplace ledger events table) |
| `ride.hidden` | Driver hide/dismiss |

Events are append-only; historical rows are not mutated.

## Driver-app behavior

- **Why am I seeing this?** — expandable panel on incoming ride sheet; loads `GET /drivers/rides/{id}/transparency`.
- **409 UI** — `ClaimConflictNotice`: “Ride already claimed / Another driver got this ride first.” + “Backend conflict proof” badge; Accept disabled; ride cleared from active state.
- **No invented facts** — panel shows backend visibility/claim/dismissal only; no ETA/route/fare synthesis.

## Tests

| Suite | File |
| --- | --- |
| Backend transparency + conflict | `backend/tests/test_ride_transparency_and_claim_conflict.py` |
| Dispatch audit (updated) | `backend/tests/test_dispatch_auditability.py` |
| Lifecycle race (updated) | `backend/tests/test_ride_lifecycle.py` |
| Driver unit | `driver-app/tests/unit/rideTransparency.test.js` |
| Trust E2E two-driver | `driver-app/tests/trust-mock-off/ride-transparency-conflict.spec.ts` |

## Commands run

```bash
pytest backend/tests/test_ride_transparency_and_claim_conflict.py backend/tests/test_dispatch_auditability.py -q
# 8 passed

npm run test --prefix driver-app
# 8 passed (locationTruth + rideTransparency)

npm run build --prefix driver-app
# ok

npx playwright test tests/ride-transparency-panel.spec.ts
# 2 passed (transparency panel + 409 conflict UI)

npx playwright test tests/trust-mock-off/ride-transparency-conflict.spec.ts -c playwright.trust.config.js
# optional two-driver trust lane (may be flaky on cold start); backend tests cover the same 409 proof
```

## Not built

Dispatch optimizer, nearest-driver, route snapshots, ETA/fare engines, financial ledger, rider/admin apps, payments, heat maps.

## Next small slice

Surface `claim_conflict` summary on the online-idle sheet after a failed claim (persist last conflict ride id in cockpit state from transparency) and add `marketplace_ledger_events` IDs to `audit.ledger_event_ids` when querying transparency.
