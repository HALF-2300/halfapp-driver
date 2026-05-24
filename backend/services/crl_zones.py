"""Zone catalog helpers and default Portland v0.1 seeds."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from models.zone_catalog import ZoneCatalog
from services.sil_h3 import DEFAULT_H3_RES, lat_lng_to_cell


def _cells_around(lat: float, lng: float, res: int = DEFAULT_H3_RES) -> list[str]:
    center = lat_lng_to_cell(lat, lng, res)
    cells = {center}
    try:
        import h3

        for n in h3.grid_disk(center, 1):
            cells.add(n)
    except Exception:
        pass
    return sorted(cells)


def ensure_default_zones(db: Session) -> None:
    if db.query(ZoneCatalog).count() > 0:
        return
    # Portland-area anchors (v0.1 demo seeds; ops can extend via admin API)
    seeds = [
        ("pdx_airport", "Portland International Airport", "airport", 45.5898, -122.5951, 2500.0),
        ("union_station", "Portland Union Station", "transport", 45.5289, -122.6765, 800.0),
        ("downtown_core", "Downtown Portland", "office", 45.5152, -122.6784, 1200.0),
        ("nightlife_pearl", "Pearl / NW nightlife", "nightlife", 45.5246, -122.6819, 900.0),
    ]
    for zone_id, name, ztype, lat, lng, radius_m in seeds:
        db.add(
            ZoneCatalog(
                zone_id=zone_id,
                name=name,
                zone_type=ztype,
                h3_list_json=json.dumps(_cells_around(lat, lng)),
                center_lat=lat,
                center_lng=lng,
                radius_m=radius_m,
                priority_weight=1.0,
            )
        )
    db.commit()


def zones_for_cell(db: Session, h3_cell: str) -> list[ZoneCatalog]:
    zones = db.query(ZoneCatalog).all()
    matched: list[ZoneCatalog] = []
    for zone in zones:
        try:
            cells = set(json.loads(zone.h3_list_json or "[]"))
        except json.JSONDecodeError:
            cells = set()
        if h3_cell in cells:
            matched.append(zone)
    return matched
