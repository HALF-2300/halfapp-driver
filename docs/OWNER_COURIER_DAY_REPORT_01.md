# Owner Courier Day — Sign-Off Report (Template)

**Task:** P0-G3  
**Document ID:** `OWNER_COURIER_DAY_REPORT_01`  
**STATUS:** **PENDING_OWNER** — AI agents must **not** mark G3 GO.

## Runbook

Follow: `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md`

| Terminal | Service | URL |
|----------|---------|-----|
| 1 | Backend `uvicorn` | http://127.0.0.1:8000/health |
| 2 | `driver-app` | http://127.0.0.1:3022 |
| 3 | `rider-app` | http://127.0.0.1:3023 |
| 4 | `ops-app` (optional) | http://127.0.0.1:3024 |

## Delivery car checklist (owner marks each)

| Step | Done | Notes / screenshot file |
|------|------|-------------------------|
| Requester registers and requests job (pickup → dropoff) | ☐ | |
| Courier goes online (approved driver) | ☐ | |
| Courier accepts OR receives auto-assign | ☐ | Flag: `HALFAPP_AUTO_ASSIGN=1` |
| Arrive pickup → Start → Complete | ☐ | |
| Requester sees **completed** + receipt | ☐ | |
| Courier earnings shows captured payment row | ☐ | |
| Ops lists ride with status + payment | ☐ | |
| No Postman / manual DB edits used | ☐ | |

## Optional routing proof (G2)

| Check | Done |
|-------|------|
| OSRM up; ride shows `route_provider=osrm_self_hosted`, `used_fallback=false` | ☐ |
| OSRM down; ride shows `haversine_fallback` honestly | ☐ |

## Sign-off

| Field | Value |
|-------|-------|
| Date (UTC) | |
| Owner name | |
| Environment | local / staging |
| Database | sqlite / postgresql |
| Verdict | **GO_OWNER_COURIER_DAY** / **NO_GO** (reason) |

## API smoke (optional, before browser)

```powershell
cd backend
py -3.11 scripts/owner_runbook_verify.py
```

Expected: `RUNBOOK API PASS`
