# Final Report: HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01

**Verdict: PARTIAL_GO** (`BLOCKED_RUNTIME_HOST`)  
**Date:** 2026-05-22  
**Runtime GO on this host:** No — Docker/OSRM not available here.  
**`osrm_runtime_claim` changed:** No — remains `not_proved` until evidence file is written on a Docker-capable host.

## Host environment

| Check | Result |
|-------|--------|
| OS | Windows 10 (`win32 10.0.26200`) |
| `docker` CLI | **Not found** on PATH |
| `http://127.0.0.1:5000` | **Connection refused** |
| `docker/osrm-portland/data/` | **Missing** (Oregon extract not prepared on this machine) |

## OSRM startup evidence

Not performed — blocked at procedure step 1 (`docker info`).

**VPS / Linux commands to run when unblocked:**

```bash
cd docker/osrm-portland
# one-time: see README.md (extract / partition / customize Oregon PBF)
docker compose up -d
docker compose ps
curl "http://127.0.0.1:5000/route/v1/driving/-122.5951,45.5898;-122.6784,45.5152?overview=false"
```

## Route request evidence

Not collected on this host. Health check output:

```text
BLOCKED_DEPENDENCY_NOT_RUNNING
error: [WinError 10061] No connection could be made because the target machine actively refused it
```

**Expected GO excerpt (when OSRM is up, strict mode):**

```text
route_provider:      osrm_self_hosted
used_fallback:       False
distance_km:         <from OSRM>
duration_minutes:    <from OSRM>
```

## Snapshot evidence

Not collected on this host. Proof tooling supports:

```bash
cd backend
python scripts/proof_osrm_portland_routes.py --strict --snapshot-proof --write-evidence
```

which persists a `diagnostic` `route_snapshots` row with `route_provider=osrm_self_hosted`, `used_fallback=false`.

## Fallback behavior

Code path verified by unit tests (`test_fallback_when_osrm_unavailable`). Proof script includes a **fallback honesty leg** (OSRM on dead port `59998` + `ROUTING_FALLBACK_ENABLED=true` → `haversine_fallback`). Not executed live here because primary proof did not start.

## Docs changed

| File | Change |
|------|--------|
| `docs/HALFAPP_OSRM_RUNTIME_PROOF_PORTLAND_01_REPORT.md` | This report |
| `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md` | Re-check note + proof command order |
| `docs/RUNTIME_PROOF_PROCEDURE.md` | `verify_osrm_health.py` + evidence file behavior |

## Code / tooling added (no fake GO)

| Piece | Purpose |
|-------|---------|
| `backend/scripts/verify_osrm_health.py` | Mandatory curl-equivalent health gate |
| `backend/scripts/proof_osrm_portland_routes.py` | `--strict`, `--write-evidence`, `--snapshot-proof`, fallback leg |
| `backend/services/osrm_runtime_truth.py` | Reads validated evidence; gates `osrm_runtime_claim` |
| `backend/tests/test_osrm_runtime_truth.py` | Evidence validation tests |
| `backend/tests/test_osrm_runtime_proof_portland.py` | Live test (skipped unless `HALFAPP_OSRM_RUNTIME_PROOF=1` + OSRM up) |
| `route_snapshots_read.py`, `ride_audit.py` | Use `osrm_runtime_claim()` |
| `driver-app/.../routeTruthFormat.js` | Honest label when claim is `proved_portland_v0_1` |

## Commands run

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
python scripts/verify_osrm_health.py          # exit 2 BLOCKED
python -m pytest -q                           # 265 passed, 1 skipped
```

```powershell
cd c:\Users\him\Desktop\halfapp-driver\driver-app
npm test                                      # 78 passed (after route truth test add)
```

## Test results

| Suite | Result |
|-------|--------|
| Backend `pytest -q` | **265 passed, 1 skipped** |
| OSRM health on this host | **BLOCKED** (exit 2) |
| Driver `npm test` | Run locally after pull (1 new unit test) |

## Whether `osrm_runtime_claim` may change from `not_proved`

| Condition | Claim |
|-----------|--------|
| **This session (Windows dev)** | **No** — stays `not_proved` |
| **After VPS/Docker GO proof** | **Yes** — run proof with `--write-evidence`, commit or deploy `backend/runtime_evidence/osrm_portland_proof.json`, re-run API tests; claim becomes `proved_portland_v0_1` |
| **`production_routing_claim`** | **Unchanged** — stays `not_proved` until a separate production launch proof lane |

## Remaining next slice

1. Prepare `docker/osrm-portland/data/` on Linux/VPS.
2. `docker compose up -d` + curl `code: Ok`.
3. `python scripts/proof_osrm_portland_routes.py --strict --snapshot-proof --write-evidence`.
4. Commit evidence JSON (or mount on server) + update this report to **GO**.
5. Optional: `HALFAPP_OSRM_RUNTIME_PROOF=1 pytest tests/test_osrm_runtime_proof_portland.py`.

## Closed lanes (not reopened)

Route snapshot read UI, driver audit UI, dispatch/lifecycle/pricing, payments, dossier, ride-product AI.
