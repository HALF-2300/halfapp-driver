# COCKPIT_SESSION_RESILIENCE_01 — Cockpit Session Resilience

**Date:** 2026-05-25  
**Status:** **GO (code + backend)** · **TODO (E2E live stack run)**  
**Slice:** Roadmap slice 6 — `HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`  
**Scope:** Confirm shipped implementation against completion bar. No code changes needed.

---

## Completion bar (from roadmap)

> Refresh/resume active ride; stale presence messaging; block offline during active ride; network error recovery on accept/advance.  
> **Done when:** Owner test: refresh mid-ride does not lose state; heartbeat stale → visible status.

---

## Implementation evidence

### Backend — `GET /drivers/me/active-ride`

| Item | Status | Reference |
|------|--------|-----------|
| Endpoint returns single non-terminal ride | **GO** | `backend/tests/test_active_ride_recovery.py` — 3 passed (2026-05-25) |
| Active statuses: `accepted`, `driver_arrived`, `in_progress` | **GO** | `docs/COCKPIT_SESSION_RECOVERY_V0_1.md` |
| Full `RideDriverView` payload (pricing, route metadata, dispatch fields) | **GO** | Same — service-side composition |
| `lifecycle` block (current, available_actions, history) | **GO** | Backend tests |
| Customer cancel notice when ride disappears | **GO** | MapHome.jsx:489 — "This job was cancelled by the customer…" |

### Cockpit — `MapHome.jsx` + supporting components

| Item | Status | Reference |
|------|--------|-----------|
| `useActiveRide` hook (undefined loading / null idle / object active) | **GO** | `driver-app/src/hooks/useActiveRide.js` |
| `CockpitSkeleton` during hydration (no empty-cockpit flash) | **GO** | `driver-app/src/components/cockpit/CockpitSkeleton.jsx` |
| Hydration from active-ride before marketplace refresh | **GO** | `MapHome.jsx` `hydrateFromActiveRidePayload` |
| `recoverActiveRideOnOnline` on network return | **GO** | `MapHome.jsx` — `navigator.online` handler |
| `cockpit-resume-notice` banner with ride ID + status | **GO** | `MapHome.jsx:1081-1098` |
| `data-cockpit-state` + `data-ride-id` attributes on active sheets | **GO** | E2E selectors in `session-recovery.spec.ts` |
| Stale presence messaging (`cockpit-presence-stale`) | **GO** | `MapHome.jsx:1070-1080` — orange banner when last_seen > 45s |
| Network error recovery on advance | **GO** | `MapHome.jsx:863` — degraded marker + retry-on-online |

### E2E — `driver-app/tests/session-recovery.spec.ts`

| Scenario | Spec exists | Run on this machine |
|----------|-------------|---------------------|
| Refresh @ `accepted` → `sheet-accepted_to_pickup` resumes | **YES** | Not run (no live stack) |
| Refresh @ `driver_arrived` → `sheet-arrived_pickup` resumes | **YES** | Not run |
| Refresh @ `in_progress` → `sheet-in_progress` resumes | **YES** | Not run |
| Network delay → `cockpit-skeleton` then correct sheet | **YES** | Not run |

**Why not run:** Spec requires backend on `:8011` + driver-app on `:3024` + Playwright ride-flow config. This workstation runs unit tests only. The spec itself is correctly written against the shipped implementation.

---

## Verdict per P1.2 checklist (`docs/P1_2_SESSION_RECOVERY_VERDICT_01.md`)

| Item | Status |
|------|--------|
| Backend test `test_drivers_me_active_ride_returns_single_non_terminal` | **GO** (passes) |
| E2E spec exists | **GO** |
| E2E run green | **TODO** (live stack dependency — owner-runnable) |

**Backend lane: GO. E2E lane: implementation GO, run pending owner-runnable stack.**

---

## What this means for the slice

The completion bar is met **in code**:
- Refresh mid-ride does not lose state — `MapHome` hydrates from `GET /drivers/me/active-ride` before marketplace refresh, `CockpitSkeleton` masks the load
- Heartbeat stale → visible status — `cockpit-presence-stale` banner when `last_seen_at` > 45s
- Block-offline-during-active-ride — `DriverSettings.jsx:306` calls out "Use cockpit to finish an active job before going offline" + cockpit gates the online-toggle when an active ride exists

The remaining "TODO" is a **proof verification** (E2E run), not a code gap. Owner can close by running:

```powershell
cd driver-app
npm run test:e2e:ride-flow -- tests/session-recovery.spec.ts --reporter=line
```

---

## Governance

| Guard | Result |
|-------|--------|
| Closed lanes | None touched (no claim-lock, no lifecycle guards modified) |
| Backend tests | `test_active_ride_recovery.py` 3 passed |
| Driver-app tests | 150 passed |
