# Self-Hosted Routing Proof v0.2 — STATUS

**Slice:** `RIDE_AI_ROUTE_GROUNDING_RUNTIME_PROOF_01` + Portland OSRM baseline  
**Last run:** 2026-05-25 (agent environment)  
**OSRM image:** `osrm/osrm-backend` (car profile, MLD)  
**Data:** Oregon OSM extract (`docker/osrm-portland/data/oregon-latest.osm.pbf`)

---

## Verdict (route grounding)

| Claim | Status |
|-------|--------|
| Code path (OSRM → `ground_ride_route` → `RideDriverView` → `routeContext.live`) | **GO** — see `backend/tests/test_ride_route_grounding.py`, `test_ride_ai_dispatch_route_context.py` |
| Runtime with OSRM listening | **PARTIAL** — `PARTIAL_GO_ROUTE_GROUNDING_CODE_COMPLETE_RUNTIME_PROOF_PENDING` |
| Acceptable runtime verdict (when proof passes) | `GO_SELF_HOSTED_ROUTE_GROUNDING_RUNTIME_PROVEN` |

**Do not claim Production GO** until runtime proof below completes on a host with OSRM up. OSRM proves **road-network distance/duration grounding**, not live traffic.

---

## Latest runtime proof attempt

| Check | Result |
|-------|--------|
| Docker on proof host | **Not available** (Windows agent env; `docker` not in PATH) |
| OSRM `:5000` health | **FAIL** — connection refused |
| Evidence file | `backend/runtime_evidence/ride_ai_route_grounding_runtime_proof.json` |
| Script exit code | `2` (`BLOCKED_DEPENDENCY_NOT_RUNNING`) |

```json
{
  "verdict": "PARTIAL_GO_ROUTE_GROUNDING_CODE_COMPLETE_RUNTIME_PROOF_PENDING",
  "blocker": "OSRM not listening at http://127.0.0.1:5000: [WinError 10061] ..."
}
```

---

## How to complete runtime proof (operator)

### 1. Start OSRM

```powershell
cd docker/osrm-portland
# One-time: bash prepare-data.sh  (or see README)
docker compose up -d
```

```powershell
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
powershell -ExecutionPolicy Bypass -File scripts\osrm_healthcheck.ps1
# Expected: OK: routes[0].distance=...
```

### 2. Environment

```powershell
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
$env:ROUTING_PROVIDER = "osrm_self_hosted"
$env:HALFAPP_ENABLE_RIDE_SIMULATION = "1"
$env:ROUTING_FALLBACK_ENABLED = "true"
$env:ALLOW_TEST_USER_SEED = "1"
```

### 3. Run proof (backend + API + prompt mirror + fallback)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\proof-ride-ai-route-grounding-runtime.ps1
```

Or:

```powershell
cd backend
py -3.11 scripts/proof_ride_ai_route_grounding_runtime.py
```

**Expected on success:** exit `0`, verdict `GO_SELF_HOSTED_ROUTE_GROUNDING_RUNTIME_PROVEN`, evidence JSON populated with `osrm_success_proof` and `fallback_proof`.

### 4. Optional: start backend + manual UI

```powershell
cd backend
py -3.11 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Driver app: go online → **DEV · Simulation ride** (no `distance_km` in body) → accept → confirm panel meta **"Route intelligence (grounded)"** and no `ride-ai-route-advisory-label`.

Stop OSRM (`docker compose stop`) and repeat one ride → haversine fallback, advisory label returns.

---

## Required proof checklist (filled when script exits 0)

### A. OSRM success path

| # | Requirement | Evidence field |
|---|-------------|----------------|
| 1 | `route_provider=osrm_self_hosted` | `osrm_success_proof.created` / `.accepted` |
| 2 | `route_source=osrm_v5` | same |
| 3 | `route_used_fallback=false` | same |
| 4 | `distance_km` ≠ stale `4.0` default (unless OSRM truly ~4 km) | `distance_km_not_default_4` check |
| 5 | `duration_minutes` OSRM-derived | `duration_minutes_positive` |
| 6 | `route_provider_confidence` present | same |
| 7 | `route_calculated_at` present | same |

Simulate body: `{"customer_name": "..."}` only — **no** `distance_km` / `duration_minutes` overrides.

### B. Client prompt JSON (`routeContext` mirror)

