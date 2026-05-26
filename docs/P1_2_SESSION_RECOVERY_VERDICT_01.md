# P1.2 — Session recovery verdict

**Date:** 2026-05-25  
**Rule:** GO only if all three checks exist **and pass**. Otherwise **TODO**.

---

## Checklist

| # | Requirement | Exists | Pass (this run) | Verdict |
|---|-------------|--------|-----------------|---------|
| 1 | Backend `test_drivers_me_active_ride_returns_single_non_terminal` | **YES** — `backend/tests/test_active_ride_recovery.py` | **YES** — `pytest tests/test_active_ride_recovery.py` → 3 passed | **GO** |
| 2 | E2E `driver-app/tests/session-recovery.spec.ts` | **YES** | **NOT RUN** — requires ride-flow stack (backend + driver-app + Playwright) | **TODO** |
| 3 | Hard reload during `in_progress` preserves state | **YES** — parameterized case in `session-recovery.spec.ts` (lines 111–133): `page.reload()` + `expectActiveSheet(..., 'in_progress', ride.id)` | **NOT RUN** (same E2E dependency) | **TODO** |

---

## Item 1 — Backend

**Test:** `test_drivers_me_active_ride_returns_single_non_terminal`

- Seeds two **completed** rides + one **in_progress** ride for the same driver.
- Asserts `GET /drivers/me/active-ride` returns the in-progress job only.

```bash
cd backend && pytest tests/test_active_ride_recovery.py::test_drivers_me_active_ride_returns_single_non_terminal -q
```

**Result:** PASS (2026-05-25 agent run).

---

## Item 2 — E2E spec

**File:** `driver-app/tests/session-recovery.spec.ts`  
**Config:** `playwright.ride-flow.config.js`

```bash
cd driver-app
npm run test:e2e:ride-flow -- tests/session-recovery.spec.ts --reporter=line
```

**Result:** Not executed — no E2E stack started in this session.

---

## Item 3 — Hard reload @ in_progress

Covered by the same spec as item 2 (`STATES` includes `in_progress`; reload + sheet assertions).

**Result:** Not executed.

---

## Overall P1.2 status: **TODO**

- Backend lane: **GO**
- E2E lane: **TODO** until `session-recovery.spec.ts` is run green on the ride-flow stack

**To reach GO:** run the Playwright command above with backend on `:8000` and driver-app per `docs/COCKPIT_SESSION_RECOVERY_V0_1.md`.
