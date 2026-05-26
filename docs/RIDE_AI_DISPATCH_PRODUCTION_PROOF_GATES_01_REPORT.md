# RIDE_AI_DISPATCH_PRODUCTION_PROOF_GATES_01 — Report

**Task:** RIDE_AI_DISPATCH_PRODUCTION_PROOF_GATES_01  
**Baseline:** RIDE_AI_DISPATCH_LOOP_REMEDIATION_01 = PARTIAL_GO (superseded for demo tier)  
**Date:** 2026-05-25 (Playwright 2/2; OSRM grounding patch)  

---

## Verdict

| Tier | Label |
|------|--------|
| Demo | **GO_DEMO_SAFE** |
| Production routing | **PARTIAL_GO_PRODUCTION_ROUTE_CODE_COMPLETE_RUNTIME_PROOF_PENDING** |

**Not issued:** `NO_GO` (no demo gate failed). **Not issued:** Production GO.

### GO_DEMO_SAFE

All demo-scope gates are **PASS** or explicitly out-of-claim. Payment reads `ride_payments` (ledger when captured). The simulation path is explicit, tested, and labeled (`DEMO_SIMULATION` when no ledger row). UI lifecycle is proven in a real browser via Playwright (2/2).

| Gate | Result |
|------|--------|
| 1. Payment proof | **PASS** — `ride_payments` persisted; driver GET matches DB row |
| 2. UI lifecycle E2E | **PASS** — Playwright `ride-ai-dispatch-ui-proof.spec.ts` (2/2, ~17s) |
| 3. Route advisory | **PASS** — unit tests + UI `ride-ai-route-advisory-label` |
| 4. PII prompt proof | **PASS** — unit tests + snapshot artifact |
| 5. Production GO claim | **DENIED** — runtime OSRM proof + persistent AI quota; see production delta below |

### PARTIAL_GO_PRODUCTION_ROUTE_CODE_COMPLETE_RUNTIME_PROOF_PENDING

Production route grounding is **no longer “architecture open.”** OSRM integration and the `distance_km` / `duration_minutes` default-overwrite fix are **code-complete** (`ground_ride_route`, `routeContextFromRide`, simulation create/accept). **Production GO is not claimed** until runtime evidence below is captured on a listening OSRM instance.

---

## 1. Payment proof gate

### Backend truth (PROVEN)

`GET /drivers/rides/{ride_id}/payment` reads the **`ride_payments`** SQLAlchemy model (`backend/models/payment.py`), not client-side fare math.

| Step | Evidence |
|------|----------|
| Row created on ride create | `create_payment_for_ride` in `rider_rides.py` |
| Authorized on accept / auto-assign | `authorize_payment_for_ride` |
| Captured on complete | `capture_payment_for_ride` in `drivers.py` |
| Driver GET | `get_ride_payment_for_driver` → `get_ride_payment(db, ride_id)` |

**Test run:**

```text
pytest tests/test_ride_ai_dispatch_payment_gate.py tests/test_ride_payment_phase3.py -q
# 3 passed
```

`test_driver_payment_endpoint_returns_persisted_ride_payments_row` asserts:

- HTTP 200 after full ride complete
- `RidePayment.status == "captured"` in DB
- Response `amount_cents` / `driver_payout_cents` / `status` **equal** DB row

`test_driver_payment_endpoint_404_when_no_ride_payments_row` asserts no invented payment when row missing.

### Client truth (PROVEN)

`useRideAiDispatch.onTripComplete` → `fetchRidePayment(rideId)` → `resolveTripRecord`:

| Condition | `TripRecord.source` | UI meta |
|-----------|---------------------|---------|
| Payment API returns `payment` with `amount_cents` | `LEDGER` | "Trip complete — ledger-backed financials" |
| 404 / error / missing row | `DEMO_SIMULATION` | "Trip complete — DEMO_SIMULATION financials" |

**No** `+0.09`/180ms ticker or hardcoded $9.25 production floor in the AI module.

**Caveat:** `driver-app` **offline mock** (`ALLOW_OFFLINE_MOCK`) synthesizes a payment object from mock ride pricing — still structured, but not PostgreSQL production data. Ops must run against **real API** for ledger proof.

---

## 2. UI lifecycle E2E

### Proven without browser (this run)

**Source contract** (`rideAiDispatchProductionProof.test.js`):

- `MapHome.jsx` calls: `onIncomingMatch`, `onDriverAccept`, `onDriverDecline`, `onTripStart`, `onTripComplete`
- `MarketplaceBottomSheet.jsx` renders `RideAiDispatchPanel`
- `data-testid="ride-ai-dispatch-panel"`, `ride-ai-dispatch-state`

| Lifecycle stage | Hook / trigger | Expected panel behavior |
|-----------------|----------------|-------------------------|
| Request / incoming | `onIncomingMatch` | State `matched`; meta "Match analysis (advisory)" |
| Accept | `onDriverAccept` | State `accepted`; route meta or advisory label |
| Decline | `onDriverDecline` | `declined` → `redispatching`; no stacked timeouts (unit) |
| Start trip | `onTripStart` | State `in_trip`; "Ops monitoring (advisory)" |
| Complete | `onTripComplete` | State `complete`; LEDGER or DEMO_SIMULATION meta |

