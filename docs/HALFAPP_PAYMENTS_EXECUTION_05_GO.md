# HALFAPP_PAYMENTS_EXECUTION_05 — GO (Phase 5: Transfers + Payout Visibility)

**Status:** GO (repo-grounded)  
**Date:** 2026-05-22  
**Companion:** `docs/CURRENT_TRUTH.md` (payments lanes), Phase 4 in same file  

**Proof commands:**

```powershell
cd backend
py -3.11 -m pytest tests/test_payout_ingestion_phase5.py tests/test_payment_reconciliation_phase4.py -q

cd ..\driver-app
npm test
```

---

## Scope (Phase 5)

- Provider transfer ingestion (Stripe Connect `tr_*`)
- Provider payout ingestion (connected-account `po_*`)
- Payout → transfer linkage via balance transactions on connected account
- Driver payout visibility endpoints + reconciliation enrichment
- UI payout section (`BETA_PAYOUT_*` copy only)
- Signed webhooks + event dedupe preserved
- Targeted tests pass

## NOT in scope (explicit)

- Bank deposit confirmation / “deposited to bank” / “sent to your bank” claims
- Ledger rewrite (`settlement_entries` remains obligation truth)
- Payout initiation / scheduling controls
- MapHome mount changes

---

## GO ritual (checklist)

### A) Schema

- [x] Migrations `0020`–`0023` applied at head `0023_stripe_payout_transfers`
  - `payment_execution.external_charge_id` — `backend/alembic/versions/0020_payment_execution_charge_id.py`
  - `stripe_transfers` — `0021_stripe_transfers.py`
  - `stripe_payouts` — `0022_stripe_payouts.py`
  - `stripe_payout_transfers` — `0023_stripe_payout_transfers.py`

### B) Webhooks (security + gating)

- [x] Dual secret verification: `STRIPE_WEBHOOK_SECRET` + optional `STRIPE_CONNECT_WEBHOOK_SECRET` — `backend/routes/payments_webhooks.py`
- [x] `record_event_once` before processing — unchanged dedupe path
- [x] `PAYOUTS_ENABLED` gates `transfer.*` / `payout.*` ingestion — `backend/services/stripe_client.py`
- [x] `payment_intent.succeeded` sets `external_charge_id` (`ch_*`) when present
- [x] Connect events use top-level `event.account` for connected-account payouts

### C) Ingestion (minimum)

- [x] `stripe_transfer_ingest.ingest_transfer` → `stripe_transfers`, links `ch_*` → `payment_execution`
- [x] `stripe_payout_ingest.ingest_payout` → `stripe_payouts` (scoped by `stripe_account_id`)
- [x] `map_payout_to_transfers_via_balance_transactions` → `stripe_payout_transfers`
- [x] Driver APIs filter by `DriverStripeAccount` for logged-in driver only — no cross-driver leakage

### D) API surface

- [x] `GET /drivers/me/payouts` — `backend/routes/drivers.py`
- [x] `GET /drivers/me/payment-reconciliation` enriched with:
  - `payout_paid_cents` (status `paid`)
  - `payout_pending_cents` (status `pending`, `in_transit`)
  - `provider_payout_visible` — **true when `PAYOUTS_ENABLED=1` and driver has a Connect account row** (amounts may be zero)

### E) Frontend (beta-safe)

- [x] Payout section renders only when `data.provider_payout_visible` — `driver-app/src/components/EarningsVisibilityPanel.jsx`
- [x] `BETA_PAYOUT_*` keys — `driver-app/src/utils/betaTruthCopy.js`
- [x] `driverAPI.getPayouts()` — `driver-app/src/utils/api.js`
- [x] `assert-no-money-claims.mjs` PASS (driver-facing scan + allowlist)

### F) Tests

- [x] `backend/tests/test_payout_ingestion_phase5.py` (9 tests: visibility lock + Phase 5.1 failed/last/contract)
- [x] `backend/tests/test_payment_reconciliation_phase4.py`
- [x] `driver-app/tests/unit/earningsVisibilityPanel.test.js`
- [x] `npm test` → unit tests + `assert-no-ai-providers` + `assert-no-money-claims`

---

## UI contract: `GET /drivers/me/payment-reconciliation`

Stable keys the driver app consumes (Phase 4 + 5). Amounts are integer cents.

```json
{
  "driver_id": 42,
  "pricing_earned_cents": 2650,
  "execution_collected_cents": 3000,
  "execution_refunded_cents": 0,
  "execution_disputed_cents": 0,
  "execution_pending_collection_cents": 0,
  "execution_refundable_cents": 3000,
  "execution_net_collected_cents": 3000,
  "collected_cents": 3000,
  "refunded_cents": 0,
  "disputed_cents": 0,
  "pending_cents": 0,
  "available_cents": 3000,
  "payout_paid_cents": 0,
  "payout_pending_cents": 0,
  "payout_failed_cents": 0,
  "payout_last_status": null,
  "payout_last_at": null,
  "provider_payout_visible": true,
  "provider_stripe_account_id": "acct_xxx",
  "display_note": "Shows processed and pending payment execution amounts from the provider. Not a bank deposit, payout guarantee, or instant transfer.",
  "truth_labels": [
    "pricing_earned_is_obligation_not_payout",
    "execution_collected_is_psp_not_bank_deposit",
    "payment_execution_not_implemented_in_audit_copy"
  ]
}
```

