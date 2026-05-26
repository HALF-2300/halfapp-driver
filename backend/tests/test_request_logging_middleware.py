"""
Tests for RequestLoggingMiddleware (DEPLOY_CORS_OBSERVABILITY_01).

Verifies:
- Each response carries an X-Request-ID header (generated or echoed).
- A structured JSON log line is emitted for each request.
- ride_id is extracted from /rides/{id} and /drivers/rides/{id} paths.
- driver_id is extracted from JWT Bearer token payload (without re-validation).
"""
from __future__ import annotations

import base64
import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware import request_logging as request_logging_mod
from middleware.request_logging import RequestLoggingMiddleware


@pytest.fixture
def captured_logs(monkeypatch):
    """Intercept request_logging.logger.info calls directly.

    pytest's logging plugin interferes with custom handlers on named loggers,
    so we patch the logger.info call site to capture structured records.
    """
    records: list[dict] = []
    real_logger = request_logging_mod.logger

    class _Spy:
        def info(self, msg, *args, **kwargs):
            try:
                records.append(json.loads(msg))
            except Exception:
                pass

        def __getattr__(self, name):
            return getattr(real_logger, name)

    monkeypatch.setattr(request_logging_mod, "logger", _Spy())
    return records


@pytest.fixture
def app_with_middleware() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/drivers/rides/{ride_id}/anything")
    def driver_ride(ride_id: int):
        return {"ride_id": ride_id}

    @app.get("/rides/{ride_id}/cancel")
    def rider_ride(ride_id: int):
        return {"ride_id": ride_id}

    return app


def _make_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.sig"


def test_response_carries_request_id(app_with_middleware, captured_logs):
    client = TestClient(app_with_middleware)
    res = client.get("/health")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    uuid.UUID(res.headers["x-request-id"])  # must parse


def test_request_id_is_echoed_when_provided(app_with_middleware, captured_logs):
    client = TestClient(app_with_middleware)
    incoming = "client-fixed-id-123"
    res = client.get("/health", headers={"X-Request-ID": incoming})
    assert res.headers["x-request-id"] == incoming


def test_log_line_has_required_fields(app_with_middleware, captured_logs):
    client = TestClient(app_with_middleware)
    res = client.get("/health")
    assert res.status_code == 200

    assert captured_logs, "expected at least one structured log record"
    last = captured_logs[-1]
    assert last["method"] == "GET"
    assert last["path"] == "/health"
    assert last["status"] == 200
    assert "request_id" in last
    assert "duration_ms" in last
    assert "driver_id" not in last
    assert "ride_id" not in last


def test_ride_id_from_driver_path(app_with_middleware, captured_logs):
    client = TestClient(app_with_middleware)
    res = client.get("/drivers/rides/42/anything")
    assert res.status_code == 200
    assert captured_logs[-1]["ride_id"] == 42


def test_ride_id_from_rider_path(app_with_middleware, captured_logs):
    client = TestClient(app_with_middleware)
    res = client.get("/rides/77/cancel")
    assert res.status_code == 200
    assert captured_logs[-1]["ride_id"] == 77


def test_driver_id_from_jwt_bearer(app_with_middleware, captured_logs):
    client = TestClient(app_with_middleware)
    token = _make_jwt({"sub": "drv@example.com", "user_id": 99, "role": "driver"})
    res = client.get("/health", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert captured_logs[-1]["driver_id"] == 99


def test_invalid_bearer_does_not_crash(app_with_middleware, captured_logs):
    client = TestClient(app_with_middleware)
    res = client.get("/health", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert res.status_code == 200
    assert "driver_id" not in captured_logs[-1]
