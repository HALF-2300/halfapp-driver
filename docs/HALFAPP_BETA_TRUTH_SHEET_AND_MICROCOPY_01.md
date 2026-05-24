# HalfApp Driver — Beta Truth Sheet & Microcopy

**Order:** `HALFAPP_BETA_TRUTH_SHEET_AND_MICROCOPY_01`  
**Date:** 2026-05-23  
**Audience:** Trusted drivers in the no-money comprehension beta  
**Canonical code:** `driver-app/src/utils/betaTruthCopy.js`  
**Enable in-app notices:** `VITE_BETA_NO_MONEY_TRUTH=true` at driver-app build time

---

## One-page beta truth sheet

### What this beta is

HalfApp Driver is running a **trusted, no-money comprehension beta**. You exercise the real driver cockpit, ride lifecycle, pricing ledger, trip audit, and route truth surfaces so we can validate that drivers **understand** how the system works — not that money moves.

You may:

- Go online and receive **test or ops-created rides**
- Accept rides on an **open board** (first claim wins)
- Complete the full lifecycle on a map-first cockpit
- View **test earnings** and **recorded obligations** after completion
- Open **trip audit / receipt** and **route truth** for transparency

### What this beta is not

This beta is **not**:

- A public marketplace launch
- A paid pilot or payment test
- Rider billing or driver payouts
- Proof that every route is a live road-network path
- A guarantee that production Postgres concurrency is fully proved

There is **no PSP**, **no wallet**, **no cash-out**, and **no bank settlement** in this build.

### Money truth (read this first)

| Statement | Meaning |
|-----------|---------|
| **No rider charges. No driver payouts.** | HalfApp does not collect from riders or send money to drivers in this beta. |
| **Test earnings (not paid)** | Dollar amounts on Earnings and completed trips are **calculation records** from the backend pricing ledger. |
| **Recorded obligation (testing only)** | Settlement rows describe what the backend **would** record — not money sent. |
| **This is a calculation record. No payout has been sent.** | Completing a ride locks integer-cent pricing; nothing is transferred to your bank. |

### How rides appear

- **Test rides / ops-created rides** — Created via simulation flags or operations tools for validation. Labeled in-app when `lifecycle_reason` is `simulation`, `ops_*`, `beta_*`, or `test_*`.
- **Open-board dispatch** — Rides can appear to **multiple drivers at once**. **First successful claim wins**; others receive a claim conflict (409) with an honest message.

### Route truth

| Label | When to use |
|-------|-------------|
| **Straight-line estimate** | Backend used `haversine_fallback` or `used_fallback` is true. Distance/time are approximate — not a proved road path. |
| **Road-network route** | Only when OSRM runtime proof is **GO** on the host (`osrm_runtime_claim: proved_portland_v0_1`). **Today default: OSRM runtime not proved.** |

The map is a visualization surface. **Route provider metadata comes from the backend**, not from drawing alone.

### Recorded obligation meaning

After completion, the backend may write **settlement obligation rows** (`settlement_entries`). These are:

- Integer-cent amounts the ledger computed
- Status such as `pending` — **not** “paid” or “deposited”
- Shown on trip audit under **Settlement obligations**

`payment_execution` remains **`not_implemented`**.

### When you are confused

1. Re-read this sheet and the in-app banner (when beta flag is on).
2. Open **Trip audit** for the ride — check pricing, obligations, route truth, and technical proof.
3. Remember: **if it sounds like a payment, it is not** — contact support before assuming money moved.

### Support channel (placeholder)

**Beta support:** `[support channel — ops to configure]`  
Ops should replace the placeholder in `BETA_SUPPORT_PLACEHOLDER` before inviting external drivers.

---

## In-app microcopy by surface

Strings below are implemented in `betaTruthCopy.js` and wired to UI when `VITE_BETA_NO_MONEY_TRUTH=true` (banner, first-run ack, earnings) or always (incoming ride open-board note, claim conflict, route fallback labels).

