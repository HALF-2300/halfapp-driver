# NOTIFICATIONS_PRODUCT_UI_01 — Notifications Inbox Completion

**Date:** 2026-05-25  
**Status:** **GO**  
**Slice:** Roadmap slice 5 — `HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`  
**Scope:** Driver-app Notifications component audit + stale test fix. No backend changes.

---

## Completion bar (from roadmap)

> Align notifications page with driver app chrome (ha-* / dark shell).  
> Backend-only list; honest empty state; remove or gate demo messages tab.  
> **Done when:** `GET /drivers/notifications` is the only source; UI matches trips/earnings quality bar.

**Verdict: DONE.** All items already satisfied; stale E2E assertion corrected.

---

## Current state audit

| Criterion | Status | Evidence |
|-----------|--------|---------|
| Uses `AppShellLayout` (dark ha-* shell) | **GO** | `Notifications.jsx` line 97 |
| Backend-only data source | **GO** | `driverAPI.getNotifications()` only; no localStorage fallback |
| Empty state | **GO** | `data-testid="notifications-empty"` with honest copy; no fake system cards |
| Demo messages tab gated | **GO** | `SHOW_DEMO_MESSAGES_TAB = import.meta.env.DEV` — not shown in production builds |
| Stale heading assertion | **FIXED** | E2E test checked `{ name: 'Inbox' }` but component renders `title="Notifications"` → corrected to `"Notifications"` |

---

## Changes made

### `driver-app/src/components/Profile.jsx`

- Stats tab: `"Total rides"` → `"Total jobs"` (delivery vocabulary alignment)

### `driver-app/tests/trust-mock-off/mock-off-contract.spec.ts`

- `page.getByRole('heading', { name: 'Inbox' })` → `{ name: 'Notifications' }` — component renders `title="Notifications"` via AppShellLayout; old assertion was stale from a prior UI iteration.

---

## Governance checks

| Guard | Result |
|-------|--------|
| `assert-no-money-claims.mjs` | **OK** |
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

---

## Notifications component state (reference)

- Route: `/driver/notifications` registered in `App.jsx`
- Component: `driver-app/src/components/Notifications.jsx`
- Data: `GET /drivers/notifications` → normalizes via `notificationDisplay.js`
- Mark-read: `PUT /drivers/notifications/{id}/read` (optimistic update + backend confirm)
- Demo tab: `SHOW_DEMO_MESSAGES_TAB = import.meta.env.DEV` — only visible in Vite dev server, blocked in production build
- Unread badge: propagated to `BottomNavigation` via `DriverPreferencesContext.refreshUnreadNotifications()`