### Playwright E2E (PROVEN — 2026-05-25)

`driver-app/tests/ride-ai-dispatch-ui-proof.spec.ts`

| Test | Result |
|------|--------|
| Simulation lifecycle (match → accept → advance → complete) | **pass** (~7–12s) |
| Decline (AI state off `matched`, idle sheet + hide notice) | **pass** (~6s) |

**Command (self-contained — starts isolated backend :8012 + app :3026):**

```powershell
cd driver-app
npx playwright test -c playwright.ride-ai-dispatch.config.js --reporter=list
```

Config: `playwright.ride-ai-dispatch.config.js` (SQLite temp DB, `HALFAPP_ENABLE_RIDE_SIMULATION=1`, mock-off).

**Manual stack (your original recipe) still works:**

```powershell
$env:HALFAPP_ENABLE_RIDE_SIMULATION=1
# backend on :8000
cd driver-app
npx playwright test tests/ride-ai-dispatch-ui-proof.spec.ts --reporter=html
```

Screenshots: `driver-app/test-results/ride-ai-dispatch-ui-proof/`

Without `ENGINEERING_ASSISTANT_ENABLED=1`, panel shows **manual mode** — lifecycle state transitions are still observable via `ride-ai-dispatch-state` (proven in Playwright).

---

## 3. Route advisory proof

**Constant:** `[ADVISORY · AI ESTIMATE · NOT LIVE TRAFFIC]` (`ROUTE_ADVISORY_LABEL`)

**When shown:**

- `routeContextFromRide(ride)` sets `live: false` unless `route_provider` + `route_calculated_at` + distance/duration evidence exist
- Prompt JSON includes `route_source`, `route_calculated_at`, `route_provider_confidence` when live evidence is present (production wiring target)
- Typical accepted ride without OSRM snapshot → **not live**
- `formatRouteNoteForDisplay` prefixes advisory label on panel text
- `RideAiDispatchPanel` renders `data-testid="ride-ai-route-advisory-label"` when meta or text includes label

**Tests:**

```text
node --test tests/unit/rideAiDispatch.test.js
# route intelligence advisory label — pass

node --test tests/unit/rideAiDispatchProductionProof.test.js
# route intelligence prompt carries advisory when not live — pass
```

**Demo-safe:** Advisory label + fallback honesty are proven in unit/UI tests.  
**Production claim:** Requires OSRM runtime proof (see production delta §6). Claude must not be read as authoritative routing until `routeContext.live === true` with evidence fields.

---

## 4. PII final prompt proof

Sanitization in `piiSanitizer.js` before every advisory prompt:

| Field | Treatment |
|-------|-----------|
| `license_plate` / `plate` | → `vehicle_token` (e.g. `VEHICLE_TOKEN_23`) |
| `rider_name` / `customer_name` | Removed |
| `pickup_location` / `destination` | → zone redaction labels |
| Exact lat/lng | → rounded `*_lat_rounded` / `*_lng_rounded` (2 dp) |

**Tests:** `rideAiDispatch.test.js` + `rideAiDispatchProductionProof.test.js` — no raw `WA-7823`, names, or full-precision coords in prompts.

**Audit artifact (generated by test):**

`driver-app/test-results/ride-ai-dispatch-proof/sanitized-prompt-snapshot.json`

Contains captured `match`, `route`, `complete_demo`, `complete_ledger` prompt bodies for review.

---

## 5. Tests executed (exact commands)

```text
cd backend
py -3.11 -m pytest tests/test_ride_ai_dispatch_payment_gate.py tests/test_ride_payment_phase3.py -q
# 3 passed

cd driver-app
node --test tests/unit/rideAiDispatch.test.js
# 13 passed

node --test tests/unit/rideAiDispatchProductionProof.test.js
# 10 passed

cd driver-app
npx playwright test -c playwright.ride-ai-dispatch.config.js --reporter=list
# 2 passed (~23s)
```

---

## Before / after risk (production readiness)

| Risk | Demo-safe? | Production-ready? |
|------|------------|-------------------|
| Fake money in AI summary | Yes — DEMO_SIMULATION labeled | Yes — when `ride_payments` captured (proven) |
| Hallucinated live traffic | Yes — advisory label | Code wired; needs runtime `routeContext.live` proof |
| Stale AI streams | Yes — streamId + AbortController | Yes |
| Decline stuck / stacked redispatch | Yes — state machine tested | Yes |
| PII in prompts | Yes — sanitized | Yes (review snapshot periodically) |
| AI cost runaway | Yes — client + server quota | Server quota in-memory only (multi-instance gap) |

---

## Remediation items already closed (not production blockers)

| Item | Status | Evidence |
|------|--------|----------|
| AbortController on stream supersession | **CLOSED** | `streamAI.js` — `abortActiveStream()` before each fetch; `AbortError` returns without `onError` |
| Client rate limit + session budget | **CLOSED** | `rateLimiter.js` + unit tests |
| Declined-state / no stacked redispatch | **CLOSED** | `declineRedispatch.js` + unit + Playwright decline test |
| Server engineering-assistant quota (429) | **CLOSED** | `ai_assistant_quota.py` — in-memory only |

