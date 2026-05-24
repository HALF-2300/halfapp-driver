# HALFAPP Trusted No-Money Beta — Truth Boundary Pack 01

> **DEFERRED (2026-05-23 direction reset):** External trusted-driver beta, beta onboarding, and beta launch copy are **not in scope**. Active planning: `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`. Keep this file as reference only; do not enable `VITE_BETA_NO_MONEY_TRUTH` or invite outside drivers unless leadership re-opens the lane.

Date: 2026-05-23  
Order: `HALFAPP_TRUSTED_NO_MONEY_BETA_BOUNDARY_PACK_01`  
Verdict target: **ARCHIVED / DEFERRED**  
Status: **Not active** — superseded by product-completion roadmap for internal owner-car testing only.

---

## What this beta is (and is not)

| This beta **is** | This beta **is not** |
|------------------|----------------------|
| Controlled **operational truth / usability** beta with trusted drivers | Marketplace launch |
| Backend lifecycle, pricing ledger, trip audit, route truth UI validation | Paid pilot |
| Honest dollar-like **calculated test values** with explicit no-money labels | PSP / payment / payout testing |
| Open-board dispatch comprehension (first claim wins) | Public waitlist or marketing campaign |
| Ops/support supervised rides | Rider app |

**Canonical build flag (driver app):** `VITE_BETA_NO_MONEY_TRUTH=true`  
**Canonical copy module:** `driver-app/src/utils/betaTruthCopy.js`  
**First-run acknowledgment UI:** `driver-app/src/components/BetaFirstRunAck.jsx` (localStorage; server ack is ops-owned)

Companion truth (unchanged):

- `docs/PRODUCT_BOUNDARY_STAGE0.md`
- `docs/CURRENT_TRUTH.md`
- `docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md`
- `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md`

---

## 1. Beta truth boundary (program)

### Current HalfApp truth (pre-invite baseline)

| Lane | Status | Beta implication |
|------|--------|----------------|
| Driver cockpit | **GO** | In scope |
| Ride-flow E2E | **GO** | In scope |
| Trip audit / receipt UI | **GO** | In scope; obligation language required |
| Route truth UI | **GO** | In scope; fallback/OSRM honesty required |
| Pricing ledger | **GO** | In scope as **calculated test values** only |
| Settlement obligation rows | **GO (boundary)** | In scope as **recorded obligation**, not payout |
| PSP / payment / payout execution | **NO_GO** | **Forbidden** in beta |
| OSRM runtime | **NO_GO** | Do not claim road-network truth |
| Postgres claim-race proof | **Not observed** | Do not claim DB concurrency GO |
| Dossier spine | **PARALLEL_NOT_WIRED** | **Quarantined** (§9) |

### Required boundary sentences (use verbatim in driver-facing material)

1. **No money will be collected or paid through HalfApp during this beta.**
2. **Values shown are calculated test values for system validation.**
3. **Recorded obligation does not mean payout.**
4. **Route may be an estimate/fallback unless OSRM runtime proof is GO.**
5. **Beta ride / simulation ride — for product testing only.** (simulation / dev-created rides)

### Dollar display policy

- **Do not** replace all currency UI with fake credits/STU unless the product owner explicitly approves.
- **Do** keep integer-cent / dollar formatting from `ride_pricing` and label it:  
  **Calculated test value — no money collected or paid.**

### Forbidden implementation during beta (no exceptions without new order)

- PSP implementation, payment UI, wallet, cash-out
- Rider app
- Dossier wiring into `driver-app`
- Dispatch rewrite (open board stays)
- Production OSRM claim without runtime GO doc
- Postgres claim-race GO claim without observed proof
- Public marketing / waitlist copy implying paid rides or payouts

---

## 2. Driver onboarding / acknowledgment copy

**Channel:** Email or ops doc + in-app first-run modal (`BetaFirstRunAck` when `VITE_BETA_NO_MONEY_TRUTH=true`).

**Subject (ops email):** HalfApp trusted driver beta — operational truth only (no payments)

**Body blocks** (same order as `BETA_DRIVER_ACKNOWLEDGMENT_BLOCKS` in `betaTruthCopy.js`):

1. No rider charges. No driver payouts.
2. No money will be collected or paid through HalfApp during this beta.
3. Values shown are calculated test values for system validation — not money received or sent.
4. Recorded obligation does not mean payout.
5. This is a calculation record. No payout has been sent.
6. This is an operational truth and usability beta — not a marketplace launch, paid pilot, or payment test.
7. Open board: rides appear to multiple drivers; first claim wins.
8. Route may be an estimate/fallback unless OSRM runtime proof is GO.
9. I will not describe dollar amounts in the app as money received, deposited, or paid out.

**Checkbox label (in-app):** I understand this is a no-money comprehension beta.

**Confirm button:** Continue to cockpit

**Ops record (minimum):** driver user id, ack timestamp, beta pack version `01`, channel (email + in-app).

---

## 3. In-app copy rules (by surface)