| Surface | Element | String |
|---------|---------|--------|
| **Onboarding / first-run** | Title | Before you drive — beta truth |
| | Checkbox | I understand this is a no-money comprehension beta. |
| | CTA | Continue to cockpit |
| | Blocks | See `BETA_DRIVER_ACKNOWLEDGMENT_BLOCKS` in code |
| **Cockpit banner** | Title | Trusted driver beta — comprehension only |
| | Headline | No rider charges. No driver payouts. |
| | Body | Operational truth beta: lifecycle, pricing ledger, and audit — not a marketplace launch or paid pilot. |
| **Incoming ride sheet** | Eyebrow | Incoming ride · open board |
| | Estimate label | Est. test earnings |
| | Hint | (not paid) |
| | Note | Open board: rides appear to multiple drivers; first claim wins. |
| **Completed ride sheet** | Note | This is a calculation record. No payout has been sent. |
| **Earnings screen** | Subtitle | Test earnings from completed backend rides — calculation records only, not payouts. |
| | Hero note | Test earnings (not paid) · This is a calculation record. No payout has been sent. |
| **Trip audit page** | Disclaimer | Obligation rows record backend-computed amounts — not bank or PSP movement. |
| | Obligation label | Recorded obligation (testing only) — backend accounting only, not payment execution. |
| | Settlement section | Obligation recorded — not payout execution. |
| **Route truth section** | Fallback label | Straight-line estimate |
| | Fallback note | Straight-line estimate — not a live road-network route. |
| | OSRM default | OSRM runtime not proved |
| | Proved label | Road-network route (only when runtime claim is proved) |
| **Claim conflict** | Headline | Ride already claimed |
| | Body | Another driver accepted this ride first. Open board dispatch — first claim wins. |
| **Simulation / beta ride** | Simulation | Beta ride / simulation ride — for product testing only. |
| | Ops/test | Ops-created test ride — for product testing only. |

---

## Forbidden wording list

Do **not** use these in **driver-visible** product copy unless PSP/payment execution is implemented and documented as GO:

| Forbidden phrase | Preferred alternative |
|------------------|----------------------|
| paid (alone, implying transfer) | Test earnings (not paid) |
| paid out | Recorded obligation (testing only) |
| payout sent | No payout has been sent |
| deposited | Calculation record / not deposited |
| cash out | (omit — no wallet UI) |
| wallet | (omit) |
| available balance | Test earnings total |
| instant pay | (omit) |
| payment processed | Payment execution: not_implemented |
| bank settled | Not bank or PSP movement |

**Allowlisted substrings** (scanner ignores): `not paid`, `no payout`, `no driver payouts`, `no rider charges`, `testing only`, `not payout execution`.

Enforced in:

- `BETA_FORBIDDEN_PAYMENT_PHRASES` + `containsBetaForbiddenPaymentLanguage()` — `betaTruthCopy.js`
- `tripAuditFormat.containsForbiddenPaymentLanguage()` — re-exports beta list
- `cockpitLayout.test.js` — repo-wide grep for select phrases in `driver-app/src`

---

## Route wording lock

| Condition | Required label | Forbidden |
|-----------|----------------|-----------|
| `haversine_fallback` / `used_fallback: true` | **Straight-line estimate** | production OSRM, road-accurate, live road network proof |
| `osrm_runtime_claim: not_proved` | **OSRM runtime not proved** | “Production routing live” |
| `osrm_runtime_claim: proved_portland_v0_1` | **Road-network route** (Portland evidence on file) | Generic “always road-accurate” |

---

## Money wording lock

| UI area | Required framing |
|---------|------------------|
| Earnings totals | Test earnings (not paid) |
| Incoming estimate | Est. test earnings (not paid) |
| Trip audit headline | Recorded obligation (testing only) |
| Settlement rows | Obligation recorded — not payout execution |
| Global banner | No rider charges. No driver payouts. |

Internal API/field names (e.g. `driver_payout_cents`) may remain in technical JSON; **user-facing sentences** must follow the table above.

---

## Remaining beta gates (not closed by this order)

| Gate | Status |
|------|--------|
| OSRM runtime on Docker/VPS | **NO_GO** — `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` |
| Postgres claim-race proof | **NO_GO** — not observed in production DB |
| Dossier spine wired to driver-app | **NO** — parallel path only |
| PSP / payout execution | **NO** — by design for this beta |
| Rider mobile app | **NO** — API/simulation only |

---

## Build flag

```bash
# driver-app/.env.local (example)
VITE_BETA_NO_MONEY_TRUTH=true
```

Without this flag, first-run acknowledgment and cockpit/earnings banners are hidden; core honesty strings on incoming rides, claim conflicts, audit, and route truth remain active where wired.
