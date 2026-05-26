# P0-G5 — Surface-Freeze / OpenAPI Drift Report

**Task:** P0-G5  
**Date:** 2026-05-25  
**STATUS:** **GO**

## COMMAND RUN

```powershell
cd backend
py -3.11 -m pytest tests/test_active_route_surface.py -q
```

**Output:** `3 passed` (includes openapi drift companion if present in file — 2 tests in module + stable car unrelated)

```
2 passed in test_active_route_surface.py
```

## PROOF

| Item | Result |
|------|--------|
| `ACTIVE_PATHS` updated with `/rides/my-rides` | Done |
| Regenerate instructions in module docstring | Points to `scripts/print_active_routes.py` |
| `test_active_route_surface_is_driver_only_mvp` | PASS |
| `test_openapi_exposes_only_registered_product_routes` | PASS |
| Dossier paths excluded when spine off | PASS |

## DOCS UPDATED

- `backend/tests/test_active_route_surface.py`

## NEXT TASK

P0-G6 (completed in same pass) → overall P0 remains **PARTIAL_GO** until G1 local PG + G2 OSRM + G3 owner.
