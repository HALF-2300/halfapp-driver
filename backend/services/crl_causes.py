"""Cause codes and driver-facing explanation labels (probabilistic wording)."""

from __future__ import annotations

from services.crl_labels import CRL_DISCLAIMER

# Primary cause enum values (stored in DB)
UNCERTAIN_PATTERN = "uncertain_pattern"
MORNING_COMMUTE = "morning_commute"
EVENING_COMMUTE = "evening_commute"
TRANSPORT_HUB_ARRIVAL = "transport_hub_arrival"
TRANSPORT_HUB_DEPARTURE = "transport_hub_departure"
DRIVER_SHORTAGE = "driver_shortage"
MATCH_FRICTION = "match_friction"
EVENT_DRIVEN = "event_driven"
PICKUP_SOURCE_ZONE = "pickup_source_zone"
DROPOFF_SINK_ZONE = "dropoff_sink_zone"

CAUSE_DRIVER_TEMPLATES: dict[str, str] = {
    MORNING_COMMUTE: "Higher ride activity likely from work commute patterns",
    EVENING_COMMUTE: "Higher ride activity likely from evening commute patterns",
    TRANSPORT_HUB_ARRIVAL: "Increased dropoffs near a transport hub area",
    TRANSPORT_HUB_DEPARTURE: "Increased pickups near a transport hub area",
    DRIVER_SHORTAGE: "Fewer available drivers nearby",
    MATCH_FRICTION: "Temporary increase in cancellations (possible match friction)",
    EVENT_DRIVEN: "Temporary increase in ride requests (possible local event)",
    PICKUP_SOURCE_ZONE: "More ride pickups than dropoffs in this area",
    DROPOFF_SINK_ZONE: "More ride dropoffs than pickups in this area",
    UNCERTAIN_PATTERN: "Activity pattern is unclear from recent signals",
}


def driver_label_for_cause(primary_cause: str, secondary_causes: list[str] | None = None) -> str:
    primary = CAUSE_DRIVER_TEMPLATES.get(primary_cause, CAUSE_DRIVER_TEMPLATES[UNCERTAIN_PATTERN])
    parts = [primary]
    if secondary_causes:
        for sec in secondary_causes[:2]:
            sec_label = CAUSE_DRIVER_TEMPLATES.get(sec)
            if sec_label and sec_label not in parts:
                parts.append(sec_label)
    body = " · ".join(parts)
    return f"{body}. {CRL_DISCLAIMER}"
