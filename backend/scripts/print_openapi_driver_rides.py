"""
Print OpenAPI paths and schemas for driver ride lifecycle (proof for Stage 3).

Usage (from repository root or backend/):

  py -3.11 scripts/print_openapi_driver_rides.py
  cd backend && py -3.11 scripts/print_openapi_driver_rides.py
"""
from __future__ import annotations

import json
import os
import sys

# Ensure backend package root is on path when run as script
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

os.chdir(_BACKEND_ROOT)

from main import app  # noqa: E402


_DRIVER_PREFIXES = (
    "/drivers/available-rides",
    "/drivers/my-rides",
    "/drivers/accept-ride",
    "/drivers/decline-ride",
    "/drivers/arrive-pickup",
    "/drivers/start-ride",
    "/drivers/complete-ride",
    "/drivers/earnings",
)

_RIDER_PREFIXES = (
    "/rides/",
)


def _is_relevant_schema(name: str) -> bool:
    return (
        "Ride" in name
        or "Decline" in name
        or "Earnings" in name
        or "Rider" in name
    )


def main() -> None:
    spec = app.openapi()
    paths = spec.get("paths", {})

    print("=== Driver ride lifecycle paths (OpenAPI) ===")
    for p in sorted(paths):
        if any(p.startswith(pref) for pref in _DRIVER_PREFIXES):
            methods = list(paths[p].keys())
            print(f"  {p}  {methods}")

    print("\n=== Rider-side ride paths (OpenAPI) ===")
    for p in sorted(paths):
        if any(p.startswith(pref) for pref in _RIDER_PREFIXES):
            methods = list(paths[p].keys())
            print(f"  {p}  {methods}")

    print("\n=== Schemas (ride/earnings/rider) ===")
    components = spec.get("components", {}).get("schemas", {})
    for name in sorted(components):
        if _is_relevant_schema(name):
            print(f"  - {name}")

    print("\n=== RideDriverView properties ===")
    rdv = components.get("RideDriverView", {})
    props = (rdv.get("properties") or {}).keys()
    print("  " + ", ".join(sorted(props)))

    print("\n=== DriverEarningsResponse properties ===")
    der = components.get("DriverEarningsResponse", {})
    der_props = (der.get("properties") or {}).keys()
    print("  " + ", ".join(sorted(der_props)))

    if os.environ.get("WRITE_OPENAPI_SNIPPET") == "1":
        out = os.path.join(_BACKEND_ROOT, "openapi_driver_snippet.json")
        snippet = {
            "paths": {
                k: v
                for k, v in paths.items()
                if k.startswith("/drivers/") or k.startswith("/rides/")
            },
            "schemas": {k: v for k, v in components.items() if _is_relevant_schema(k)},
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(snippet, f, indent=2)
        print(f"\nWrote {out} (WRITE_OPENAPI_SNIPPET=1)")


if __name__ == "__main__":
    main()
