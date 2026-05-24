import os

from typing import List



from production_guards import (

    DEFAULT_DEV_SECRET,

    assert_safe_secret_key_for_runtime,

    get_cors_origins_for_environment,

    is_ride_simulation_enabled as _is_ride_simulation_enabled,

    normalize_halfapp_env,

    validate_cors_for_environment,

)



# Environment settings

HALFAPP_ENV = normalize_halfapp_env(os.getenv("HALFAPP_ENV"))

SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_DEV_SECRET)



# CORS settings

CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "")



# Map / routing provider flags (v0.1 — free stack default, paid providers off)

MAP_DISPLAY_PROVIDER = os.getenv("MAP_DISPLAY_PROVIDER", "current_osm_leaflet")

ROUTING_PROVIDER = os.getenv("ROUTING_PROVIDER", "osrm_self_hosted")

OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "http://127.0.0.1:5000")

ROUTING_FALLBACK_ENABLED = os.getenv("ROUTING_FALLBACK_ENABLED", "true").lower() in {

    "1",

    "true",

    "yes",

}

TRAFFIC_PROVIDER = os.getenv("TRAFFIC_PROVIDER", "none")

TRAFFIC_SIGNALS_ENABLED = os.getenv("TRAFFIC_SIGNALS_ENABLED", "false").lower() == "true"

ODOT_TRIPCHECK_SUBSCRIPTION_KEY = os.getenv("ODOT_TRIPCHECK_SUBSCRIPTION_KEY", "").strip()

WSDOT_ACCESS_CODE = os.getenv("WSDOT_ACCESS_CODE", "").strip()

GOOGLE_MAPS_FALLBACK_ENABLED = os.getenv("GOOGLE_MAPS_FALLBACK_ENABLED", "false").lower() == "true"

MAPBOX_TRAFFIC_ENABLED = os.getenv("MAPBOX_TRAFFIC_ENABLED", "false").lower() == "true"



# Boot-time production guards (fail loudly; never auto-generate secrets)

assert_safe_secret_key_for_runtime()

validate_cors_for_environment(HALFAPP_ENV, CORS_ORIGINS_STR)





def get_cors_origins() -> List[str]:

    """

    Returns CORS origins based on the environment.

    Production: only explicit CORS_ORIGINS (no localhost union).

    Development/test: unions configured origins with standard local dev ports.

    """

    return get_cors_origins_for_environment(HALFAPP_ENV, CORS_ORIGINS_STR)





def is_ride_simulation_enabled() -> bool:

    """Explicit opt-in via HALFAPP_ENABLE_RIDE_SIMULATION=1 (all environments)."""

    return _is_ride_simulation_enabled(HALFAPP_ENV)


