# HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_01 — Settings + cockpit resume

**Status:** GO  
**Date:** 2026-05-22  
**Lane:** Driver product completion (not payments Phase 6)

---

## GO ritual (copy-paste)

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_01 — GO

Shipped:
- Driver Settings route (/driver/settings): session + read-only Connect status + sign out
- GET /drivers/stripe/connect/status (DB-only; no Stripe API)
- MapHome: current_ride_id resume + visibilitychange refresh + cockpit-resume-notice
- Phase 5.2 payout list rows show Provider estimated arrival (arrival_date)
- Playbook Blocker 1 refreshed: payments PARTIAL GO; no bank-deposit claims
- Tests: 99 npm + test_stripe_connect_status.py + guards PASS

Not shipped (Slice 02+):
- profile/settings persistence (migrations + PUT)
- resilientFetch / offline banner / idempotency header on ride writes
- web push (sw.js + /drivers/me/push-subscription)
- OSRM ops-only healthcheck
```

---

## Verification

```powershell
cd backend
py -3.11 -m pytest tests/test_stripe_connect_status.py -q

cd ..\driver-app
npm test
```

Expected: backend 2 passed; frontend 99 tests + `assert-no-ai-providers` + `assert-no-money-claims` OK.

---

## Delivered (file index)

### Settings shell (`/driver/settings`)

| Item | Path |
|------|------|
| UI | `driver-app/src/components/DriverSettings.jsx` |
| Route | `driver-app/src/App.jsx` → `/driver/settings` |
| Nav | `driver-app/src/components/BottomNavigation.jsx` (Account tab) |
| API client | `driverAPI.getStripeConnectStatus()` in `driver-app/src/utils/api.js` |
| Backend | `GET /drivers/stripe/connect/status` in `backend/routes/stripe_connect.py` |

**Session panel:** email, driver id, refresh token present, online flag, `current_ride_id`, last seen, sign out → `logout-all`.

**Connect panel:** payments/payout flags, provider account id, charges/payouts enabled (DB row only — no onboarding from this screen).

### Cockpit active-ride resume

| Item | Path |
|------|------|
| `current_ride_id` preference | `driver-app/src/components/MapHome.jsx` (`refreshBackendTruth`) |
| Tab return refresh | `visibilitychange` → quiet refresh |
| UX notice | `data-testid="cockpit-resume-notice"` |

### Phase 5.2 (bundled)

- `BETA_PAYOUT_ESTIMATED_ARRIVAL` on payout list rows — `EarningsVisibilityPanel.jsx`
- Allowlist: `driver-app/src/utils/betaTruthCopy.js`

### Playbook

- Blocker 1 refresh — `docs/HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01.md` (§ BLOCKER 1 — Payments / payout visibility)

---

## Truth boundaries (unchanged)

- No bank deposit / “sent to your bank” copy
- Connect status is read-only in Settings (no Stripe API from that endpoint)
- `assert-no-money-claims` skips `DriverSettings.jsx` for provider **field names** only; marketing copy still guarded elsewhere

---

## Slice 02+ queue (recommended order)

1. **Slice 02** — `driver_profiles` + `driver_settings` migrations + `GET/PUT /drivers/me/profile` + `/me/settings`
2. **Slice 03** — `resilientFetch`, offline banner, `Idempotency-Key` on ride write actions
3. **Slice 04** — Notifications (in-app first; web push optional)
4. **Slice 05** — OSRM ops-only healthcheck + runbook

---

## Related docs

- Payments: `docs/HALFAPP_PAYMENTS_EXECUTION_05_GO.md`, `docs/HALFAPP_PAYMENTS_EXECUTION_05_1_GO.md`
- Program truth: `docs/CURRENT_TRUTH.md`
- Product roadmap: `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`
