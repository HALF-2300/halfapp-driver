"""Street Intelligence Layer — exact driver-facing honesty copy (v0.1)."""

LABEL_VERSION = "sil_v0.1"

BUSY_LAYER_LABEL = (
    "Estimated busy areas (based on recent in-app requests/offers). Not official demand."
)

SLOW_LAYER_LABEL = (
    "Fleet-estimated slow areas (based on recent driver speeds). Not official live traffic."
)

ROUTE_LABEL_OSRM = "Route: Road-based (OSRM)"
ROUTE_LABEL_FALLBACK = "Route: Approximate (straight-line) — not road-accurate"

ETA_HONESTY_OSRM = "ETA is an estimate; does not include official live traffic."
ETA_HONESTY_FALLBACK = "ETA is approximate (straight-line); may differ from road travel."

PROOF_BADGE_A = "Proof: Road-accurate receipt"
PROOF_BADGE_B = "Proof: Approximate receipt (no road geometry)"
PROOF_BADGE_C = "Proof: Unavailable"

SIL_MAP_DISCLAIMER = (
    "Street Intelligence uses aggregated HalfApp signals only — not official traffic or demand data."
)
