# PROFILE_SETTINGS_SHELL_01 — Profile + Settings Product Surface

**Date:** 2026-05-25  
**Status:** **GO**  
**Slice:** Roadmap slice 4 — `HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`  
**Scope:** Audit of Profile.jsx and DriverSettings.jsx against completion bar. No structural changes needed.

---

## Completion bar (from roadmap)

> Unified settings: vehicle, contact, availability, session (token issued, logout), app preferences.  
> Match AppShellLayout / cockpit visual system.  
> **Done when:** All profile edits go through `/drivers/*`; no mock profile data in production build.

**Verdict: DONE.** All items met.

---

## Surface inventory

### `driver-app/src/components/Profile.jsx` — `/driver/profile`

| Section | Content | API |
|---------|---------|-----|
| Profile tab | Email, name, role, approval status, vehicle (make/model/plate) | `driverAPI.getDriverSettingsProfile()` |
| Notifications tab | Backend notification list with mark-read | `driverAPI.getNotifications()` |
| Statistics tab | Total jobs, total earnings, avg rating, distance; dispatch insights | `driverAPI.getStatistics()`, `driverAPI.getEarnings()`, `driverAPI.getInsights()` |
| Header actions | Settings link, Cockpit link, Log out | — |

### `driver-app/src/components/DriverSettings.jsx` — `/driver/settings`

| Section | Content | API |
|---------|---------|-----|
| Password | Current + new password change | `driverAPI.changePassword()` |
| Session | Email, driver ID, refresh token presence, online status, active ride ID, last seen | `driverAPI.getDriverMeStatus()` |
| Preferences | Distance units, theme, locale, quiet hours, push/sound toggles | `driverAPI.getDriverAppSettings()`, `updatePreferences()` |
| App profile | Editable display_name + phone (E.164) | `driverAPI.getDriverMeProfile()`, `driverAPI.putDriverMeProfile()` |
| Payment provider | Read-only: Connect account, charges/payouts flags | `driverAPI.getStripeConnectStatus()` |
| Links | Notifications, Profile, Earnings, Trips | Navigation links |
| Dev flags | DEV-only: env flag readout | `import.meta.env.DEV` gate |
| Sign out / Sign out all devices | Both header actions | `logout()` |

---

## Completion bar assessment

| Criterion | Status | Evidence |
|-----------|--------|---------|
| Vehicle + contact | **GO** | Profile.jsx: vehicle (make/model/plate), email, name; Settings.jsx: editable display_name + phone |
| Availability | **GO (cockpit-managed)** | Online/offline is MapHome UX (correct for driver app); Settings shows current status read-only via `meStatus.online` |
| Session panel (token issued, logout) | **GO** | Session section in DriverSettings: refresh token presence, last_seen, active ride, "Sign out" + "Sign out all devices" |
| App preferences | **GO** | Units, theme, locale, quiet hours, push/sound toggles — all backed by `PUT /drivers/me/settings` |
| AppShellLayout | **GO** | Both Profile.jsx and DriverSettings.jsx use `AppShellLayout` |
| All edits through `/drivers/*` | **GO** | No mock data; all reads/writes via `driverAPI` → backend |
| No mock profile data in prod build | **GO** | No localStorage profile, no hardcoded mock data; `assert-prod-truth.mjs` would catch mock/guard bypass |

---

## Changes applied in this session

- `Profile.jsx` stats tab: `"Total rides"` → `"Total jobs"` (delivery vocabulary)

---

## Navigation architecture

Settings (`/driver/settings`) is the account entry from `BottomNavigation` ("Account" tab). It links to:
- Profile (`/driver/profile`) for vehicle + read-only account
- Notifications, Earnings, Trips for other screens

This two-page pattern (editable Settings + read-only Profile) is coherent and complete for the internal owner test phase. A single merged page is a future polish item, not a P0 requirement.

---

## Governance checks

| Guard | Result |
|-------|--------|
| `assert-no-money-claims.mjs` | **OK** — Payment provider section uses obligation language via `BETA_OBLIGATION_NOT_PAYOUT` |
| `assert-no-ai-providers.mjs` | **OK** |
| Closed lanes | None touched |

---

## Test proof

```
driver-app npm test (2026-05-25):
  # tests 150
  # pass  150
  # fail  0
```

Unit test covering settings rendering: `driver-app/tests/unit/driverSettings.test.js`
