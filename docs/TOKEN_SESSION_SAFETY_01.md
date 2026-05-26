# TOKEN_SESSION_SAFETY_01 — Refresh / Revocation MVP

**Date:** 2026-05-25  
**Status:** **GO**  
**Slice:** Roadmap slice 7 — `HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`  
**Scope:** Audit of already-shipped refresh-token rotation and revocation against completion bar.

---

## Completion bar (from roadmap)

> Design doc + minimal implementation (refresh token or rotation + revocation list).  
> Driver UI: "Sign out everywhere" on profile/settings.  
> **Done when:** Lost-device scenario covered by tests; no infinite-lived JWT without ops story.

**Verdict: DONE.** Shipped under `HALFAPP_AUTH_REFRESH_REVOCATION_01`.

---

## Implementation

| Item | Status | Reference |
|------|--------|-----------|
| Refresh token table | **GO** | Migration `0016_refresh_tokens_foundation` |
| Token rotation on refresh | **GO** | `backend/services/auth.py` `rotate_refresh_token` |
| Logout-all-devices revocation | **GO** | `routes/auth.py` `revoke_all_refresh_tokens` at logout-all and password-change |
| Driver UI: "Sign out all devices" | **GO** | `DriverSettings.jsx` headerAction — `data-testid="settings-logout-all-btn"` |
| Driver UI: "Sign out" | **GO** | `DriverSettings.jsx` — `data-testid="settings-logout-btn"` |
| Lost-device test coverage | **GO** | `backend/tests/test_auth_refresh_rotation.py` |

---

## Driver UX

`/driver/settings` provides:

1. **Sign out** — revokes the current session.
2. **Sign out all devices** — revokes refresh tokens on the server for the user. Title attribute: "Revokes refresh tokens on the server."
3. **Password change** — when successful, displays "Password updated. Other devices were signed out." (implicit revoke-all).

Session section also surfaces:
- Refresh token presence (`hasRefresh`)
- Last seen timestamp
- Active job (backend)

---

## Governance

| Guard | Result |
|-------|--------|
| `tests/test_auth_refresh_rotation.py` | Passes |
| Closed lanes | AUTH-001 not modified |
| No client-side secret persistence beyond `driver_token` + `driver_refresh_token` | OK — both in localStorage, scoped to driver app |
