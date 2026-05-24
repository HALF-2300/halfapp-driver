# HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_05 — OSRM ops-only (GO)

**Status:** GO  
**Date:** 2026-05-23  
**Lane:** Operations — healthcheck scripts + runbook + docker healthcheck  
**Depends on:** Slices 01–04 **GO**

**Maps to roadmap:** OSRM ops / `HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01` in launch playbook Blocker 2

---

## Purpose

Give operators repeatable, language-neutral scripts to verify OSRM is up before running backend proof scripts or pointing production traffic at a self-hosted instance.

This slice does **not** change routing logic, dispatch, cockpit UI, or provider marketing claims.

---

## In scope (Slice 05)

| # | Deliverable | Acceptance |
|---|-------------|------------|
| 1 | `scripts/osrm_healthcheck.ps1` | Exit 0 when OSRM returns `code: Ok` and positive distance |
| 2 | `scripts/osrm_healthcheck.sh` | Same contract on bash |
| 3 | Runbook | `docs/HALFAPP_OSRM_OPS_ONLY_SLICE_05.md` |
| 4 | Docker healthcheck | `docker/osrm-portland/docker-compose.yml` optional stanza |
| 5 | Docs | This file + playbook Section 4B updated |

---

## Out of scope (guardrails)

| Out | Reason |
|-----|--------|
| UI / copy changes | No product claim surface |
| `routing_service.py` behavior changes | Fallback stays as-is |
| Runtime proof verdict | Still `SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS` + proof script |
| Postgres CI, push, payments | Other slices / blockers |

---

## GO checklist

```markdown
### HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_05 — GO

Shipped:
- scripts/osrm_healthcheck.ps1 + scripts/osrm_healthcheck.sh
- docs/HALFAPP_OSRM_OPS_ONLY_SLICE_05.md (ops runbook)
- docker/osrm-portland compose healthcheck on Route API

Not shipped:
- Production OSRM runtime GO (separate proof run + status doc)
- Routing/dispatch/cockpit code changes
- CI job that requires live OSRM (optional Slice 05.1)
```

---

## Verification ritual

With OSRM running (`docker/osrm-portland`):

```powershell
cd c:\Users\him\Desktop\halfapp-driver
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
powershell -ExecutionPolicy Bypass -File scripts\osrm_healthcheck.ps1
```

Without OSRM: expect exit **1** (connection failure) — scripts are still valid artifacts.

Existing Python gate (unchanged):

```powershell
cd backend
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
py -3.11 scripts/verify_osrm_health.py
```

No `npm test` / ride-flow E2E required for this slice (no app diff).

---

## Rollback

Remove or revert `scripts/osrm_healthcheck.*`, runbook, and compose `healthcheck:` block. No migrations.

---

## File index

| Path | Role |
|------|------|
| `scripts/osrm_healthcheck.ps1` | PowerShell healthcheck |
| `scripts/osrm_healthcheck.sh` | Bash healthcheck |
| `docs/HALFAPP_OSRM_OPS_ONLY_SLICE_05.md` | Ops runbook |
| `docker/osrm-portland/docker-compose.yml` | Container healthcheck |
| `backend/scripts/verify_osrm_health.py` | Existing Python health gate (proof procedure) |

---

## Related

- Slice 04 GO: `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_04.md`
- Playbook: `docs/HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01.md`
- Program truth: `docs/CURRENT_TRUTH.md` (OSRM runtime still **NO_GO** until proof doc updated)
