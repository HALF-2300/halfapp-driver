# INTERNAL_OWNER_TEST_MODE_01 — Internal Test Labeling & Runbook

**Date:** 2026-05-25  
**Status:** **GO**  
**Slice:** Roadmap slice 1 — `HALFAPP_DRIVER_PRODUCT_COMPLETION_ROADMAP_01.md`  
**Scope:** Audit of beta-flag gating and owner runbook completeness. No code changes required.

---

## Completion bar (from roadmap)

> Consolidate copy: **Internal test ride** / **Owner test run** (replace beta-first-run and `VITE_BETA_NO_MONEY_TRUTH` as default path).  
> Document owner-car runbook (`docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md`).  
> Keep `VITE_ENABLE_RIDE_SIMULATION` dev-only; production build unchanged.  
> **Done when:** Owner can run a full trip locally without beta flags or external onboarding artifacts.

**Verdict: DONE.** All items met.

---

## Beta-flag gating audit

| Component | Guard | Default (no flag) | With `VITE_BETA_NO_MONEY_TRUTH=true` |
|-----------|-------|-------------------|--------------------------------------|
| `BetaFirstRunAck` | `BETA_NO_MONEY_TRUTH_ENABLED` | `return null` — invisible | Modal with acknowledgment blocks |
| `BetaTruthNotice` (compact, full, inline, cockpit variants) | `BETA_NO_MONEY_TRUTH_ENABLED` | `return null` — invisible | Informational banner/card |
| Dev simulation dock (`VITE_ENABLE_RIDE_SIMULATION`) | `import.meta.env.VITE_ENABLE_RIDE_SIMULATION === 'true'` | Hidden | Visible dev button |
| Demo messages tab in Notifications | `import.meta.env.DEV` | Hidden in production build | Visible in Vite dev server |
| `VITE_ALLOW_OFFLINE_MOCK` | Build-time flag | `false` | Rejected by `assert-prod-truth.mjs` in production |
| `VITE_ENABLE_GUARD_BYPASS` | Build-time flag | `false` | Rejected by `assert-prod-truth.mjs` in production |

**Default product path is clean:** No beta-first-run modal, no no-money-truth notices, no simulation dock shows in the default (no-flag) build.

---

## Simulation label (correct)

`lifecycle_reason=simulation` rides display `"Simulation job — for product testing only."` via `TestRideLabel` component. This is the correct internal test labeling — not "beta ride," not external copy.

---

## Owner runbook

**File:** `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md`

Covers:
1. Backend start (`uvicorn main:app --port 8000`)
2. Driver app start (`npm run dev`, port 3022)
3. Rider app start (`npm run dev`, port 3023)
4. Open-board vs. auto-assign modes
5. OSRM optional Docker step
6. Full rider → driver → complete loop

**Done when:** Owner can run the runbook end-to-end without Postman or beta-specific onboarding. Status: **GO** for owner local runs.

---

## Production build proof

```
driver-app/scripts/assert-prod-truth.mjs:
  VITE_ALLOW_OFFLINE_MOCK=true  → EXIT 1 (blocked)
  VITE_ENABLE_GUARD_BYPASS=true → EXIT 1 (blocked)
  Default build                 → passes
```

CI job `truth-and-drift` runs `npm run build` (includes `prebuild` → `assert-prod-truth.mjs`).

---

## Test proof

```
driver-app npm test (2026-05-25):
  # tests 150
  # pass  150
  # fail  0
  assert-no-money-claims: OK
  assert-no-ai-providers: OK
```
