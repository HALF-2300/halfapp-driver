# OPENAPI_TRUTH_SYNC_01 — Contract CI + Doc Reconciliation

**Date:** 2026-05-25  
**Status:** **GO**  
**Slice:** Roadmap slice 10 — `HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`  
**Scope:** Confirm Ticket 1.3 fail-on-drift CI; reconcile BACKLOG.md / CURRENT_TRUTH.md against shipped slices.

---

## Completion bar (from roadmap)

> OpenAPI snapshot fail-on-drift (Ticket 1.3).  
> Update `BACKLOG.md` / `CURRENT_TRUTH.md`: audit UI, route read UI **GO**; remove deferred beta from P0 queue.  
> **Done when:** Agent brain docs match code; CI blocks silent API drift.

---

## CI fail-on-drift (Ticket 1.3) — DONE_PROVEN

| Item | Status | Reference |
|------|--------|-----------|
| OpenAPI path-set snapshot | **GO** | `backend/tests/snapshots/openapi_paths.json` |
| Drift detector test | **GO** | `backend/tests/test_openapi_surface_does_not_drift.py` |
| CI job that runs it | **GO** | `.github/workflows/halfapp-driver-ci.yml` `truth-and-drift` job |
| Dossier paths excluded when flag unset | **GO** | Test handles `HALFAPP_DOSSIER_SPINE_ENABLED` env |

See `docs/BACKLOG.md` Ticket 1.3 — reclassified DONE_PROVEN in this session.

---

## Doc reconciliation completed this session

`docs/CURRENT_TRUTH.md` next-work section now reflects shipped slices:

| Slice | Report | Verdict |
|-------|--------|---------|
| 1. Internal owner test mode | `INTERNAL_OWNER_TEST_MODE_01.md` | GO |
| 4. Profile + settings shell | `PROFILE_SETTINGS_SHELL_01.md` | GO |
| 5. Notifications product UI | `NOTIFICATIONS_PRODUCT_UI_01.md` | GO |
| 6. Cockpit session resilience | `COCKPIT_SESSION_RESILIENCE_01.md` | GO (code) / TODO (E2E run) |
| 7. Token session safety | `TOKEN_SESSION_SAFETY_01.md` | GO |
| 8. Deploy CORS/observability | `DEPLOY_CORS_OBSERVABILITY_01.md` | GO |
| 9. Trips & earnings polish | `TRIPS_EARNINGS_POLISH_01.md` | GO |
| 10. OpenAPI truth sync | this doc | GO |
| P1.3 Delivery vocabulary | `P1_3_DELIVERY_VOCABULARY_PASS_01.md` (extended) | GO |

`docs/BACKLOG.md` P1 table updated: notifications, profile/settings, cockpit-session, settlement/calculation copy, CORS/observability rows marked DONE with report references.

---

## Owner-blocked items (correctly NOT marked GO)

| Slice | Status | Reason |
|-------|--------|--------|
| 2. OSRM runtime proof | **PARTIAL_GO** | Code path GO; needs Docker for runtime proof |
| 3. Postgres claim-race CI | **PARTIAL_GO** | CI job wired; needs local PG proof OR CI green run |
| G3. Owner courier day | **PENDING_OWNER** | Requires owner human walkthrough |

These remain in `CURRENT_TRUTH.md` P0 gates table as PARTIAL_GO / PENDING_OWNER per agent directives §1 ("AI must not mark G3 GO").

---

## Governance

| Guard | Result |
|-------|--------|
| Backend test gate | 390 passed (was 383; +7 new middleware tests) |
| Driver-app test gate | 150 passed |
| `assert-no-money-claims.mjs` | OK |
| `assert-no-ai-providers.mjs` | OK |
| `assert-prod-truth.mjs` | OK |
| OpenAPI drift | Snapshot test passes — no path-set change required by this session |

---

## What stays out of scope here

- Deep schema alignment (Ticket 1.3 note): full RIDE_LIFECYCLE_CONTRACT schema diff is a separate P1 hardening item; current snapshot compares **path set** only.
- Dossier surface execution (G4 decision is GO; execution deferred per `DOSSIER_PATH_DECISION_01.md`).
- External beta artifacts (explicitly out per direction reset in roadmap doc).
