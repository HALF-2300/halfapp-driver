# HALFAPP_PAYMENTS_EXECUTION_05_1 — GO (Phase 5.1: Payout accuracy polish)

**Status:** GO  
**Parent:** `docs/HALFAPP_PAYMENTS_EXECUTION_05_GO.md`  
**Date:** 2026-05-22  

## Scope

Adds three reconciliation fields (no schema change, no semantics drift):

| Field | Meaning |
|-------|---------|
| `payout_failed_cents` | Sum of `stripe_payouts` with `status=failed` on driver's connected account |
| `payout_last_status` | Status of most recent payout row, or `null` |
| `payout_last_at` | ISO time from latest row (`created_at`, else `arrival_date`), or `null` |

Still **not** bank deposit confirmation.

## Code

- `backend/services/payment_reconciliation.py` — `enrich_reconciliation_with_payouts()`
- `driver-app/src/components/EarningsVisibilityPanel.jsx` — failed + last status/time rows
- `driver-app/src/utils/betaTruthCopy.js` — `BETA_PAYOUT_FAILED_*`, `BETA_PAYOUT_LAST_*`

## Tests

- `test_reconciliation_includes_failed_and_last_payout_fields`
- `test_reconciliation_payout_contract_keys_when_visible`
- Visibility test asserts `payout_last_*` null when no rows
- Frontend: `earningsVisibilityPanel.test.js` — failed/last row test IDs

```powershell
py -3.11 -m pytest backend/tests/test_payout_ingestion_phase5.py -q
cd driver-app && npm test
```
