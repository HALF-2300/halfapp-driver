# Final Report: HALFAPP_BETA_TRUTH_SHEET_AND_MICROCOPY_01

**Verdict: GO**  
**Date:** 2026-05-23  
**Scope:** Driver-facing beta truth sheet, canonical microcopy, forbidden-phrase lock, and in-app wiring for trusted no-money comprehension beta — **no PSP, wallet, dossier, rider app, or false routing/payout claims.**

---

## Summary

Trusted drivers now have a **one-page truth sheet** (`docs/HALFAPP_BETA_TRUTH_SHEET_AND_MICROCOPY_01.md`), a **single code source** for strings and guards (`driver-app/src/utils/betaTruthCopy.js`), and **wired UI copy** on cockpit, incoming/completed ride sheets, earnings, trip audit, route truth, and claim conflict. Money and route wording align with current product truth: pricing ledger + obligation rows only, open-board dispatch, straight-line fallback when OSRM runtime is not proved.

**Build flag for banner + first-run ack:** `VITE_BETA_NO_MONEY_TRUTH=true`

---

## Files changed

| Area | File | Role |
|------|------|------|
| **Docs** | `docs/HALFAPP_BETA_TRUTH_SHEET_AND_MICROCOPY_01.md` | Truth sheet + microcopy table + locks |
| **Docs** | `docs/HALFAPP_BETA_TRUTH_SHEET_AND_MICROCOPY_01_REPORT.md` | This report |
| **Copy constants** | `driver-app/src/utils/betaTruthCopy.js` | Canonical strings, forbidden list, routing helpers |
| **UI** | `driver-app/src/components/BetaFirstRunAck.jsx` | First-run acknowledgment modal |
| **UI** | `driver-app/src/components/BetaTruthNotice.jsx` | Cockpit / earnings banner variants |
| **UI** | `driver-app/src/components/TestRideLabel.jsx` | (existing) simulation/ops labels |
| **UI** | `driver-app/src/components/MapHome.jsx` | Cockpit banner + first-run ack |
| **UI** | `driver-app/src/components/Earnings.jsx` | Beta subtitle + test earnings note |
| **UI** | `driver-app/src/components/TripAuditReceipt.jsx` | Audit obligation copy + test ride label |
| **UI** | `driver-app/src/components/cockpit/RideRequestCard.jsx` | Open board + est. test earnings |
| **UI** | `driver-app/src/components/cockpit/ClaimConflictNotice.jsx` | Open-board conflict copy |
| **UI** | `driver-app/src/components/cockpit/MarketplaceBottomSheet.jsx` | Completed trip beta note + test label |
| **UI** | `driver-app/src/components/cockpit/RouteTruthDetails.jsx` | Straight-line estimate helpers |
| **Utils** | `driver-app/src/utils/routeTruthFormat.js` | Fallback label → Straight-line estimate |
| **Utils** | `driver-app/src/utils/tripAuditFormat.js` | Forbidden list from betaTruthCopy |
| **Backend copy** | `backend/services/ride_audit.py` | AUDIT_COPY + `lifecycle_reason` on audit |
| **Backend copy** | `backend/services/route_snapshots_read.py` | Straight-line routing labels |
| **Tests** | `driver-app/tests/unit/betaTruthCopy.test.js` | Forbidden allowlist + routing label |
| **Tests** | `driver-app/tests/route-truth-flow-ui-proof.spec.ts` | Straight-line estimate assertions |
| **Tests** | `backend/tests/test_driver_ride_audit.py` | Obligation (testing only) label |
| **Tests** | `backend/tests/test_route_snapshot_read_ui.py` | Straight-line routing_label |

**Not changed (by design):** PSP, wallet/cashout UI, dossier wiring, rider app, Postgres claim-race proof, OSRM runtime proof.

---

## Final beta truth sheet text

See **`docs/HALFAPP_BETA_TRUTH_SHEET_AND_MICROCOPY_01.md`** (full one-pager). Core statements:

- **What it is:** Comprehension / operational truth beta — real lifecycle, pricing ledger, audit, route truth; no money movement.
- **What it is not:** Marketplace launch, paid pilot, PSP, wallet, production OSRM guarantee, Postgres race proof.
- **Money:** No rider charges. No driver payouts. Test earnings (not paid). Recorded obligation (testing only).
- **Dispatch:** Open board; first claim wins; test/ops-created rides labeled.
- **Routing:** Straight-line estimate when fallback; road-network route only when OSRM runtime proved.
- **Support:** Placeholder channel for ops to configure.

---

## Microcopy table

