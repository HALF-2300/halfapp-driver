# Dispatch concurrency contract (future Postgres note)

Date: 2026-05-22  
Status: **contract stub** — current MVP uses SQLite-compatible atomic updates.

## Rules

1. **First-claim-wins** — exactly one driver may transition `requested` → `accepted` for a given ride.
2. **Conflict response** — losing concurrent claims receive **HTTP 409** with a stable machine-readable reason (e.g. `ride_already_claimed`).
3. **No double-booking** — `driver_id` must not be set twice; assigned rides are exclusive.
4. **Audit** — every attempt records `claim_attempted`; outcomes record `claim_won` / `claim_lost` in marketplace ledger events.

## Current implementation (MVP)

- Accept ride uses a transactional update on the active DB session.
- Tests: `backend/tests/test_ride_lifecycle.py` (`test_open_board_first_claim_wins_with_conflict_for_loser`), `backend/tests/test_dispatch_auditability.py`.

## Future Postgres implementation

When the active database is PostgreSQL and dispatch volume requires row-level locking:

```sql
-- Illustrative pattern only — adapt to ORM/session in backend
SELECT id FROM rides
WHERE id = :ride_id AND status = 'requested' AND driver_id IS NULL
FOR UPDATE SKIP LOCKED;
```

Equivalent requirements:

- Run claim inside a single transaction.
- Skip rows already locked by another worker instead of blocking indefinitely.
- Commit only if the update row count is 1; otherwise return 409.

Do **not** introduce Redis/Kafka claim queues until the repo explicitly scopes them.

## Client behavior

- On 409, clear stale local selection and refresh `GET /drivers/available-rides`.
- Never treat a failed accept as a successful assignment.
