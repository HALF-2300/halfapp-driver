# Owner Internal Test Runbook — Two-Sided Loop

**Purpose:** Run a full **rider → driver → complete** trip locally without Postman, beta flags, or legacy UI.  
**Checklist:** `docs/HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md` (Phase 1 exit).

---

## Prerequisites

- Python 3.11, Node 18+
- Ports free: **8000** (API), **3022** (driver), **3023** (rider), **3024** (ops)
- Optional: Docker OSRM on **5000** (routing falls back to haversine if down)

**Route grounding runtime proof** (when OSRM is up): see `docs/SELF_HOSTED_ROUTING_PROOF_V0_2_STATUS.md`. One command:

```powershell
cd docker/osrm-portland; docker compose up -d
powershell -ExecutionPolicy Bypass -File scripts\proof-ride-ai-route-grounding-runtime.ps1
```

**Ride AI dispatch tiers:** **GO_DEMO_SAFE** (Playwright 2/2). Production routing: **PARTIAL_GO_PRODUCTION_ROUTE_CODE_COMPLETE_RUNTIME_PROOF_PENDING** — `docs/RIDE_AI_DISPATCH_PRODUCTION_PROOF_GATES_01_REPORT.md` §7. **Production GO not claimed.**

---

## 1. Backend

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
# Phase 2 auto-assign (nearest online approved driver):
# HALFAPP_AUTO_ASSIGN=1
# HALFAPP_AUTO_ASSIGN_MODE=nearest
py -3.11 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Verify: `http://127.0.0.1:8000/health` → `{"status":"ok",...}`

---

## 2. Driver app

```powershell
cd c:\Users\him\Desktop\halfapp-driver\driver-app
npm install
npm run dev
```

Open: `http://127.0.0.1:3022`

1. Register a **driver** (license required).
2. If approval is pending in your DB, approve via admin API or test helper — approved drivers only see/accept rides.
3. Go **online** on the map cockpit.
4. With **Phase 2** (`HALFAPP_AUTO_ASSIGN=1` in backend `.env`), a rider request should auto-assign — cyan “Ride auto-assigned” banner; skip Accept.

---

## 3. Rider app

```powershell
cd c:\Users\him\Desktop\halfapp-driver\rider-app
npm install
npm run dev
```

Open: `http://127.0.0.1:3023`

1. **Register** a rider account (separate email from driver).
2. Enter Portland-area pickup and destination (e.g. `Pioneer Courthouse Square` → `Portland Airport`).
3. Tap **Request ride**.

---

## 4. Complete the loop (driver)

**Open-board mode** (`HALFAPP_AUTO_ASSIGN=0`): find ride on incoming sheet → **Accept**.

**Auto-assign mode** (`HALFAPP_AUTO_ASSIGN=1`): ride appears assigned — skip Accept → **Arrive at pickup** → **Start** → **Complete**.

On rider app, confirm status moves: looking for driver → assigned → on the way → **Trip complete**.

**Phase 3:** Rider should show estimated fare before request and receipt on complete. Driver **Earnings** shows captured ride payments.

---

## 5. Ops console (Phase 4)

```powershell
cd c:\Users\him\Desktop\halfapp-driver\ops-app
npm install
npm run dev
```

Open: `http://127.0.0.1:3024`

1. Sign in with an **admin** account (`POST /auth/admin/login`).
   - Dev seed (when `ALLOW_TEST_USER_SEED=true`):  
     `POST /internal/test-users` with `{"role":"admin","email":"ops@local.test","password":"pw12345","name":"Ops"}`
2. **Rides** tab — confirm the trip appears with status + payment.
3. Open ride detail — lifecycle events + payment state visible.
4. **Drivers** tab — driver shows online / in_ride / available.
5. Optional: cancel an in-flight test ride from ops and confirm rider/driver reflect cancellation.

---

## 6. Verify backend truth (optional)

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
py -3.11 -m pytest tests/test_ride_flow_ui_proof.py tests/test_rider_auth.py tests/test_rider_ride_stream.py tests/test_ops_phase4.py -q
```

**Automated API loop (same DB as uvicorn in `backend/`):**

```powershell
py -3.11 scripts/owner_runbook_verify.py
```

Expect `RUNBOOK API PASS` then do §2–4 once in the browser for human sign-off.

---

## Dev-only shortcuts

| Tool | Use |
|------|-----|
| `VITE_ENABLE_RIDE_SIMULATION=true` (driver-app) | Creates backend `requested` ride without rider app — label as **internal test**, not production demand |
| `rider-stub/` | **Demo only** — do not use for product sign-off |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Rider CORS error | Add `http://127.0.0.1:3023` to `CORS_ORIGINS` in backend `.env` |
| Ops CORS error | Add `http://127.0.0.1:3024` (auto-included in dev for ports 3020–3034) |
| Driver cannot see ride | Driver must be **online** + **approved**; ride must be `requested` |
| Rider 403 on `/rides/` | Token must be **customer** role — use rider app login, not driver token |
| Status stuck | Check backend logs; confirm driver completed all lifecycle steps |

---

## 7. OSRM runtime proof (production route claim — optional)

Only needed to close **PARTIAL_GO → Production GO** routing evidence. Code path is complete; this section proves OSRM is **listening**.

```powershell
cd c:\Users\him\Desktop\halfapp-driver\docker\osrm-portland
docker compose up -d
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
$env:ROUTING_PROVIDER = "osrm_self_hosted"
```

1. Restart backend with env above.
2. Run two-sided loop (§2–4) or driver simulation accept.
3. On accepted ride, confirm API fields: `route_provider=osrm_self_hosted`, `route_source=osrm_v5`, `route_used_fallback=false`, `route_calculated_at` set, `route_provider_confidence` set, `distance_km` ≠ stale `4.0` default.
4. Driver cockpit: no `ride-ai-route-advisory-label` when OSRM succeeded (`routeContext.live`).
5. Stop OSRM; repeat — expect `route_used_fallback=true`, advisory label returns.

Full checklist: `docs/RIDE_AI_DISPATCH_PRODUCTION_PROOF_GATES_01_REPORT.md` §7 · `docs/SELF_HOSTED_ROUTING_PROOF_V0_2_STATUS.md`.

---

## Phase 1 sign-off

Phase 1 is **DONE** when this runbook completes once end-to-end with **rider app + driver app** (simulation-only counts as dev aid, not rider product proof).