**`provider_payout_visible` rule (locked by tests):**

- `true` iff `PAYOUTS_ENABLED=1` **and** driver has `DriverStripeAccount` row
- Independent of `payout_paid_cents` / `stripe_payouts` row count

When `provider_payout_visible` is false, payout keys are `0` and `provider_stripe_account_id` is omitted.

---

## Truth boundary (unchanged + Phase 5 addition)

| Field | Meaning |
|-------|---------|
| `pricing_earned_cents` | Locked obligation (`ride_pricing`) |
| `collected_cents` / `available_cents` | PSP execution truth (Phase 4) |
| `payout_paid_cents` | Sum of Stripe payout rows with status `paid` on driver's connected account |
| `payout_pending_cents` | Sum with status `pending` or `in_transit` |
| `payout_failed_cents` | Sum with status `failed` (Phase 5.1) |
| `payout_last_status` | Status of latest payout row for connected account, or `null` |
| `payout_last_at` | ISO timestamp from latest row (`created_at`, else `arrival_date`) |

**UI must never claim:** deposited, sent to bank, received in bank, instant payout to bank.

Trip audit copy remains `payment_execution: not_implemented` for payout execution product claims.

---

## Ops enablement (staging)

1. `PAYMENTS_ENABLED=1`
2. `PAYOUTS_ENABLED=1`
3. `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` (platform endpoint)
4. `STRIPE_CONNECT_WEBHOOK_SECRET` (Connect-scoped endpoint, if separate)
5. Stripe Dashboard — Connect webhook subscribe:
   - `transfer.created`, `transfer.updated`, `transfer.reversed`
   - `payout.created`, `payout.paid`, `payout.failed`, `payout.canceled`
6. Platform webhook — keep:
   - `payment_intent.*`, refund events, `charge.dispute.*`

**Webhook staging logs:** each verified event logs  
`stripe_webhook_verified event_id=… event_type=… verified_via=platform|connect connect_account_present=true|false`  
(`backend/routes/payments_webhooks.py`) — use to confirm Connect events hit the right endpoint/secret.

See `backend/.env.example` for variable names.

### Smoke checks (no real payout required)

1. Test driver with Connect row + `PAYOUTS_ENABLED=1` → `provider_payout_visible=true`, payout cents may be `0`
2. Send test `payout.created` webhook with `account=acct_*` → row in `GET /drivers/me/payouts`
3. `npm test` → money-claim guard still PASS

---

## Rollback (safe)

- Set `PAYOUTS_ENABLED=0` — stops transfer/payout ingestion; Phase 4 execution visibility unchanged
- UI hides payout section when `provider_payout_visible` is false
- No migration rollback required for truth safety (read-only visibility tables)

---

## PR body (copy-paste)

```markdown
## HALFAPP_PAYMENTS_EXECUTION_05 — Phase 5 GO (Transfers + Payout Visibility)

### Why
Adds Stripe Connect transfer + payout ingestion and exposes provider payout visibility to drivers, while preserving HalfApp truth boundaries (pricing obligations ≠ PSP executions ≠ bank deposits).

### Backend
- Migrations `0020`–`0023`: `external_charge_id`, `stripe_transfers`, `stripe_payouts`, `stripe_payout_transfers`
- `stripe_transfer_ingest.py`, `stripe_payout_ingest.py` (balance-tx mapping on connected account)
- Webhooks: dual secrets; `payment_intent.succeeded` → `ch_*`; `transfer.*` / `payout.*` when `PAYOUTS_ENABLED`
- `GET /drivers/me/payouts`; reconciliation + `payout_paid_cents`, `payout_pending_cents`, `provider_payout_visible`

### Frontend
- `driverAPI.getPayouts()`; `EarningsVisibilityPanel` payout section; `BETA_PAYOUT_*` copy

### Semantics
- `payout_paid_cents` = Stripe payout status `paid` — NOT bank deposit confirmation
- No “deposited” / “sent to bank” UI claims

### Tests
- `test_payout_ingestion_phase5.py`, Phase 4 reconciliation tests, `npm test` + money-claim guard

### Out of scope
Bank deposit confirmation; payout initiation; ledger rewrite
```

---

## Release notes (changelog snippet)

```markdown
### Payments (Phase 5)
- Provider payout visibility for drivers with Stripe Connect (gated: `PAYOUTS_ENABLED`).
- Transfer and payout ingestion with payout→transfer linkage via balance transactions.
- UI shows provider payout status only; does not claim bank deposit confirmation.
```

---

## File index

| Area | Path |
|------|------|
| Webhooks | `backend/routes/payments_webhooks.py` |
| Reconciliation | `backend/services/payment_reconciliation.py` |
| Models | `backend/models/stripe_transfer.py`, `stripe_payout.py`, `stripe_payout_transfer.py` |
| Routes | `backend/routes/drivers.py` (`/me/payouts`, enriched reconciliation) |
| UI | `driver-app/src/components/EarningsVisibilityPanel.jsx` |
| Copy | `driver-app/src/utils/betaTruthCopy.js` |
| CI guard | `driver-app/scripts/assert-no-money-claims.mjs` |
