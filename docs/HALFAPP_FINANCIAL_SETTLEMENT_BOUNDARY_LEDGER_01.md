# HALFAPP_FINANCIAL_SETTLEMENT_BOUNDARY_LEDGER_01

**Date:** 2026-05-22  
**Scope:** Internal settlement boundary from locked `ride_pricing` — not payments, payouts, or PSP integration.

---

## Verdict

**GO**

---

## What changed

| Area | Change |
|------|--------|
| Model | `backend/models/settlement_entry.py` — `settlement_entries` table |
| Migration | `0011_settlement_entries_foundation` |
| Service | `backend/services/ride_settlement.py` — idempotent generation, immutability via DB unique + locked rows |
| Wiring | `POST /drivers/complete-ride/{id}` generates settlement after pricing lock + complete route snapshot |
| API | `GET /drivers/rides/{ride_id}/settlement` (read-only, driver-scoped) |
| Tests | `backend/tests/test_ride_settlement_ledger.py` (9 tests) |

---

## Settlement entry types

| `entry_type` | `party` | Source field |
|--------------|---------|--------------|
| `customer_charge_obligation` | `rider` | `customer_total_cents` |
| `driver_payout_obligation` | `driver` | `driver_ride_payout_cents` (80% shareable; excludes tip line) |
| `platform_commission` | `platform` | `platform_commission_cents` |
| `platform_service_fee` | `platform` | `platform_service_fee_cents` ($1.50 default) |
| `platform_revenue` | `platform` | `platform_revenue_cents` (commission + service fee) |
| `tip_payable_to_driver` | `driver` | `tip_cents` (only if > 0) |
| `city_fee_liability` | `city` | `city_fee_cents` (if > 0) |
| `airport_fee_liability` | `airport` | `airport_fee_cents` (if > 0) |
| `toll_liability` | `toll_authority` | `toll_cents` (if > 0) |
| `accessibility_fee_liability` | `accessibility_authority` | `accessibility_fee_cents` (if > 0) |
| `tax_liability` | `tax_authority` | `tax_cents` (if > 0) |

Pass-through liabilities are **not** platform revenue and **not** driver ride payout unless separately reimbursed (tolls reimbursement not in v0.1 settlement slice).

---

## Display field meanings

| Field | Meaning |
|-------|---------|
| `Ride.fare_amount` | **Driver earnings display** (`driver_earnings_cents` / total payout), not customer charge |
| `CompleteRideResponse.fare_earned` | Same as driver total payout on complete |
| `ride_pricing.customer_total_cents` | Customer charge obligation source |

---

## Idempotency

- `UNIQUE (ride_id, entry_type)` on `settlement_entries`
- `generate_settlement_entries()` returns existing rows if any entry exists for the ride
- Re-running after complete does not insert duplicates

## Immutability

- Rows written once with `locked_at` at creation
- No update/delete API
- Duplicate `(ride_id, entry_type)` raises `IntegrityError`

---

## Verification

```powershell
cd backend
python -m pytest -q
# 145 passed (includes pricing, route snapshot, settlement suites)

cd ..\driver-app
npm run build
npm test
npm run test:e2e:ride-flow
npm run test:e2e:trust
```

---

## Intentionally not built

- Stripe / card capture / bank payouts
- Insurance, PBOT export, Checkr
- OSRM runtime, Google/Mapbox APIs
- Surge pricing, UI redesign
- Settlement mutation or manual mark-paid API (status field reserved)

---

## Next tasks (out of scope)

- Payment processor integration
- `manually_marked_paid` workflow with admin controls
- Rider-facing charge receipts
