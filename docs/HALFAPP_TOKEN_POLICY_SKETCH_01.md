# HalfApp Token Policy Sketch

**Order:** `HALFAPP_TOKEN_POLICY_SKETCH_01`  
**Date:** 2026-05-22  
**Status:** Honest policy sketch — **not** a claim that refresh/revocation is implemented.

---

## Current JWT behavior (active path)

| Item | Current truth |
|------|----------------|
| Algorithm | HS256 (`backend/services/auth.py`) |
| Secret | `SECRET_KEY` from environment (`backend/config.py`) |
| Payload | `user_id`, `role` (`rider` \| `driver` \| `admin`), `email`, `iat`, `exp`; `sub` mirrors email |
| Storage (driver app) | `localStorage` key `driver_token` |
| Login | `POST /auth/login` → JWT returned |
| Profile | `GET /auth/me` with `Authorization: Bearer` |

Production boot rejects unsafe or short `SECRET_KEY` when `HALFAPP_ENV=production` (see `backend/production_guards.py`).

---

## Expiration assumptions

- Default TTL: `ACCESS_TOKEN_EXPIRE_MINUTES` (default **60** minutes).
- After expiry, `decode_token` returns `None`; protected routes treat the caller as unauthenticated.
- There is **no** sliding refresh window and **no** server-side session store.

---

## What is not implemented today

- **Token revocation** (logout does not invalidate issued JWTs server-side).
- **Refresh tokens** or rotation.
- **Token blocklist** / denylist.
- **Per-device session** tracking.
- **Admin-forced logout** of active driver tokens.

If a JWT is stolen before expiry, it remains valid until natural expiration unless `SECRET_KEY` is rotated (which invalidates **all** outstanding tokens).

---

## Risk today

| Risk | Severity | Mitigation today |
|------|----------|------------------|
| Stolen `driver_token` from localStorage/XSS | High | Short TTL; HTTPS in deploy; no revocation |
| Leaked `SECRET_KEY` | Critical | Production guard; never commit secrets |
| Long-lived tokens in dev | Low | Acceptable for local only |

---

## Future refresh / revocation strategy (target)

Recommended sequence before public driver production:

1. **Refresh token pair** — short-lived access JWT (15–60 min) + longer refresh token stored httpOnly cookie or secure storage on mobile.
2. **Server-side refresh store** — hashed refresh token ID, user ID, issued_at, revoked_at.
3. **Revocation endpoints** — `POST /auth/logout` marks refresh row revoked; optional access-token jti blocklist for high-security mode.
4. **Rotation on refresh** — new refresh token each use; detect reuse as compromise signal.
5. **SECRET_KEY rotation runbook** — dual-key verify window during rotation.

Do not document or UI-copy “secure logout” until revocation exists.

---

## What must be implemented before production (auth lane)

Minimum bar alongside `HALFAPP_PRODUCTION_GUARDS_SECRET_SIMULATION_CORS_01`:

- [x] Production `SECRET_KEY` boot guard  
- [x] CORS strict in production  
- [ ] Refresh + revocation (this document’s future section)  
- [ ] HTTPS-only cookie strategy if refresh is cookie-based  
- [ ] Rate limiting on `/auth/login` (not in scope of guards pass)  

---

## References

- `backend/services/auth.py`
- `backend/production_guards.py`
- `docs/DEPLOY_ENV_VARS.md`
- `docs/HALFAPP_PRODUCTION_GUARDS_SECRET_SIMULATION_CORS_01.md`