| Surface | Key string(s) | Constant(s) |
|---------|---------------|-------------|
| Onboarding | Before you drive — beta truth; `BETA_DRIVER_ACKNOWLEDGMENT_BLOCKS` | `BetaFirstRunAck.jsx` |
| Cockpit banner | No rider charges. No driver payouts. | `BETA_COCKPIT_*`, `BetaTruthNotice` variant `cockpit` |
| Incoming ride | Incoming ride · open board; Est. test earnings (not paid) | `BETA_INCOMING_*`, `RideRequestCard` |
| Completed ride | This is a calculation record. No payout has been sent. | `BETA_COMPLETED_TRIP_NOTE` |
| Earnings | Test earnings from completed backend rides… | `BETA_EARNINGS_SUBTITLE`, `BETA_CALCULATED_VALUE_LABEL` |
| Trip audit | Recorded obligation (testing only)… | `BETA_AUDIT_*` |
| Route truth | Straight-line estimate | `BETA_STRAIGHT_LINE_*`, `betaRoutingLabelFromPayload` |
| Claim conflict | Ride already claimed; open board — first claim wins | `BETA_CLAIM_CONFLICT_*` |
| Simulation | Beta ride / simulation ride… | `BETA_SIMULATION_RIDE_LABEL` |

---

## Forbidden wording lock

| Mechanism | Status |
|-----------|--------|
| `BETA_FORBIDDEN_PAYMENT_PHRASES` | paid out, payment processed, payout sent, deposited, cash out, wallet, available balance, instant pay, bank settled, stripe |
| `BETA_FORBIDDEN_PAYMENT_ALLOWLIST` | not paid, no payout, testing only, etc. |
| `containsBetaForbiddenPaymentLanguage()` | Unit-tested |
| `cockpitLayout.test.js` | Greps `driver-app/src` for paid out, payment processed |
| Forbidden scan (2026-05-23) | **Clean** in product components; only `betaTruthCopy.js` (list + ack text) and engineering-intelligence guard strings |

---

## Route wording lock

| Condition | Label |
|-----------|--------|
| `used_fallback` / `haversine_fallback` | **Straight-line estimate** (+ note: not a live road-network route) |
| `osrm_runtime_claim: not_proved` | **OSRM runtime not proved** |
| `osrm_runtime_claim: proved_portland_v0_1` | **Road-network route** (UI helper only; runtime still NO_GO globally) |

Forbidden in driver copy: `production osrm`, `road-accurate`, `live road network proof` — guarded by `containsBetaForbiddenRoutingClaim` / route E2E spec.

---

## Money wording lock

| Surface | Required framing |
|---------|------------------|
| Earnings hero | Test earnings (not paid) |
| Incoming estimate | Est. test earnings · (not paid) |
| Trip audit | Recorded obligation (testing only); settlement: Obligation recorded — not payout execution |
| Banner | No rider charges. No driver payouts. |
| Backend audit `copy.driver_payment_label` | Recorded obligation (testing only) |

Internal field names (`driver_payout_cents`, `RidePayoutSummary` breakdown labels) remain ledger terminology in technical breakdowns; user-facing sentences use the lock above.

---

## Remaining beta gates

| Gate | Status |
|------|--------|
| OSRM runtime (Docker/VPS) | **NO_GO** |
| Postgres claim-race proof | **NO_GO** (not marked GO) |
| Dossier spine in driver-app | **PARALLEL_NOT_WIRED** |
| PSP / payout execution | **NO_GO** (intentional) |
| Rider mobile app | **NO** |
| Ops support channel | **Placeholder** — replace `BETA_SUPPORT_PLACEHOLDER` before external beta |

---

## Commands run

```powershell
cd driver-app; npm test
# 86 passed, assert-no-ai-providers: OK

cd backend; py -3.11 -m pytest tests/test_route_snapshot_read_ui.py tests/test_driver_ride_audit.py -q
# 7 passed
```

**Forbidden phrase scan:** `rg` on `driver-app/src/**/*.{js,jsx}` for payout sent, wallet, payment processed, etc. — only expected hits in `betaTruthCopy.js` (forbidden list + acknowledgment) and `engineeringIntelligenceContext.js` (guard string, excluded from product paths).

---

## Verdict

**GO** — Beta truth sheet and microcopy are documented, centralized in `betaTruthCopy.js`, enforced by unit tests and existing layout guards, and wired to primary driver surfaces without implying payments, production OSRM, or Postgres proof GO. Enable `VITE_BETA_NO_MONEY_TRUTH=true` for cockpit banner and first-run acknowledgment before inviting trusted external drivers.
