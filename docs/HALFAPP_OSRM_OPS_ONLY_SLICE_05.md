# HALFAPP_OSRM_OPS_ONLY_SLICE_05 — OSRM ops-only runbook

**Status:** GO (ops artifacts)  
**Date:** 2026-05-23  
**Lane:** Operations — prove OSRM runtime, troubleshoot, keep fallback labeling honest  

**Maps to:** `HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_05`, `HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01`, Blocker 2 in `docs/HALFAPP_LAUNCH_BLOCKERS_CODE_FIRST_PLAYBOOK_01.md`

---

## Purpose

Prove OSRM runtime availability and provide an ops workflow for monitoring and troubleshooting.

**No product/UI claims change.** Routing logic and haversine fallback behavior are unchanged. Runtime proof for production launch still follows `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md`.

---

## OSRM Route API (quick reference)

Canonical point-to-point request:

```http
GET /route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false&steps=false
```

Success response includes `"code": "Ok"` and `routes[0].distance` / `duration` in meters and seconds.

Docs: [OSRM HTTP API](http://project-osrm.org/docs/v5.24.0/api/#route-service)

---

## Healthcheck scripts (repo root)

| Script | When to use |
|--------|-------------|
| `scripts/osrm_healthcheck.ps1` | Windows / PowerShell |
| `scripts/osrm_healthcheck.sh` | Linux / macOS / Git Bash |
| `backend/scripts/verify_osrm_health.py` | Python path (same contract; used in `RUNTIME_PROOF_PROCEDURE.md`) |

All require **`OSRM_BASE_URL`** (no trailing slash required). Default local proof stack: `http://127.0.0.1:5000`.

### Windows

```powershell
cd c:\Users\him\Desktop\halfapp-driver
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
powershell -ExecutionPolicy Bypass -File scripts\osrm_healthcheck.ps1
echo $LASTEXITCODE
```

### Linux / macOS

```bash
cd /path/to/halfapp-driver
export OSRM_BASE_URL="http://127.0.0.1:5000"
bash scripts/osrm_healthcheck.sh
echo $?
```

### Expected success

- Exit code **0**
- stdout contains `OK: routes[0].distance=<positive>`

### Expected failure modes

| Exit | Meaning |
|------|---------|
| **2** | `OSRM_BASE_URL` not set |
| **1** | OSRM unreachable, non-Ok code, no routes, or zero distance |

---

## Start OSRM (Portland proof stack)

See `docker/osrm-portland/README.md` for one-time data prep.

```bash
cd docker/osrm-portland
docker compose up -d
```

Compose includes a **container healthcheck** on the same Route API path (requires `curl` in the image; if the check stays unhealthy, use the host scripts above).

---

## Troubleshooting checklist

1. **Endpoint reachable** — DNS, port `5000`, firewall, correct host in `OSRM_BASE_URL`
2. **Container/service running** — `docker compose ps`, container health status
3. **Dataset loaded** — `docker/osrm-portland/data/` contains processed `oregon-latest.osrm` after extract/partition/customize
4. **Profile** — proof stack uses `driving` (car.lua extract)
5. **Backend env** (when running HalfApp against OSRM):
   - `ROUTING_PROVIDER=osrm_self_hosted`
   - `OSRM_BASE_URL=http://127.0.0.1:5000` (or your host)
   - `ROUTING_FALLBACK_ENABLED=true` (fallback must stay enabled until runtime is proved GO)
6. **After healthcheck passes** — run `backend/scripts/proof_osrm_portland_routes.py` and update `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` per `docs/RUNTIME_PROOF_PROCEDURE.md`

---

## Truth boundary (do not regress)

| State | UI / API labeling |
|-------|-------------------|
| OSRM up, proof script GO | `route_provider=osrm_self_hosted`, `used_fallback=false` where applicable |
| OSRM down or healthcheck fails | `haversine_fallback`, `used_fallback=true` — honest, not road-network truth |
| Runtime not proved for prod | Do **not** claim production OSRM in marketing or `CURRENT_TRUTH` |

Trip audit / route truth UI must keep **`osrm_runtime_claim: not_proved`** until the runtime status doc is **GO**.

---

## Slice 05.1 (optional, still ops-only)

- Cron / scheduled task calling `osrm_healthcheck.*` with alert on non-zero exit
- No application code changes required

---

## Related

- `docs/HALFAPP_DRIVER_PRODUCT_COMPLETION_SLICE_05.md` — slice GO checklist
- `docs/RUNTIME_PROOF_PROCEDURE.md` — full Portland proof steps
- `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` — runtime verdict
- `backend/services/routing_service.py` — OSRM try → haversine fallback