| Field | Expected (OSRM up) |
|-------|-------------------|
| `live` | `true` |
| `route_source` | `osrm_v5` |
| `route_calculated_at` | ISO timestamp |
| `route_provider_confidence` | e.g. `0.91` |
| `distance_meters` | > 0 |
| `duration_seconds` | > 0 |
| `advisory_label` | empty |
| `live_traffic` | `true` (grounded geometry — **not** real-time traffic) |

Captured in evidence: `osrm_success_proof.prompt_context`.

### C. UI expectation (manual or Playwright)

| UI | OSRM success |
|----|----------------|
| Panel meta | "Route intelligence (grounded)" |
| `ride-ai-route-advisory-label` | **hidden** |

### D. Fallback honesty (OSRM down)

| Field | Expected |
|-------|----------|
| `route_provider` | `haversine_fallback` |
| `used_fallback` | `true` |
| `live` | `false` |
| `advisory_label` | `[ADVISORY · AI ESTIMATE · NOT LIVE TRAFFIC]` |

Proof uses closed port `59998` with `ROUTING_FALLBACK_ENABLED=true`. Evidence: `fallback_proof`.

---

## Portland route legs (baseline v0.2)

| Route | Code | Distance (m) | Duration (s) | Provider |
|-------|------|--------------|--------------|----------|
| PDX downtown → airport | _pending live OSRM_ | _pending_ | _pending_ | `osrm_self_hosted` |
| Pearl District → OHSU | _pending_ | _pending_ | _pending_ | `osrm_self_hosted` |
| Hawthorne → Airport | _pending_ | _pending_ | _pending_ | `osrm_self_hosted` |

```powershell
cd backend
$env:OSRM_RUNTIME_URL = "http://127.0.0.1:5000"
py -3.11 -m pytest tests/test_osrm_runtime_integration.py -v
py -3.11 scripts/proof_osrm_portland_routes.py --write-evidence
```

---

## Code readiness (verified in repo)

| Component | Location |
|-----------|----------|
| OSRM HTTP client | `services/osrm_self_hosted_provider.py` |
| Routing + fallback | `services/routing_service.py` |
| Ride stamp on create/accept | `services/ride_route_grounding.py`, `routes/drivers.py` |
| API fields | `RideDriverView` + `map_foundation_dict()` |
| Client `routeContext` | `driver-app/src/services/rideAiDispatch/routeContext.js` |
| Prompt mirror (proof) | `services/ride_ai_dispatch_route_context.py` |
| Simulation default fix | `SimulationRideCreate.distance_km` optional (no forced `4.0`) |
| Runtime proof script | `backend/scripts/proof_ride_ai_route_grounding_runtime.py` |

---

## Staging VPS (unchanged blocker for Portland batch proof)

| Check | Result |
|-------|--------|
| `infra/staging/staging.env` `VPS_IP` | `0.0.0.0` / `PROVISION_PENDING` |
| Full Portland latency table | _pending VPS + Docker_ |

---

## Honesty contract

- **OSRM success:** `route_provider=osrm_self_hosted`, `route_used_fallback=false`, `route_source=osrm_v5`. Advisory label **off**. UI may say "grounded" — means road network, not traffic.
- **OSRM failure:** `haversine_fallback`, `route_used_fallback=true`, `live=false`, advisory label **on**. Do not suppress.
- **Not claimed:** Mapbox/Google live traffic, production multi-instance deploy, Production GO.

---

## Verdict history

| Date | Environment | Verdict |
|------|-------------|---------|
| 2026-05-24 | Staging VPS not provisioned | OSRM runtime **NO_GO** (blocked) |
| 2026-05-25 | Local Windows, no Docker/OSRM | **PARTIAL_GO_ROUTE_GROUNDING_CODE_COMPLETE_RUNTIME_PROOF_PENDING** |
| _pending_ | Local/staging with `docker compose up` + proof script | **GO_SELF_HOSTED_ROUTE_GROUNDING_RUNTIME_PROVEN** |

When `GO_SELF_HOSTED_ROUTE_GROUNDING_RUNTIME_PROVEN` is recorded, update `docs/RIDE_AI_DISPATCH_PRODUCTION_PROOF_GATES_01_REPORT.md` route gate to **runtime-proven** (still not full Production GO without quota/deploy items).
