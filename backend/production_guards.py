"""Production security guards — import-safe validation (no FastAPI dependency)."""
from __future__ import annotations

import os
from typing import List

DEFAULT_DEV_SECRET = "insecure-dev-key-change-me-immediately-in-prod"

# Known unsafe literals (lowercase match) and substrings checked separately.
UNSAFE_SECRET_LITERALS = frozenset(
    {
        "",
        "change_me",
        "change_me_in_production",
        "dev",
        "development",
        "test",
        "secret",
        "insecure-dev-key-change-me-immediately-in-prod",
    }
)

UNSAFE_SECRET_SUBSTRINGS = ("change_me", "changeme", "replace_me", "your_secret")


PRODUCTION_UNSAFE_SECRET_ERROR = "Unsafe SECRET_KEY for production"


def normalize_halfapp_env(raw: str | None) -> str:
    value = (raw or "development").strip().lower()
    if value in ("production", "prod"):
        return "production"
    if value in ("test", "testing"):
        return "test"
    return "development"


def resolve_runtime_environment() -> str:
    """
    Resolve the effective runtime environment for boot guards.

    HALFAPP_ENV is authoritative when set (existing HalfApp convention).
    Otherwise ENV, APP_ENV, and FASTAPI_ENV are checked conservatively.
    """
    halfapp_raw = os.getenv("HALFAPP_ENV")
    if halfapp_raw is not None and halfapp_raw.strip():
        return normalize_halfapp_env(halfapp_raw)

    for key in ("ENV", "APP_ENV", "FASTAPI_ENV"):
        raw = os.getenv(key)
        if raw is not None and raw.strip():
            if normalize_halfapp_env(raw) == "production":
                return "production"

    for key in ("ENV", "APP_ENV", "FASTAPI_ENV"):
        raw = os.getenv(key)
        if raw is not None and raw.strip():
            normalized = normalize_halfapp_env(raw)
            if normalized == "test":
                return "test"

    return "development"


def secret_key_is_unsafe(secret_key: str | None) -> bool:
    if secret_key is None:
        return True
    key = secret_key.strip()
    if not key:
        return True
    lower = key.lower()
    if lower in UNSAFE_SECRET_LITERALS:
        return True
    if any(fragment in lower for fragment in UNSAFE_SECRET_SUBSTRINGS):
        return True
    return False


def validate_secret_for_environment(env: str, secret_key: str) -> None:
    """Raise RuntimeError when secret is not allowed for the given environment."""
    if env == "production":
        if secret_key_is_unsafe(secret_key) or len((secret_key or "").strip()) < 32:
            raise RuntimeError(PRODUCTION_UNSAFE_SECRET_ERROR)
        return

    if env == "test":
        if secret_key_is_unsafe(secret_key):
            raise RuntimeError(
                "FATAL: Unsafe SECRET_KEY in test environment. "
                "Set SECRET_KEY to a non-default test value (≥16 characters) in pytest/CI, "
                "or use a dedicated pytest secret (not change_me/dev/empty)."
            )
        if len(secret_key.strip()) < 16:
            raise RuntimeError(
                "FATAL: SECRET_KEY in test environment must be at least 16 characters."
            )
        return

    # development: allow repository default for local work; still reject empty.
    if not secret_key or not secret_key.strip():
        raise RuntimeError(
            "FATAL: SECRET_KEY is empty. Set SECRET_KEY in the environment or .env file."
        )


def parse_cors_origin_list(cors_origins_str: str) -> List[str]:
    return [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]


def cors_origins_contain_wildcard(origins: List[str]) -> bool:
    for origin in origins:
        if origin == "*" or origin.endswith("/*"):
            return True
    return False


def validate_cors_for_environment(env: str, cors_origins_str: str) -> None:
    """Raise RuntimeError on unsafe CORS configuration at boot."""
    origins = parse_cors_origin_list(cors_origins_str)
    if cors_origins_contain_wildcard(origins):
        raise RuntimeError(
            "FATAL: Wildcard CORS origins are not allowed. "
            "Set explicit origins in CORS_ORIGINS."
        )
    if env == "production" and not origins:
        raise RuntimeError(
            "FATAL: CORS_ORIGINS must list at least one explicit origin in production. "
            "Localhost defaults are not added automatically."
        )


def get_cors_origins_for_environment(env: str, cors_origins_str: str) -> List[str]:
    """Resolve allowed CORS origins for the active environment."""
    validate_cors_for_environment(env, cors_origins_str)
    origins = parse_cors_origin_list(cors_origins_str)

    if env != "production":
        dev_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]
        for port in range(3020, 3035):
            dev_origins.append(f"http://localhost:{port}")
            dev_origins.append(f"http://127.0.0.1:{port}")
        return list(dict.fromkeys(origins + dev_origins))

    return origins


def is_ride_simulation_enabled(env: str | None = None) -> bool:
    """True only when HALFAPP_ENABLE_RIDE_SIMULATION is explicitly enabled."""
    _ = env  # reserved for future per-env defaults; flag is always explicit today.
    flag = os.getenv("HALFAPP_ENABLE_RIDE_SIMULATION", "").strip().lower()
    return flag in ("1", "true", "yes")


SIMULATION_DISABLED_DETAIL = {
    "detail": "Ride simulation is disabled in this environment",
    "truth_status": "simulation_disabled",
    "code": "SIMULATION_DISABLED",
}


def assert_safe_secret_key_for_runtime() -> None:
    """
    Fail fast when production-like runtime uses an unsafe SECRET_KEY.

    Reads SECRET_KEY from the environment only; never logs the secret value.
    """
    env = resolve_runtime_environment()
    secret_key = os.getenv("SECRET_KEY", DEFAULT_DEV_SECRET)
    validate_secret_for_environment(env, secret_key)
