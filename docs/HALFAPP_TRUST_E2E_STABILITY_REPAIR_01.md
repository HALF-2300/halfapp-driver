# HALFAPP_TRUST_E2E_STABILITY_REPAIR_01

**Date:** 2026-05-22  
**Scope:** Trust Playwright lane stabilization (no product feature expansion).

---

## Verdict

**GO** — `npm run test:e2e:trust` reports **12 passed** (including retries where configured).

---

## Failures reproduced (baseline)

| Test | Symptom |
|------|---------|
| `mock-off-contract` dismiss persistence | `sync-marketplace-btn` not clickable (hidden in closed diagnostics drawer) |
| `mock-off-contract` accept error UI | Stub 409 used string `detail`; UI routed to `claim-conflict-notice` instead of `accept-ride-error` |
| `ride-transparency-conflict` | `map-home` timeout; dual-browser race; API 409 assertion flaky vs UI timing |

---

## Root causes

1. **Dismiss:** `backend-hide-notice` only rendered inside collapsed `DriverAvailabilityCard`; sync lived in closed `DiagnosticsDrawer`.
2. **Accept error:** `MapHome.acceptRide` treated any 409 message as structured conflict and cleared `backendError`.
3. **Go online:** `goOnline` called `refreshBackendTruth(false)` so stubbed/real available rides did not surface before accept.
4. **Conflict harness:** Dual-browser UI race for B’s claim; pre-setting presence made `go-online-btn` absent; direct cross-origin API without Vite `/api` proxy added CORS flake.
5. **Conflict test:** Empty `available-rides` poll false-positive when driver offline on API.

---

## Fixes made

### Product (`driver-app`)

| Area | Change |
|------|--------|
| `MarketplaceBottomSheet.jsx` | Show `backend-hide-notice` + visible `sync-marketplace-btn` on online-idle sheet after hide |
| `MapHome.jsx` | `goOnline` → `refreshBackendTruth(true)`; structured 409 → conflict path only; string 409 → `accept-ride-error`; newest eligible marketplace ride; no alternate ride bind while conflict memory active |
| `DriverMapShell.jsx` | `data-testid="driver-shell"` wrapper for readiness |
| `ClaimConflictNotice.jsx` | `data-claim-result` / `data-truth-status` attributes |
| `playwright.trust.config.js` | `/api` proxy to trust backend (same pattern as ride-flow) |

### Tests

| File | Change |
|------|--------|
| `mock-off-contract.spec.ts` | Wait for `sheet-request-incoming`; use `accept-ride-btn` |
| `ride-transparency-conflict.spec.ts` | Single page; `addInitScript` + `/#/driver`; assert conflict rider name; B wins via API; A UI accept + `waitForResponse` 409 |
| `rideTransparency.test.js` | Assert non-structured `detail` is not conflict |

---

## Files changed

- `driver-app/src/components/MapHome.jsx`
- `driver-app/src/components/cockpit/MarketplaceBottomSheet.jsx`
- `driver-app/src/components/cockpit/DriverMapShell.jsx`
- `driver-app/src/components/cockpit/ClaimConflictNotice.jsx`
- `driver-app/playwright.trust.config.js`
- `driver-app/tests/trust-mock-off/mock-off-contract.spec.ts`
- `driver-app/tests/trust-mock-off/ride-transparency-conflict.spec.ts`
- `driver-app/tests/unit/rideTransparency.test.js`

---

## Verification

```powershell
cd backend
python -m pytest -q
# 126 passed

cd ..\driver-app
npm run build
npm test
# 50 passed
npm run test:e2e:ride-flow
# 1 passed
npm run test:e2e:trust
# 12 passed
```

---

## Trust contract preserved

- Mock-off remains disabled (`VITE_ALLOW_OFFLINE_MOCK=false`).
- Structured backend 409 still shows `claim-conflict-notice` with `backend_conflict` / `lost`.
- Legacy/string 409 stubs still show `accept-ride-error` (no fake success).
- Dismiss remains **backend** truth (`POST /drivers/rides/{id}/hide`), not localStorage.
- No dossier endpoints, payments, or routing claims added.

---

## Remaining blockers

- OSRM runtime proof still **NO_GO** (separate lane).
- Trust DB accumulates `requested` rides across specs in one Playwright process; UI now prefers newest eligible ride and skips marketplace re-bind during conflict memory.

---

## Next recommended task

**`HALFAPP_ROUTE_SNAPSHOTS_FOUNDATION_01`**
