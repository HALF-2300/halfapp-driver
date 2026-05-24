# HalfApp public face and app shell (freeze 01)

**Directive:** `HALFAPP_LANDING_PAGE_FREEZE_AND_SHELL_CLEANUP_01`  
**Active surface:** `driver-app` only (backend contracts unchanged except existing auth paths).

## What changed

The plain centered login card was replaced with a **driver portal landing page** — a full public face with hero, capabilities, safety copy, embedded auth at `#access`, and footer. Legacy `LoginScreen.jsx` was removed after confirming it was unused in the active app shell.

| Area | Active files |
|------|----------------|
| Shell route | `driver-app/src/App.jsx` |
| Public face | `HalfAppDriverPortalFrontPage.jsx` + `driver-portal.css` |
| Subcomponents | `DriverPortalNav`, `DriverPortalHero`, `DriverPortalCapabilities`, `DriverAuthAccessPanel`, `DriverPortalFooter`, `DriverPortalCockpitPreview` |
| Compatibility | `HalfAppFrontPage.jsx` re-exports `HalfAppDriverPortalFrontPage` for stable import paths |
| Removed | `LoginScreen.jsx`, orphaned `halfapp-frontpage.css` |

`index.html` title: **HalfApp**.

## Active route behavior

Hash router (`driver-app`):

| Route | Logged out | Logged in |
|-------|------------|-----------|
| `/` | Driver portal landing | Redirect → `/driver` |
| `/login` | Same landing; scrolls to `#access` | Redirect → `/driver` |
| `/driver` | Redirect → `/` | Map cockpit (`MapHome`) |
| `/driver/trips`, `/earnings`, `/profile`, `/notifications` | Redirect → `/` | Protected screens |
| `/rides`, `/trips`, `/earnings`, … | Redirect to `/driver/*` aliases | — |
| `*` | Redirect → `/` | — |

**Logout** (`MapHome`) → `navigate('/')` → public landing.

**Protected routes** use `ProtectedRoute`: unauthenticated users (no token / no `isAuthenticated`) → `<Navigate to="/" replace />`.

## Auth behavior

- **Driver sign-in / sign-up** uses existing `useAuth` → `driverAPI.login` / `register`.
- Validation unchanged: `validateLoginData`, `validateRegistrationData` (email, password, name, `license_no` on signup).
- Successful auth → `navigate('/driver', { replace: true })`.
- **DEV MODE** and **mock-mode** banners render at app shell level (`DevBanner`, `MockModeBanner`), not inside the hero.

## Customer / rider entry (intentionally absent)

This repo’s active app is the **driver portal only**.

- No rider/customer role tabs on the public face.
- No customer sign-in, booking, payment, Stripe, or trip-request UI.
- No fake ride availability or map request flow for riders.
- Backend driver auth still rejects non-driver roles at the API layer.

A shared rider/customer product surface is **out of scope** for this freeze; do not mirror landing into legacy `frontend/`.

## Legacy `frontend/` — not touched

The dormant multi-role `frontend/` app was **not** updated, revived, or mirrored. HalfApp’s active public face lives only in `driver-app`.

## Screenshot / evidence

- `driver-app/tests/screenshots/halfapp-frontpage.png` (captured from production build preview; driver portal layout)

## Build (reference)

```text
vite build — PASS (see CI/local run in freeze report)
dist/assets/index-*.css ~70 kB
dist/assets/index-*.js  ~424 kB
```

## Tests

- Unit: `npm run test` (`driver-app/tests/unit/*.test.js`)
- E2E: `npm run test:e2e` — includes `driver-portal-frontpage.spec.ts` (landing, auth panel, cockpit login, protected redirect, logout, no rider surface, dev banner outside hero)
- Trust mock-off suite uses `driver-portal-frontpage` test id (separate config)

## Next recommended UI slice

**Unify Earnings, Trips, and Account (Profile)** with the driver portal design system (`driver-portal.css` tokens: dark surfaces, glass cards, `dp-btn` patterns) so post-login navigation feels continuous with the public face — without adding marketplace, payments, or customer flows.
