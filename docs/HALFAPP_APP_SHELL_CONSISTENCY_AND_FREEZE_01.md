# HalfApp App Shell Consistency and Freeze

Date: 2026-05-22  
Order: `HALFAPP_APP_SHELL_CONSISTENCY_AND_FREEZE_01`  
Status: **frozen** public face + unified authenticated inner screens.

---

## Public face status

| Item | Status |
|------|--------|
| Official app title | **HalfApp** (`DriverPortalNav` brand + `HalfApp Driver Portal` hero eyebrow) |
| Logged-out `/` | `HalfAppDriverPortalFrontPage` (landing + embedded auth) |
| `/login` | Same landing; scrolls to `#access` auth panel |
| Logged-in `/` | Redirects to `/driver` cockpit |
| Dev clutter on landing | Diagnostics/cockpit dev controls not shown on public page (Playwright proof) |

**Do not redesign** the landing unless a regression is found. Screenshot proof path: run Playwright `driver-portal-frontpage.spec.ts` and capture `driver-portal-frontpage` + hero (local CI artifact / manual capture).

---

## Active app route map

| Route | Screen | Wired to backend |
|-------|--------|------------------|
| `/#/` | Public landing (logged out) | `POST /auth/login`, register |
| `/#/login` | Same landing + auth focus | same |
| `/#/driver` | Map cockpit (logged in) | `/drivers/*` |
| `/#/driver/trips` | Trips | `GET /drivers/my-rides` |
| `/#/driver/earnings` | Earnings | `GET /drivers/earnings` |
| `/#/driver/profile` | Account | `GET/PUT /drivers/profile`, stats, notifications |
| `/#/driver/notifications` | Notifications (optional route; not in bottom nav) | `GET /notifications/` |

Redirects: `/trips`, `/earnings`, `/profile` → `/driver/*` equivalents.

---

## Pages unified (this slice)

| Page | Shell | Notes |
|------|-------|-------|
| Earnings | `AppShellLayout` + `ha-*` tokens | Backend-only earnings copy preserved |
| Trips | `AppShellLayout` + `ha-*` tokens | Stored distance/duration labeled, not routing |
| Account (`Profile.jsx`) | `AppShellLayout` + tabs | Replaced light gray legacy layout; added bottom nav |
| Cockpit (`MapHome`) | Unchanged map-first layout | Regression-tested |

Shared tokens: `driver-app/src/styles/globals.css` (`--ha-*`), `driver-app/src/theme/halfAppTheme.js`.

---

## Pages intentionally not expanded

- Payment / wallet UI
- Booking / rider product surface
- Route engine, ETA, traffic, surge
- Admin dashboard
- Support / compliance workflows
- Legacy `frontend/`
- Dossier spine UI (`/supply`, `/demand`, `/trip`)

---

## Dossier spine (not wired)

Still **foundation only**. See `docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md`.

`driver-app/src/utils/api.js` has **no** calls to dossier endpoints.

---

## Stale login / auth leftovers

| File | Status |
|------|--------|
| `LoginScreen.jsx` | **Not present** in repo (already removed) |
| `HalfAppDriverPortalFrontPage.jsx` | **Active** official entrance |
| `SimpleLoginTest.jsx` | **Inactive** — not imported by `App.jsx`; dev-only artifact, kept for local auth experiments |
| `HalfAppFrontPage.jsx` | Not used by active `App.jsx` |

---

## Backend truth preserved

- Cockpit: `/drivers/presence`, heartbeat, available-rides, claim, transparency, lifecycle transitions
- No fake ETA/route/fare claims on unified screens
- Earnings/trips/account show unavailable states when API fails
- Profile clarifies profile availability vs cockpit presence endpoints

---

## Tests and build

| Command | Purpose |
|---------|---------|
| `cd driver-app && npm run build` | Production build |
| `cd driver-app && npm run test` | Unit tests |
| `cd driver-app && npx playwright test tests/driver-portal-frontpage.spec.ts` | Landing freeze |
| `cd driver-app && npx playwright test tests/app-shell-consistency.spec.ts` | Shell unity |
| `cd driver-app && npx playwright test tests/cockpit-identity.spec.ts` | Cockpit regression |
| `cd driver-app && npx playwright test tests/ride-transparency-panel.spec.ts` | Transparency |
| `cd backend && python -m pytest -q` | Backend still green |

---

## Next slice

**`HALFAPP_PUBLIC_FACE_AND_APP_SHELL_01`** — further polish of entrance and first-screen product feel while keeping cockpit and `/drivers/*` truth path unchanged. Do not wire dossier spine.
