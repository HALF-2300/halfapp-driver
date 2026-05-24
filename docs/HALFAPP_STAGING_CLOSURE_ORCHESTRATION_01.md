# HalfApp Staging Closure — Agent Orchestration

**Date:** 2026-05-24  
**Goal:** Close the proof gap — from "works in pytest on SQLite" to "works on PostgreSQL + deployed staging + live OSRM, with an honest owner-day."

**Owner principle:** No agent waits for credentials. Infra plans, Dockerfiles, scripts, and env templates ship first. `[HUMAN GATE]` marks exactly where a human must provide a credential or click a button.

---

## Dependency graph

```
Agent 1 (infra plan + deploy scripts)
   ├──> [HUMAN GATE: provision VPS, ~15 min] ──> Agent 1 finalizes
   │       ├──> Agent 2 (OSRM runtime)
   │       └──> Agent 3 (Postgres migration + race test)
   │
Agent 4 (surface-freeze test fixes)      ── independent, minute zero
Agent 5 (SSE for ride pool)               ── independent (code GO; staging proof pending)
Agent 6 (cockpit session recovery)        ── independent (code GO; staging proof pending)
Agent 7 (rider stub)                      ── independent (code GO; staging proof pending)
Agent 8 (cockpit visual polish)           ── independent (code GO; staging proof pending)
```

**Critical path:** Agent 1 → Agent 2 → owner-day demo.  
**Parallel from minute zero:** Agents 4–8.

---

## P0 closure definition

A P0 is closed only when:

1. A `docs/<NAME>_PROOF_V0_X.md` exists with literal commands run and literal output.
2. The corresponding pytest or Playwright test passes against the **real** environment, not a mock.
3. `docs/CURRENT_TRUTH.md` is updated with the new GO/NO_GO state.

Do not mark anything green in `CURRENT_TRUTH.md` based on code review alone.

---

## Agent status board (2026-05-24)

| # | Agent | Output | P0 | Blocks demo | Status |
|---|-------|--------|----|-------------|--------|
| 1 | Infra & deploy | `infra/staging/*` runbook, Compose, env template | Yes | Yes | **Ready for merge** — scripts exist; proof **NO_GO** until GATE-VPS-1 |
| 2 | OSRM runtime | OSRM on staging, route curl passes | Yes | Yes | **Blocked on GATE-VPS-1** — runbook `docs/OSRM_RUNTIME_PROOF_V0_2.md` |
| 3 | PostgreSQL | Neon DB, alembic head, 10-driver race | Yes | Yes | **Blocked on GATE-NEON-1** — local proof GO; Neon proof pending |
| 4 | Test repair | 345/345 green (7 skipped), CURRENT_TRUTH updated | Yes | No | **Ready for merge** |
| 5 | SSE pool | `/drivers/available-rides/stream` + EventSource | No | Yes | **Code GO** — `docs/SSE_RIDE_POOL_V0_1.md`; staging proof pending |
| 6 | Session recovery | `/drivers/me/active-ride` + rehydrate | No | Yes | **Code GO** — `docs/COCKPIT_SESSION_RECOVERY_V0_1.md` |
| 7 | Rider stub | `rider-stub/` single-page app | No | Yes | **Code GO** — `rider-stub/index.html` |
| 8 | Visual polish | CARTO tiles, motion, conflict panel | No | Yes | **Code GO** — `docs/COCKPIT_VISUAL_V0_2.md`; screenshots pending |

---

## Human gates (~30 min total)

| Gate | Where | What you do |
|------|-------|-------------|
| **GATE-VPS-1** | After Agent 1 artifacts | Spin up Hetzner/DO box; paste IP into `infra/staging/env/staging.env.local` (`STAGING_HOST`) |
| **GATE-NEON-1** | After Agent 3 plan | Sign up at [neon.tech](https://neon.tech); project `halfapp-staging`; paste `DATABASE_URL` into `env/staging.env.local` → `/etc/halfapp/staging.env` on VPS |
| **GATE-DNS-1** | After nginx deploy | Optional: A-record `staging.halfapp.app` → VPS IP |
| **GATE-STADIA-1** | After Agent 8 | Optional: [stadiamaps.com](https://stadiamaps.com) API key; default is CARTO public tiles |

Everything else is autonomous once gates are cleared.

---

## Agent 1 — provision (GATE-VPS-1)

**Copy template:**

```bash
cp infra/staging/env/staging.env.template infra/staging/env/staging.env.local
# fill STAGING_HOST, DATABASE_URL (GATE-VPS-1 + GATE-NEON-1)
```

**Hetzner (preferred):**

```bash
export HCLOUD_TOKEN="<token>"
bash infra/staging/scripts/provision-hetzner.sh
ssh -i ~/.ssh/halfapp_staging_ed25519 halfapp@$VPS_IP docker ps
```

**Any VPS:**

```bash
scp infra/staging/staging.env.local root@VPS_IP:/etc/halfapp/staging.env
ssh root@VPS_IP 'REPO_URL=https://github.com/YOUR_ORG/halfapp-driver.git bash -s' \
  < infra/staging/scripts/01_provision_vps.sh
```

**Proof doc:** `docs/STAGING_INFRA_PROOF_V0_1.md` (fill after GATE-VPS-1).

---

## Agent 2 — OSRM (after VPS)

```bash
bash infra/staging/scripts/run-osrm-remote.sh
# on VPS: curl -s 'http://127.0.0.1:5000/route/v1/driving/-122.6765,45.5152;-122.5968,45.5887?overview=false' | jq .code
# expect: "Ok"
```

**Proof doc:** `docs/OSRM_RUNTIME_PROOF_V0_2.md`

---

## Agent 3 — PostgreSQL (GATE-NEON-1)

```bash
# on laptop with DATABASE_URL set to Neon
cd backend
alembic upgrade head
py -3.11 -m pytest tests/test_postgres_claim_race_proof_01.py -s
```

**Proof doc:** `docs/HALFAPP_POSTGRES_CLAIM_RACE_PROOF_01_REPORT.md` (Neon section TBD)

---

## Agent 4 — test gate

```powershell
cd backend
py -3.11 -m pytest tests -q
# expect: 345 passed, 7 skipped, 0 failed
```

---

## Owner-day demo script (after critical path GO)

1. Open `rider-stub/index.html` → create ride (Portland addresses).
2. Open driver cockpit (two windows) → SSE shows pool delta without refresh.
3. Claim ride → hard refresh → session recovery restores sheet stage.
4. Complete ride → verify route provider is `osrm` (not `haversine_fallback`) in transparency panel.

---

## Branch naming

Each agent commits to `agent-N-<task>` with:

- Proof doc path
- Test commands + output
- Files changed list
- One line: **Ready for merge / Blocked on X / Question for human**

Do not merge to `main` until the proof doc is in the PR.