| Surface | Rule | Canonical constants |
|---------|------|---------------------|
| **Cockpit** (`MapHome`) | Show `BetaTruthNotice` variant `cockpit` + `BetaFirstRunAck` on first run | `BETA_COCKPIT_BANNER_*`, `BETA_NO_MONEY_*` |
| **Incoming ride** | Eyebrow + estimate labeled as test, not paid | `BETA_INCOMING_RIDE_EYEBROW`, `BETA_INCOMING_ESTIMATE_*` |
| **Claim conflict** | Open-board first-claim-wins; no payment wording | `BETA_CLAIM_CONFLICT_*` |
| **Trips list** | `BetaTruthNotice`; test-ride badge when `lifecycle_reason` matches | `TestRideLabel`, `testRideLabelForLifecycleReason` |
| **Earnings** | `BetaTruthNotice` full; hero totals keep `$` with `BETA_CALCULATED_VALUE_LABEL` when beta flag on | `BETA_EARNINGS_SUBTITLE` |
| **Trip audit** | Obligation + calculated test label; payment execution stays `not_implemented` | `BETA_AUDIT_*`, backend `AUDIT_COPY` |
| **Route truth** | Fallback → straight-line estimate; OSRM status not proved unless doc GO | `BETA_STRAIGHT_LINE_*`, `BETA_ROUTE_ESTIMATE_DISCLAIMER` |
| **Dev simulation FAB** | Only when `VITE_ENABLE_RIDE_SIMULATION=true` (non-prod); label as simulation | `BETA_SIMULATION_RIDE_LABEL` |

**Production trusted-beta build:**

```env
VITE_BETA_NO_MONEY_TRUTH=true
VITE_ENABLE_RIDE_SIMULATION=false
VITE_ALLOW_OFFLINE_MOCK=false
```

---

## 4. Simulation / ops-created ride labeling

| Source | `lifecycle_reason` (examples) | UI label |
|--------|------------------------------|----------|
| Driver dev simulation API | `simulation` | Beta ride / simulation ride — for product testing only. |
| Ops seed / internal scripts | `investor_showcase_seed`, `ops_*`, `beta_*`, `test_*` | Ops-created test ride — for product testing only. |
| Real rider API cancel reason | free text | **No** test badge unless reason matches table above |
| Open-board real ride | null or dispatch reasons | No test badge |

**Ops-created rides (production beta):** create via internal/rider API or approved scripts; set `lifecycle_reason` to an `ops_*` or `beta_*` prefix. Document ride id in the reconciliation log (§8).

**Support must say:** “This was a test ride for system validation — not a paid trip.”

---

## 5. Support / runbook FAQ

| Question | Approved answer |
|----------|-----------------|
| When do I get paid? | No money is collected or paid through HalfApp during this beta. Dollar amounts are calculated test values for system validation only. |
| Why does the app show $ amounts? | The pricing ledger records calculated test values and obligations — not money sent to your bank. |
| What is “recorded obligation”? | A backend accounting row for validation. Recorded obligation does not mean payout. |
| Is the route distance accurate? | It may be a straight-line or fallback estimate unless OSRM runtime proof is GO on this environment. |
| Another driver took my ride | Open board dispatch — first atomic claim wins. This is expected beta behavior. |
| Is this Uber/Lyft? | No. This is a controlled trusted-driver operational beta, not a marketplace launch. |
| Can I cash out / wallet? | No wallet, cash-out, or payout execution exists in this beta. |
| The app said “payment” | Payment execution is not implemented. If copy implies money moved, escalate to engineering — forbidden phrase regression. |
| Simulation / test ride | Beta ride — product testing only; not real rider demand unless ops assigned it. |
| Who do I contact? | `BETA_SUPPORT_PLACEHOLDER` — ops must set channel before invite. |

**Escalation triggers:** driver reports money received/missing; copy contains forbidden phrases (§6); unexpected PSP redirect; dossier/supply/demand URLs in app.

---

## 6. No-money / no-payout forbidden phrase list

**Driver-visible product copy** must not contain these substrings (unless negated per allowlist in `betaTruthCopy.js`):

| Phrase | Notes |
|--------|--------|
| `paid out` | Use “not paid” / obligation language |
| `payment processed` | Use “payment execution: not_implemented” in technical section only |
| `payout sent` | |
| `payout executed` | |
| `deposited` | |
| `cash out` | |
| `wallet` | |
| `available balance` | |
| `instant pay` | |
| `bank settled` | |
| `stripe` | |

**Allowlisted negations (examples):** `not paid`, `no driver payouts`, `no rider charges`, `testing only`, `not payout execution`.

**Automated guards:** `driver-app/tests/unit/betaTruthCopy.test.js`, `cockpitLayout.test.js` (src scan), `audit-flow-ui-proof.spec.ts`.

**Routing forbidden (unchanged):** `production osrm`, `road-accurate`, `live road network proof`.

---

## 7. Beta stop conditions

Stop inviting new drivers and pause the beta if any of the following occur:

1. **Copy regression:** forbidden payment phrase appears in driver-visible UI without fix within 24h.
2. **False money movement:** driver or ops believes funds were collected, held, or paid via HalfApp.
3. **PSP / payment surface:** any payment UI, redirect, or capture attempt ships without explicit order.
4. **Dossier leak:** driver app calls `/supply`, `/demand`, or `/trip` or shows dossier ledger as earnings truth.
5. **Unsafe build:** production build with `VITE_ALLOW_OFFLINE_MOCK`, `VITE_ENABLE_RIDE_SIMULATION`, or guard bypass enabled.
6. **OSRM overclaim:** UI or support states road-network routing is production-proved while runtime doc is NO_GO.
7. **Concurrency overclaim:** marketing/support claims Postgres claim-race proof without observed test artifact.
8. **Uncontrolled demand:** non-trusted riders creating unmanaged load without ops plan.
9. **Data integrity:** systematic pricing/obligation mismatch between audit API and DB without explanation.
10. **Security:** auth bypass, cross-driver PII leak, or SECRET_KEY guard failure.

**Resume criteria:** root cause documented, copy/tests updated, ops re-briefs affected drivers, §10 checklist re-run.

---

## 8. Manual reconciliation / export requirements

**Per completed beta week (minimum):**

| Export | Source | Purpose |
|--------|--------|---------|
| Completed rides CSV | DB `rides` + `ride_pricing` | Match UI totals to integer cents |
| Settlement obligations | `settlement_entries` for ride ids | Verify obligation rows ≠ payout |
| Marketplace ledger events | `marketplace_ledger_events` (filtered) | Audit lifecycle evidence |
| Ops/test ride list | rides where `lifecycle_reason` ∈ simulation/ops/beta/test | Exclude from “real demand” metrics |
| Driver ack log | ops CRM / spreadsheet | Prove informed consent |

**Reconciliation checks:**

1. Sum of `driver_payout_cents` (or equivalent) on completed rides = earnings API projection (no hidden client math).
2. Every dollar shown in app has corresponding `ride_pricing` row or is labeled unavailable.
3. Zero PSP transaction ids in DB or logs.
4. Route provider `haversine_fallback` rows labeled as estimate in support scripts.

**Retention:** keep exports for beta duration + 90 days unless legal specifies otherwise.

---

## 9. Dossier quarantine rule

**Rule (non-negotiable during beta):** The dossier spine (`/supply/*`, `/demand/*`, `/trip/*`, `ledger_accounts`, geospatial auto-match) is **parallel foundation only**. It is **not** driver cockpit truth.

| Allowed | Forbidden |
|---------|-----------|
| Dossier tests in `backend/tests/test_dossier_*` | `driver-app` calls to dossier endpoints |
| Docs referencing dossier as **PARALLEL_NOT_WIRED** | Earnings UI citing dossier `ledger_*` |
| Architecture reconciliation in `HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md` | Support scripts telling drivers to use dossier APIs |

**Verification before invite:**

```powershell
# driver-app must not reference dossier paths
rg -n "supply/|demand/|trip/" driver-app/src --glob "!**/betaTruthCopy.js"
```

Expected: no matches (except excluded copy-definition files per tests).

---

## 10. Final GO / NO-GO checklist (before inviting drivers)

### Program truth

- [ ] `docs/CURRENT_TRUTH.md` reflects NO_GO for payments, OSRM runtime, dossier wired
- [ ] `docs/PRODUCT_BOUNDARY_STAGE0.md` linked to this pack
- [ ] No public marketing / waitlist implying paid marketplace

### Build & config

- [ ] `VITE_BETA_NO_MONEY_TRUTH=true` on trusted-beta deployment
- [ ] `VITE_ENABLE_RIDE_SIMULATION=false` in production beta
- [ ] `VITE_ALLOW_OFFLINE_MOCK=false`
- [ ] `driver-app/scripts/assert-prod-truth.mjs` passes on release build

### Copy & UX

- [ ] `BetaFirstRunAck` tested with flag on
- [ ] Earnings, trips, audit, cockpit show required boundary sentences
- [ ] Forbidden phrase unit + cockpit scan pass
- [ ] Simulation/ops rides show test badge when `lifecycle_reason` set

### Backend proof

- [ ] `py -3.11 -m pytest tests -q` pass
- [ ] Ride-flow and audit Playwright proofs pass (or documented waiver with owner sign-off)
- [ ] `GET /drivers/rides/{id}/audit` returns `payment_execution: not_implemented`

### Ops

- [ ] Support channel configured (replace `BETA_SUPPORT_PLACEHOLDER`)
- [ ] Driver ack process + reconciliation template ready (§8)
- [ ] Ops briefing on stop conditions (§7)
- [ ] Trusted driver list approved (no open enrollment)

### Explicit NO-GO gates (do not invite if any fail)

- [ ] OSRM runtime claimed GO without doc
- [ ] Postgres claim-race claimed GO without proof artifact
- [ ] PSP or payment UI present
- [ ] Dossier wired to driver app

**Sign-off:** Product owner + engineering lead — date: __________

---

## Proof commands

```powershell
cd driver-app
npm run test:unit

cd ..\backend
py -3.11 -m pytest tests -q

py -3.11 scripts/verify_current_truth_backlog.py
```

Report: `docs/HALFAPP_TRUSTED_NO_MONEY_BETA_BOUNDARY_PACK_01_REPORT.md`
