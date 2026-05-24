"""Production guards: SECRET_KEY, CORS, ride simulation gating."""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from production_guards import (
    PRODUCTION_UNSAFE_SECRET_ERROR,
    SIMULATION_DISABLED_DETAIL,
    assert_safe_secret_key_for_runtime,
    cors_origins_contain_wildcard,
    get_cors_origins_for_environment,
    is_ride_simulation_enabled,
    resolve_runtime_environment,
    secret_key_is_unsafe,
    validate_cors_for_environment,
    validate_secret_for_environment,
)

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_secret_key_is_unsafe_detects_known_defaults():
    assert secret_key_is_unsafe("")
    assert secret_key_is_unsafe("change_me")
    assert secret_key_is_unsafe("change_me_in_production")
    assert secret_key_is_unsafe("dev")
    assert secret_key_is_unsafe("insecure-dev-key-change-me-immediately-in-prod")


def test_validate_secret_allows_development_placeholder():
    validate_secret_for_environment("development", "change_me")


def test_validate_secret_allows_test_environment_explicit_secret():
    validate_secret_for_environment("test", "pytest-halfapp-test-secret-32chars-minimum")


def test_validate_secret_rejects_unsafe_test_secret():
    with pytest.raises(RuntimeError, match="Unsafe SECRET_KEY in test"):
        validate_secret_for_environment("test", "change_me")


def test_validate_secret_rejects_production_change_me():
    with pytest.raises(RuntimeError, match=PRODUCTION_UNSAFE_SECRET_ERROR):
        validate_secret_for_environment("production", "change_me")


def test_validate_secret_rejects_production_empty_string():
    with pytest.raises(RuntimeError, match=PRODUCTION_UNSAFE_SECRET_ERROR):
        validate_secret_for_environment("production", "")


def test_validate_secret_rejects_production_missing_as_unsafe_default():
    with pytest.raises(RuntimeError, match=PRODUCTION_UNSAFE_SECRET_ERROR):
        validate_secret_for_environment("production", None)


def test_validate_secret_accepts_strong_production_secret():
    strong = secrets.token_urlsafe(48)
    validate_secret_for_environment("production", strong)


def test_validate_secret_rejects_short_production_secret():
    with pytest.raises(RuntimeError, match=PRODUCTION_UNSAFE_SECRET_ERROR):
        validate_secret_for_environment("production", "a" * 31)


def test_production_error_does_not_leak_secret_value():
    secret = "supersecret-leak-test-value-not-in-error-message-xyz"
    with pytest.raises(RuntimeError) as exc_info:
        validate_secret_for_environment("production", secret[:20])
    assert PRODUCTION_UNSAFE_SECRET_ERROR in str(exc_info.value)
    assert secret not in str(exc_info.value)


def test_resolve_runtime_environment_halapp_env_authoritative(monkeypatch):
    monkeypatch.setenv("HALFAPP_ENV", "test")
    monkeypatch.setenv("ENV", "production")
    assert resolve_runtime_environment() == "test"


def test_resolve_runtime_environment_env_production_without_halapp(monkeypatch):
    monkeypatch.delenv("HALFAPP_ENV", raising=False)
    monkeypatch.setenv("ENV", "production")
    assert resolve_runtime_environment() == "production"