## 6. Live route grounding (OSRM — code-complete 2026-05-25)

**Provider:** OSRM self-hosted (`osrm_self_hosted` → API label `osrm_v5`).

| Layer | Behavior |
|-------|----------|
| Backend | `ground_ride_route()` on simulation create + accept; stamps `route_provider`, `route_source`, `route_used_fallback`, `route_calculated_at`, `route_provider_confidence` on driver ride view |
| Client | `routeContextFromRide()` → `live: true` only when OSRM succeeded (not haversine); `distance_meters` / `duration_seconds` populated from grounded km/min |
| UI | `[ADVISORY · AI ESTIMATE · NOT LIVE TRAFFIC]` omitted only when `routeContext.live === true` |

**Code tests (mocked HTTP):** `backend/tests/test_ride_route_grounding.py`, `tests/test_osrm_self_hosted_routing.py`.

Simulation rides no longer default `distance_km=4.0` / `duration_minutes` over OSRM — body overrides are optional only.

**Run OSRM locally (Portland/Oregon extract):**

```powershell
cd docker/osrm-portland
docker compose up -d
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
$env:ROUTING_PROVIDER = "osrm_self_hosted"
cd backend
py -3.11 -m pytest tests/test_ride_route_grounding.py -q
```

## 7. Remaining production delta (before Production GO)

Do **not** claim Production GO until all items below are evidenced on a real stack (not mocks).

### 7.1 OSRM up — accepted ride API fields

With OSRM listening (`:5000` or `OSRM_BASE_URL`), after accept (or simulation create + accept), driver ride payload must show:

| Field | Expected when OSRM succeeds |
|-------|----------------------------|
| `route_provider` | `osrm_self_hosted` |
| `route_source` | `osrm_v5` |
| `route_used_fallback` | `false` |
| `route_calculated_at` | present (ISO timestamp) |
| `route_provider_confidence` | present (numeric) |
| `distance_km` / `duration_minutes` | OSRM-derived values — **not** legacy `4.0` km default |

Record: `GET /drivers/rides/{id}` or active-ride surface JSON + `docs/SELF_HOSTED_ROUTING_PROOF_V0_2_STATUS.md` evidence tables.

### 7.2 Client `routeContext` — live path

On accept in driver cockpit (AI panel or route meta):

- `routeContext.live === true`
- `distance_meters` and `duration_seconds` populated
- `ride-ai-route-advisory-label` **hidden** (advisory copy not in panel meta/text)

### 7.3 OSRM down — fallback path

Stop OSRM or point `OSRM_BASE_URL` at a dead host; repeat accept:

- `route_used_fallback === true`
- `routeContext.live === false`
- `ride-ai-route-advisory-label` **visible** with `NOT LIVE TRAFFIC`

### 7.4 Persistent production AI quota

In-memory `ai_assistant_quota.py` is insufficient for multi-worker production. Replace with durable budget (Redis/DB) before claiming production AI cost safety.

### 7.5 Out of scope (unchanged)

- **Stripe / bank settlement** — `ride_payments` is simulated ledger, not PSP settlement.
- **Optional:** Playwright with `ENGINEERING_ASSISTANT_ENABLED=1` for streaming copy (not required for demo tier).
- **No mock path in prod builds** — `ALLOW_OFFLINE_MOCK` off.

---

## Confirmation: advisory-only dispatch

- No AI code path calls `acceptRide`, `claim_ride`, or lifecycle mutators.
- `declineRedispatch` manager affects **panel state only**; backend decline uses existing `driverAPI` routes.

---

## Files added for this gate

| File | Purpose |
|------|---------|
| `backend/tests/test_ride_ai_dispatch_payment_gate.py` | Payment persistence proof |
| `driver-app/tests/unit/rideAiDispatchProductionProof.test.js` | Wiring, prompts, PII snapshot |
| `driver-app/tests/ride-ai-dispatch-ui-proof.spec.ts` | UI lifecycle E2E |
| `driver-app/playwright.ride-ai-dispatch.config.js` | Isolated Playwright stack for gate 2 |
| `docs/RIDE_AI_DISPATCH_PRODUCTION_PROOF_GATES_01_REPORT.md` | This report |

---

## Summary for operators

- **Tier claim (demo):** **GO_DEMO_SAFE** — Playwright 2/2; simulation path explicit; payment/advisory/PII gates pass.
- **Tier claim (routing):** **PARTIAL_GO_PRODUCTION_ROUTE_CODE_COMPLETE_RUNTIME_PROOF_PENDING** — OSRM wired in code; runtime proof §7 required.
- **Safe to demo:** Yes — manual mode OK; advisory label when not live; `DEMO_SIMULATION` when payment missing.
- **Safe to claim “driver payout from ledger”:** Only after complete **and** `GET /drivers/rides/{id}/payment` returns `status: captured` from real backend.
- **Safe to claim “live / road-network route intelligence”:** No until §7.1–7.3 evidenced with OSRM listening.
- **Production GO:** Not issued.
