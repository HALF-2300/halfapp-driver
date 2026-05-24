# Financial ledger — future contract stub

Date: 2026-05-22  
Status: **not implemented** — MVP uses backend earnings summaries and ride-stored `fare_amount` only.

## Principles

1. **Money in integer cents** — no floating-point currency in storage or APIs.
2. **Immutable append-only entries** — corrections are new rows, never in-place edits.
3. **Double-entry later** — accounts, transactions, and balanced entries when payments ship.
4. **Earnings projection from ledger** — driver “today” totals derive from ledger records, not UI math.

## MVP today

- `GET /drivers/earnings` returns backend-computed summaries.
- Cockpit displays `today_earnings` / `today_rides` from API responses only.
- Completed ride flash uses `fare_earned` from transition response when present.

## Future tables (illustrative)

| Entity | Purpose |
|--------|---------|
| `accounts` | Driver platform, rider, escrow, revenue |
| `transactions` | Idempotent business event (trip complete, payout) |
| `entries` | Debit/credit lines in cents, sum to zero per transaction |

## Rejected for this slice

- Stripe/payout UI
- Client-side fare invention
- Replacing marketplace audit events with payment ledger rows prematurely
