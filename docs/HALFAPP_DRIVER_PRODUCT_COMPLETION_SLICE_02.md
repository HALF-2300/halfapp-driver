# HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02 — Profile + settings persistence

**Status:** GO  
**Date:** 2026-05-22  
**Lane:** Driver product completion (not payments Phase 6)

---

## GO ritual (copy-paste)

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_02 — GO

Shipped:
- Alembic migrations: `0024_driver_profiles`, `0025_driver_settings` (alembic head: 0025)
- Driver profile persistence:
  - `GET/PUT /drivers/me/profile` (display_name, phone_e164, photo_url overlay)
- Driver settings persistence:
  - `GET/PUT /drivers/me/settings` (units, locale, theme, notification preference toggles)
- Driver Settings UI:
  - `/driver/settings` wired to PUT (preferences auto-save + profile save)
- Stripe Connect status remains DB-only read-only:
  - `GET /drivers/stripe/connect/status` unchanged (no Stripe API)
- Existing driver read-only contract preserved:
  - `GET /drivers/profile` unchanged (User + vehicle)

Tests / guards:
- Backend: `test_driver_settings_profile_slice02.py` PASS
- Frontend: DriverSettings unit checks PASS
- Guards: assert-no-ai-providers PASS; assert-no-money-claims PASS

Not shipped (Slice 03+):
- Web push / service worker / VAPID
- resilientFetch / offline banner / ride-write Idempotency-Key
- OSRM ops-only healthcheck
- Connect onboarding buttons or Stripe API from driver app
```

---

## Scope

| In | Out |
|----|-----|
| `driver_profiles` + `driver_settings` tables | Web push delivery |
| `/drivers/me/profile` + `/drivers/me/settings` | `resilientFetch` / offline banner |
| Settings UI persistence | OSRM healthcheck |
| Notification **preference** storage only | Stripe Connect onboarding from UI |

---

## Verification

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
py -3.11 -m alembic upgrade head
py -3.11 -m pytest tests/test_driver_settings_profile_slice02.py -q

cd ..\driver-app
npm test
npm run build
npm run assert-no-ai-providers
npm run assert-no-money-claims
```

---

## Delivered (file index)

| Area | Path |
|------|------|
| Migrations | `backend/alembic/versions/0024_driver_profiles.py`, `0025_driver_settings.py` |
| Models | `backend/models/driver_profile.py`, `driver_app_settings.py` |
| Services | `backend/services/driver_profile_service.py`, `driver_app_settings_service.py` |
| Routes | `backend/routes/drivers.py` (`/me/profile`, `/me/settings`) |
| Settings UI | `driver-app/src/components/DriverSettings.jsx` |
| API client | `getDriverAppSettings`, `putDriverAppSettings`, `getDriverMeProfile`, `putDriverMeProfile` in `driver-app/src/utils/api.js` |
| Tests | `backend/tests/test_driver_settings_profile_slice02.py`, `driver-app/tests/unit/driverSettings.test.js` |

---

## API contracts

### `GET/PUT /drivers/me/profile`

Separate from legacy `GET /drivers/profile` (User + vehicle, `read_only: true` on GET).

```json
{
  "display_name": "string|null",
  "phone_e164": "string|null",
  "photo_url": "string|null",
  "updated_at": "ISO8601|null"
}
```

### `GET/PUT /drivers/me/settings`

```json
{
  "units": "mi|km",
  "locale": "en-US",
  "theme": "light|dark|system",
  "notif_push_enabled": false,
  "notif_sound_enabled": true,
  "notif_quiet_hours": null
}
```

`PUT` accepts partial bodies. Invalid `units` / `theme` → `400`.

---

## Rollback

```powershell
cd backend
py -3.11 -m alembic downgrade 0023_stripe_payout_transfers
```

Revert driver-app Settings component to Slice 01 read-only if needed.

---

## Guardrails

- No bank-deposit marketing copy (unchanged `assert-no-money-claims`)
- Connect status remains DB-only; no Stripe API from Settings
- Push toggle stores preference only — no subscription endpoints

---

## Related

- Slice 01: `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_01.md`
- Program truth: `docs/CURRENT_TRUTH.md`
