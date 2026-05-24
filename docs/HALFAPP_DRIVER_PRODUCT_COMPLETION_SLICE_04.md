# HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_04 — In-app notifications (GO)

**Status:** GO  
**Date:** 2026-05-23  
**Lane:** Driver product completion — notifications inbox (in-app only)  
**Depends on:** Slices 01–03 **GO**

**Maps to roadmap:** `NOTIFICATIONS_PRODUCT_UI_01` in `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`

**Decision:** Slice 04 is **in-app notifications polish**, not web push. Push preference from Slice 02 (`notif_push_enabled`) remains storage-only until an explicit Slice 04b or later.

---

## Purpose

Make `/driver/notifications` a first-class driver surface: same visual system as cockpit/settings, honest empty states, mark-read wired to the backend, and no fake “live chat” in default builds.

Drivers already have a `notifications` table and API; this slice is **product wiring + UX**, not a new messaging product.

---

## In scope (Slice 04)

| # | Deliverable | Acceptance |
|---|-------------|------------|
| 1 | **Notifications UI chrome** | `Notifications.jsx` uses `AppShellLayout` + `ha-*` tokens (match Settings / Trips) |
| 2 | **List from backend only** | `GET /notifications/` is the sole source for the Notifications tab in production |
| 3 | **Mark read** | Tap/ack calls `POST /notifications/{id}/read`; UI updates unread state |
| 4 | **Unread count** | Show `unread_count` from API in header or tab label when > 0 |
| 5 | **Messages tab honesty** | Demo messages **gated to `import.meta.env.DEV`** or removed; production shows explicit “not available” empty state |
| 6 | **Field mapping fix** | Map API `read` (backend) consistently in `mapApiNotification` / Profile tab |
| 7 | **Optional: lifecycle in-app alerts** | On key driver events (e.g. ride accepted, dispatch offer), insert `Notification` row for that driver — **no push delivery** |
| 8 | **Tests** | Backend list/read tests; frontend source or unit tests for mark-read + no demo in prod path |
| 9 | **Docs** | This file → **GO** ritual; playbook queue updated |

### API contracts (existing — do not break)

| Method | Path | Role |
|--------|------|------|
| GET | `/notifications/` | List for current user + non-expired broadcast (`NotificationListResponse`) |
| POST | `/notifications/{notification_id}/read` | Mark one read |
| POST | `/notifications/send` | Admin only — out of driver slice |
| POST | `/notifications/driver/ride-alert` | Admin broadcast — out of driver slice |

**Driver app** (`driver-app/src/utils/api.js`):

- `getNotifications()` → `GET /notifications/`
- `markNotificationRead(id)` → `POST /notifications/{id}/read`

**Not in Slice 04:** new `/drivers/me/notifications` router (optional future alias only if you want driver-scoped path — default: keep `/notifications/`).

---

## Out of scope (guardrails)

| Out | Reason |
|-----|--------|
| Web push / VAPID / `service-worker.js` | Slice 04b or later; preference already stored in `driver_settings` |
| `POST /drivers/me/push-subscription` | Requires push infra |
| OSRM healthcheck | Slice 05 **GO** — `docs/HALFAPP_OSRM_OPS_ONLY_SLICE_05.md` |
| Offline outbox / resilientFetch changes | Slice 03 closed |
| Rider chat / two-way messaging | Different product |
| Connect / Stripe from driver app | Payments lane |
| Dossier notification spine | Active spine is `/notifications/` on `users` |

---

## Grounded starting points (repo)

| Area | Path | Today |
|------|------|--------|
| Backend model + routes | `backend/routes/notifications.py` | `Notification` model; GET list, POST read |
| Driver UI (legacy chrome) | `driver-app/src/components/Notifications.jsx` | Light theme; demo Messages tab |
| Profile notifications tab | `driver-app/src/components/Profile.jsx` | Partial list + mark read |
| API client | `driver-app/src/utils/api.js` | `getNotifications`, `markNotificationRead` |
| Settings push toggle | `driver-app/src/components/DriverSettings.jsx` | Preference only — keep as-is |
| Route | `driver-app/src/App.jsx` | `/driver/notifications` |

---

## Implementation sketch (for agents)

### Frontend

1. Refactor `Notifications.jsx` to `AppShellLayout` (title “Notifications”, subtitle with unread count).
2. On row click → `markNotificationRead(id)` → optimistic `read: true`.
3. Remove or `DEV`-gate `DEMO_MESSAGES` and Messages tab; prod: single tab or “Messages — not available”.
4. Add `data-testid` hooks: `notifications-screen`, `notifications-list`, `notifications-mark-read`, `notifications-empty`.
5. Optional: unread badge on `BottomNavigation` Account/Inbox if product wants parity with Profile tab.

### Backend (optional lifecycle emits)

1. Small helper `services/driver_in_app_notifications.py` — `notify_driver(db, driver_id, title, message, type)`.
2. Call from `drivers.py` after accept / dispatch offer (minimal set — document which events).
3. Tests: driver receives notification row after simulated accept.

### Tests

- `backend/tests/test_driver_notifications_slice04.py` — list, mark read, 404 wrong user
- `driver-app/tests/unit/notificationsProduct.test.js` — source checks or shallow render patterns used elsewhere

---

## GO checklist

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_04 — GO

Shipped:
- /driver/notifications uses AppShellLayout + ha-* chrome
- GET /notifications/ + POST /notifications/{id}/read wired in UI
- Demo messages gated to `import.meta.env.DEV`
- In-app Notification rows on ride accept + complete (`INAPP_NOTIFICATIONS_ENABLED`, default on)
- `notificationDisplay.js` maps API `read` consistently (Notifications + Profile)
- Tests: `test_driver_notifications_slice04.py`, `notificationsSlice04.test.js`

Not shipped (Slice 04b+):
- web push / VAPID / service worker
- POST /drivers/me/push-subscription
- OSRM ops healthcheck
- offline mutation outbox (Slice 03 closed)
- Connect onboarding / Stripe API from driver app
```

---

## Verification ritual (GO)

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
py -3.11 -m pytest tests/test_driver_notifications_slice04.py -q

cd ..\driver-app
npm test
npm run build
npm run test:e2e:ride-flow
```

---

## Rollback

Revert `Notifications.jsx` and optional lifecycle hooks; no migration required unless lifecycle emits add columns (prefer none).

---

## PR body template (fill on ship)

```markdown
## HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_04 — GO

### Summary
Polishes the driver notifications inbox to match product chrome, wires mark-read to the backend, and removes misleading demo messaging from production builds. In-app only — no web push.

### Backend (optional)
- In-app Notification rows on selected driver lifecycle events

### Frontend
- Notifications screen: AppShellLayout, list, mark-read, honest empty
- Messages tab DEV-gated or removed in production

### Verification
- pytest test_driver_notifications_slice04.py PASS
- npm test + build PASS
- ride-flow E2E PASS (regression)

### Out of scope
- web push, VAPID, service worker, push subscription endpoint
```

---

## Slice 04b (optional follow-up) — Web push only

If you later want push **after** in-app is GO:

| In | Out |
|----|-----|
| VAPID keys, `sw.js`, subscription store | Changing ride idempotency |
| `POST /drivers/me/push-subscription` | OSRM |
| Send only when `notif_push_enabled` | Marketing payout claims |

Keep 04b as a **separate GO** with its own migration and security review.

---

## Related

- Slice 03 GO: `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_03.md`
- Playbook: `docs/HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01.md`
- Program truth: `docs/CURRENT_TRUTH.md`
