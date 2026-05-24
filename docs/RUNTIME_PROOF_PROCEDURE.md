# Runtime proof procedure (required order)

Use this order for **any** task that proves a dependency is running (OSRM, Postgres, Redis, etc.). Do not run application proof scripts until the dependency passes a direct health check.

## Required sequence

### 1. Check the dependency first

Verify the runtime exists before starting anything.

Examples (OSRM):

```bash
docker info          # daemon must succeed
docker ps            # optional: see existing containers
```

Also confirm prerequisites are present:

- Data directory is not empty (e.g. `docker/osrm-portland/data/` contains processed `.osrm` files after extract/partition/customize).
- Required ports are free or already bound by the expected service.

**If the dependency cannot be checked or is missing → stop here.**

Report:

```txt
BLOCKED_DEPENDENCY_NOT_RUNNING
```

Do **not** run the proof script. Running it against a dead service only proves **fallback** behavior, not the target runtime.

---

### 2. Start the required service

Example (OSRM):

```bash
cd docker/osrm-portland
docker compose up -d
```

Wait until the container is running and stable (logs show `running`, or `docker compose ps` shows healthy/up).

---

### 3. Direct health check (mandatory)

Hit the service API directly — not the HalfApp proof script.

Example (OSRM):

```bash
curl "http://127.0.0.1:5000/route/v1/driving/-122.5951,45.5898;-122.6784,45.5152?overview=false"
```

Success criteria:

- HTTP 200
- JSON `"code":"Ok"` (OSRM)
- Non-zero `routes[0].distance` and `routes[0].duration`

**If health check fails → stop.**

Report:

```txt
BLOCKED_DEPENDENCY_NOT_RUNNING
```

(with the actual error: connection refused, wrong code, empty routes, etc.)

---

### 4. Only then run the proof script

Example (HalfApp OSRM Portland proof):

```bash
# Ops healthcheck (repo root — Slice 05); or backend/scripts/verify_osrm_health.py
export OSRM_BASE_URL=http://127.0.0.1:5000
bash scripts/osrm_healthcheck.sh          # must exit 0

cd backend
export ROUTING_PROVIDER=osrm_self_hosted
python scripts/verify_osrm_health.py    # must exit 0
python scripts/proof_osrm_portland_routes.py --strict --snapshot-proof --write-evidence
```

See also `docs/HALFAPP_OSRM_OPS_ONLY_SLICE_05.md`.

Evidence file: `backend/runtime_evidence/osrm_portland_proof.json` (gitignored). When valid, API `osrm_runtime_claim` advances from `not_proved` to `proved_portland_v0_1`. `production_routing_claim` stays `not_proved`.

Interpret results against the task’s GO conditions (e.g. `route_provider=osrm_self_hosted`, `used_fallback=False`).

---

## Anti-patterns (do not do)

- Running `proof_osrm_portland_routes.py` (or similar) **before** `curl` / health check succeeds.
- Re-running the proof script multiple times while the service is still down (repeated `haversine_fallback` is not evidence).
- Reporting runtime GO when only unit tests (mocked HTTP) passed.

---

## OSRM-specific reference

- Setup: `docker/osrm-portland/README.md`
- VPS runbook: `docs/OSRM_RUNTIME_PROOF_V0_2.md`
- Status: `docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md`
