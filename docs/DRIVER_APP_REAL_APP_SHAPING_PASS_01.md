# Driver App Real-App Shaping Pass 01

**Date:** 2026-05-25  
**Status:** GO  
**Scope:** Driver app closed-beta readiness, online gate, ride-offer decision surface, trip completion receipt, and honest obligation copy.

## Verdict

**GO** for the closed-beta driver app shaping pass.

The driver app now has a visible product spine:

`Offline -> readiness check -> online -> ride offer -> accept -> trip -> completion receipt`

This is not a public-launch claim, payout claim, or production marketplace claim.

## What changed

### DriverReadinessV1

Added `driver-app/src/utils/driverReadiness.js`.

Readiness answers:

- Can this driver go online right now?
- If not, why?
- What action fixes it?

Blocked reasons include:

- profile incomplete
- vehicle info missing
- license/docs missing
- insurance missing
- insurance expired
- backend unavailable
- beta approval/manual ops required

### Online gate

Updated `driver-app/src/components/MapHome.jsx` and `driver-app/src/components/cockpit/MarketplaceBottomSheet.jsx`.

The driver cannot go online when readiness is blocked. The UI shows:

- `You are not ready to go online yet`
- `Reason: <specific blocker>`
- a clear next action

### Daily-use bottom sheet state

The cockpit bottom sheet now distinguishes:

- blocked setup state
- ready to go online
- online and waiting
- ride offered
- ride accepted
- arriving to pickup
- in trip
- trip completed

### Ride offer card

Updated `driver-app/src/components/cockpit/RideRequestCard.jsx`.

The ride card now shows:

- pickup area
- dropoff area
- estimated distance
- estimated time
- recorded obligation
- manual operations required
- accept / decline
- expired offer state
- conflict state when another driver already took the job

### Completion receipt

Added `driver-app/src/components/cockpit/CompletionReceiptCard.jsx`.

After completion the driver sees:

- `Trip completed`
- `Fare obligation recorded`
- `Payout not executed`
- `Manual review required`

### Backend profile shape

Updated `backend/routes/drivers.py` and `driver-app/src/utils/api.js` so the active `/drivers/profile` read path carries the readiness fields needed by the driver app:

- license number
- vehicle info
- insurance policy
- insurance expiry placeholder
- approval status

## Honest limits

- No real payout, deposit, wallet, cash-out, instant payout, or bank-transfer claim was added.
- Completion receipt is an obligation record only.
- Manual operations remain required.
- Backend currently exposes `insurance_expires_at: None`; expiry blocking exists in the frontend readiness model and needs real ops data to become fully live.
- Closed-beta readiness is improved; public launch readiness remains NO_GO.

## Proof

```powershell
cd driver-app
npm test
```

Result:

- 158 tests passed
- 47 suites passed
- `assert-no-ai-providers`: OK
- `assert-no-money-claims`: OK

```powershell
cd driver-app
npm run build
```

Result:

- production build passed
- Vite chunk-size/browser-data warnings only

```powershell
cd backend
py -3.11 -m pytest -q tests/test_driver_profile_read.py tests/test_driver_settings_profile_slice02.py tests/test_active_route_surface.py
```

Result:

- 10 passed
- 12 warnings

## Files changed

- `backend/routes/drivers.py`
- `driver-app/src/components/MapHome.jsx`
- `driver-app/src/components/cockpit/CompletionReceiptCard.jsx`
- `driver-app/src/components/cockpit/DriverReadinessCard.jsx`
- `driver-app/src/components/cockpit/MarketplaceBottomSheet.jsx`
- `driver-app/src/components/cockpit/RidePayoutSummary.jsx`
- `driver-app/src/components/cockpit/RideRequestCard.jsx`
- `driver-app/src/utils/api.js`
- `driver-app/src/utils/betaTruthCopy.js`
- `driver-app/src/utils/driverReadiness.js`
- `driver-app/tests/unit/driverReadiness.test.js`

## Remaining blockers

- Add an operator-owned data path for real license, insurance, insurance expiry, and vehicle-readiness updates.
- Run live owner courier day after P0 runtime gates are closed.
- Keep payout language locked to recorded obligation/manual review until real PSP/payout proof is deliberately scoped.
