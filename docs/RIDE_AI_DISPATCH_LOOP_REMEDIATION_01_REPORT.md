# RIDE_AI_DISPATCH_LOOP_REMEDIATION_01 — Report

**Task:** RIDE_AI_DISPATCH_LOOP_REMEDIATION_01  
**Audit baseline:** RIDE_AI_DISPATCH_LOOP_AUDIT_01 = PARTIAL_GO  
**Date:** 2026-05-24 (superseded for tier claims 2026-05-25)  

---

## Verdict: **PARTIAL_GO** (remediation slice)

Remediation closes all **code-level** blockers from the audit (ledger-shaped trip records, advisory route labels, AbortController cancellation, decline/redispatch guards, client + server rate limits, PII sanitization, tests).

**Current tier claims (authoritative):** see `docs/RIDE_AI_DISPATCH_PRODUCTION_PROOF_GATES_01_REPORT.md`:

- **GO_DEMO_SAFE** — Playwright E2E 2/2; demo simulation explicit and labeled.
- **PARTIAL_GO_PRODUCTION_ROUTE_CODE_COMPLETE_RUNTIME_PROOF_PENDING** — OSRM grounding code-complete; runtime proof pending.
- **Production GO** — not issued.

**Production GO is not claimed** because:

1. **Ledger-backed financials** — Trip Complete uses `GET /drivers/rides/{id}/payment` when the backend returns `ride_payments`. Mock/offline paths still fall back to **DEMO_SIMULATION** (explicitly labeled). Production GO requires every completed ride to have a captured ledger row in the operational DB.
2. **Grounded route intelligence (runtime)** — OSRM integration and `routeContextFromRide` are wired in code (2026-05-25). Production GO still requires OSRM listening with `route_used_fallback=false` and client `live: true` evidence — see gates report §7.

Claude remains **advisory only** — no dispatch state mutation in the AI module.

---

## Files changed

### Driver app — new module

| Path | Purpose |
|------|---------|
| `driver-app/src/services/rideAiDispatch/constants.js` | States, labels, rate limits |
| `driver-app/src/services/rideAiDispatch/fareBreakdown.js` | `TripRecord` / `FareBreakdown` (LEDGER vs DEMO_SIMULATION) |
| `driver-app/src/services/rideAiDispatch/routeContext.js` | Route provider interface + advisory label |
| `driver-app/src/services/rideAiDispatch/piiSanitizer.js` | Plate tokens, coord rounding, name stripping |
| `driver-app/src/services/rideAiDispatch/rateLimiter.js` | 3s min interval + session budget |
| `driver-app/src/services/rideAiDispatch/streamAI.js` | `streamId` guard + per-call `AbortController` |
| `driver-app/src/services/rideAiDispatch/declineRedispatch.js` | `DECLINED` / `REDISPATCHING`, no stacked timeouts |
| `driver-app/src/services/rideAiDispatch/prompts.js` | Structured prompts only |
| `driver-app/src/services/rideAiDispatch/index.js` | Barrel export |
| `driver-app/src/hooks/useRideAiDispatch.js` | Lifecycle orchestration (advisory) |
| `driver-app/src/components/cockpit/RideAiDispatchPanel.jsx` | Cockpit UI |
| `driver-app/tests/unit/rideAiDispatch.test.js` | Required proof tests |

### Driver app — wiring

| Path | Change |
|------|--------|
| `driver-app/src/components/MapHome.jsx` | `useRideAiDispatch`, lifecycle hooks on accept/decline/start/complete |
| `driver-app/src/components/cockpit/MarketplaceBottomSheet.jsx` | Renders `RideAiDispatchPanel` |
| `driver-app/src/services/engineeringAssistantApi.js` | `AbortSignal` on chat fetch |
| `driver-app/src/utils/api.js` | `getRidePayment(rideId)` + mock handler |

### Backend

| Path | Change |
|------|--------|
| `backend/services/ai_assistant_quota.py` | Per-driver min interval + session budget |
| `backend/routes/engineering_assistant.py` | HTTP 429 on quota exceed |
| `backend/tests/test_ai_assistant_quota.py` | Quota tests |

---

## Exact tests run

```text
cd driver-app
node --test tests/unit/rideAiDispatch.test.js
# 13 tests — all pass (after remediation)

cd backend
py -3.11 -m pytest tests/test_ai_assistant_quota.py -q
# 2 passed
```

### Proof mapping

| Requirement | Test |
|-------------|------|
| Superseded streams abort previous fetch | `aborts previous fetch when a new stream supersedes` |
| Decline cannot stack redispatch timeouts | `does not stack repeated redispatch timeouts` |
| Trip Complete uses TripRecord/FareBreakdown | `trip complete prompt uses structured ledger record only` |
| Route advisory when no live provider | `shows advisory label when no live route provider` |
| No raw plates in prompts | `does not include raw license plate in sanitized prompt payload` |
| Rate limiting | `blocks rapid calls under min interval`, `pauses after session budget` |

---

## Before / after risk table

| Risk | Before (audit) | After remediation |
|------|----------------|-------------------|
| Fake money presented as real | +$0.09/180ms ticker, $9.25 floor, 72/28 UI math | Structured `TripRecord`; LEDGER from API or **DEMO_SIMULATION** label |
| Hallucinated live traffic | Seattle notes without source | Advisory label + `routeContext` with `live` flag |
| Stale AI text | streamId guard only | streamId + **AbortController** on fetch |
| Decline stuck / stacked redispatch | MATCHED stuck, multiple timeouts | `DECLINED` → `REDISPATCHING`, single timeout guard |
| AI cost runaway | None | Client 3s + budget; server quota on `/engineering-assistant/chat` |
| PII in prompts | Plates, names, coords | Sanitized operational JSON |
| Dispatch corruption by AI | Advisory (OK) | Unchanged — advisory only |

---

## Remaining production blockers

1. **100% ledger capture** on ride complete in production DB (no DEMO_SIMULATION in ops review).
2. **Routing provider integration** — populate `route_provider`, snapshots, and `live: true` in `routeContextFromRide`.
3. **Persistent server quota** — current quota is in-memory per process (resets on restart); use Redis/DB for multi-instance production.
4. **Owner E2E** with `ENGINEERING_ASSISTANT_ENABLED=1` and real Anthropic key — verify panel + quota under load.

---

## Confirmation: advisory-only dispatch

- AI module does **not** call `acceptRide`, `declineRide`, `claim_ride`, or lifecycle mutators.
- `declineRedispatch` manager is **UI state only** for the panel; backend decline still flows through `MapHome` → `driverAPI`.
- Engineering assistant remains behind `ENGINEERING_ASSISTANT_ENABLED` and backend proxy.

---

## Removed / not reintroduced

- No client-side fare ticker (`+0.09` / 180ms).
- No hardcoded $9.25 production floor in UI.
- Claude prompts forbid inventing dollar amounts outside structured JSON.
