"""H3 cell helpers (neighborhood resolution; privacy-safe aggregation)."""

from __future__ import annotations

import os

DEFAULT_H3_RES = int(os.getenv("SIL_H3_RES", "7"))


def _grid_fallback_cell(lat: float, lng: float, res: int) -> str:
    step = 0.02 * (2 ** max(0, 9 - res))
    lat_k = round(lat / step) * step
    lng_k = round(lng / step) * step
    return f"grid_{res}_{lat_k:.5f}_{lng_k:.5f}"


def lat_lng_to_cell(lat: float, lng: float, res: int | None = None) -> str:
    res = DEFAULT_H3_RES if res is None else res
    try:
        import h3

        return h3.latlng_to_cell(lat, lng, res)
    except Exception:
        return _grid_fallback_cell(lat, lng, res)


def cell_to_lat_lng(cell: str) -> tuple[float, float]:
    if cell.startswith("grid_"):
        parts = cell.split("_")
        return float(parts[2]), float(parts[3])
    try:
        import h3

        lat, lng = h3.cell_to_latlng(cell)
        return float(lat), float(lng)
    except Exception:
        return 0.0, 0.0
