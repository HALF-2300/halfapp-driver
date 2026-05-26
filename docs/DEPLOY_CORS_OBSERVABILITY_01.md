# DEPLOY_CORS_OBSERVABILITY_01 — Production Deploy Hardening

**Date:** 2026-05-25  
**Status:** **GO**  
**Slice:** Roadmap slice 8 — `HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`  
**Scope:** Structured request logging middleware (new). CORS already hardened in prior pass.

---

## Completion bar (from roadmap)

> CORS allowlist per environment; structured request logging with `ride_id` / `driver_id` where applicable.  
> **Done when:** Deploy checklist + `GET /internal/system-health` used in ops doc.

---

## CORS — already DONE

| Behavior | Status | Reference |
|----------|--------|-----------|
| Wildcard rejected at boot | **GO** | `backend/production_guards.py`; `docs/HALFAPP_PRODUCTION_GUARDS_SECRET_SIMULATION_CORS_01.md` §3 |
| Production explicit origins required | **GO** | `CORS_ORIGINS` env; `tests/test_production_guards.py` |
| Dev/test localhost union | **GO** | Vite/Playwright ports 3020–3034 unioned with configured origins |

---

## Structured request logging — new in this slice

### Module

`backend/middleware/request_logging.py` — `RequestLoggingMiddleware`

### Behavior

Emits one structured JSON log line per request to the `halfapp.request` logger at INFO level. Adds `X-Request-ID` to every response (echoing the client header if provided, generating UUID4 otherwise).

Each record contains:

| Field | Always present | Source |
|-------|----------------|--------|
| `request_id` | yes | `X-Request-ID` header or generated UUID4 |
| `method` | yes | HTTP method |
| `path` | yes | URL path (no query string) |
| `status` | yes | response status code |
| `duration_ms` | yes | wall-clock ms from middleware entry to response |
| `driver_id` | when authenticated | decoded from JWT Bearer `user_id` claim — **logging only, not auth** |
| `ride_id` | when path matches | extracted from `/rides/{id}` or `/drivers/rides/{id}` |

### Wiring

`backend/main.py` adds the middleware after `AuthRateLimitMiddleware`. The middleware is global — runs on every request including `/health`.

### Safety

- JWT payload is decoded **without signature verification** (logging context only). Auth decisions still go through the normal `decode_token` path.
- Malformed Bearer tokens are silently ignored — never crash a request.
- No request body is logged.

### Tests

`backend/tests/test_request_logging_middleware.py` — 7 tests:

1. Response carries auto-generated `X-Request-ID` (UUID4)
2. `X-Request-ID` is echoed when client provides it
3. Log line has all required fields and correct shape
4. `ride_id` extracted from driver path
5. `ride_id` extracted from rider path
6. `driver_id` extracted from JWT Bearer
7. Invalid Bearer header doesn't crash

```
pytest tests/test_request_logging_middleware.py
  7 passed
```

---

## Operational notes

- `halfapp.request` is the canonical logger name for ops to filter/forward.
- The middleware does not configure log handlers — deployment owns log routing (stdout, file, or aggregator).
- `/internal/system-health` is the deploy-time probe (covered separately in production guards report).

---

## Governance

| Guard | Result |
|-------|--------|
| Backend test gate | 383 passed, 9 skipped + 7 new middleware tests |
| Closed lanes | None touched (no auth/claim-lock/lifecycle changes) |
| No PSP/payout claims | N/A — observability only |

---

## What this does NOT do (deferred)

- Forward logs to an aggregator (Loki, Datadog, etc.) — deployment concern
- Add tracing (OpenTelemetry) — separate decision, not P0
- Log request/response bodies — privacy concern; not requested
- Sampling — every request currently logged; introduce sampling only if volume warrants