def test_assert_safe_secret_key_for_runtime_allows_dev_placeholder(monkeypatch):
    monkeypatch.setenv("HALFAPP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "change_me")
    assert_safe_secret_key_for_runtime()


def test_assert_safe_secret_key_for_runtime_rejects_production_change_me(monkeypatch):
    monkeypatch.setenv("HALFAPP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change_me")
    with pytest.raises(RuntimeError, match=PRODUCTION_UNSAFE_SECRET_ERROR):
        assert_safe_secret_key_for_runtime()


def test_validate_cors_rejects_wildcard():
    with pytest.raises(RuntimeError, match="Wildcard CORS"):
        validate_cors_for_environment("production", "https://app.example.com,*")


def test_validate_cors_requires_origins_in_production():
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must list"):
        validate_cors_for_environment("production", "")


def test_get_cors_origins_production_strict():
    origins = get_cors_origins_for_environment(
        "production",
        "https://driver.halfapp.example,https://app.halfapp.example",
    )
    assert origins == [
        "https://driver.halfapp.example",
        "https://app.halfapp.example",
    ]
    assert "http://localhost:5173" not in origins


def test_get_cors_origins_development_unions_localhost():
    origins = get_cors_origins_for_environment("development", "http://localhost:3024")
    assert "http://localhost:3024" in origins
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:3024" in origins


def test_cors_wildcard_detection():
    assert cors_origins_contain_wildcard(["*"])
    assert cors_origins_contain_wildcard(["https://x.com/*"])
    assert not cors_origins_contain_wildcard(["https://x.com"])


def test_is_ride_simulation_enabled_requires_explicit_flag(monkeypatch):
    monkeypatch.delenv("HALFAPP_ENABLE_RIDE_SIMULATION", raising=False)
    assert is_ride_simulation_enabled("production") is False
    monkeypatch.setenv("HALFAPP_ENABLE_RIDE_SIMULATION", "1")
    assert is_ride_simulation_enabled("production") is True
    monkeypatch.setenv("HALFAPP_ENABLE_RIDE_SIMULATION", "true")
    assert is_ride_simulation_enabled("test") is True


def test_simulate_ride_rejected_when_simulation_disabled(monkeypatch):
    monkeypatch.setattr("config.is_ride_simulation_enabled", lambda: False)
    monkeypatch.setattr("routes.drivers.is_ride_simulation_enabled", lambda: False)

    db = SessionLocal()
    try:
        from tests.test_ride_lifecycle import _driver_token as lifecycle_driver_token

        token = lifecycle_driver_token(db)
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        response = client.post(
            "/drivers/simulate-ride",
            headers=headers,
            json={
                "customer_name": "Blocked Simulation",
                "pickup_location": "P",
                "destination": "D",
                "distance_km": 2.0,
                "duration_minutes": 5,
            },
        )
    assert response.status_code == 403
    assert response.json()["detail"] == SIMULATION_DISABLED_DETAIL


def test_simulate_ride_allowed_when_flag_enabled():
    """conftest sets HALFAPP_ENABLE_RIDE_SIMULATION=1."""
    assert is_ride_simulation_enabled("test") is True


def _config_import_in_subprocess(env: dict[str, str]) -> subprocess.CompletedProcess:
    base = {
        "PYTHONPATH": str(_BACKEND_DIR),
        "PATH": os.environ.get("PATH", ""),
    }
    base.update(env)
    return subprocess.run(
        [sys.executable, "-c", "import config"],
        cwd=str(_BACKEND_DIR),
        env=base,
        capture_output=True,
        text=True,
    )


def _main_import_in_subprocess(env: dict[str, str]) -> subprocess.CompletedProcess:
    base = {
        "PYTHONPATH": str(_BACKEND_DIR),
        "PATH": os.environ.get("PATH", ""),
    }
    base.update(env)
    return subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=str(_BACKEND_DIR),
        env=base,
        capture_output=True,
        text=True,
    )


def test_config_import_fails_production_with_insecure_secret():
    result = _config_import_in_subprocess(
        {
            "HALFAPP_ENV": "production",
            "SECRET_KEY": "change_me",
            "CORS_ORIGINS": "https://driver.example.com",
        }
    )
    assert result.returncode != 0
    assert PRODUCTION_UNSAFE_SECRET_ERROR in result.stderr
    assert "change_me" not in result.stdout


def test_config_import_fails_production_with_missing_secret_uses_unsafe_default():
    result = _config_import_in_subprocess(
        {
            "HALFAPP_ENV": "production",
            "CORS_ORIGINS": "https://driver.example.com",
        }
    )
    assert result.returncode != 0
    assert PRODUCTION_UNSAFE_SECRET_ERROR in result.stderr


def test_config_import_fails_production_via_env_without_halapp():
    result = _config_import_in_subprocess(
        {
            "ENV": "production",
            "SECRET_KEY": "change_me",
            "CORS_ORIGINS": "https://driver.example.com",
        }
    )
    assert result.returncode != 0
    assert PRODUCTION_UNSAFE_SECRET_ERROR in result.stderr


def test_config_import_succeeds_production_with_strong_secret():
    strong = secrets.token_urlsafe(48)
    result = _config_import_in_subprocess(
        {
            "HALFAPP_ENV": "production",
            "SECRET_KEY": strong,
            "CORS_ORIGINS": "https://driver.example.com",
        }
    )
    assert result.returncode == 0, result.stderr


def test_main_import_fails_production_with_insecure_secret():
    result = _main_import_in_subprocess(
        {
            "HALFAPP_ENV": "production",
            "SECRET_KEY": "change_me",
            "CORS_ORIGINS": "https://driver.example.com",
        }
    )
    assert result.returncode != 0
    assert PRODUCTION_UNSAFE_SECRET_ERROR in result.stderr
