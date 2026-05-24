"""HALFAPP_AI_ASSISTANT_PERMISSION_GATE_01 — backend-only engineering assistant."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.engineering_assistant import (
    ProviderNotConfiguredError,
    chat_with_provider,
    is_assistant_enabled,
    is_provider_configured,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def driver_headers():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        user = create_user(
            db,
            f"eng_assist_{uid}@example.com",
            "Engineer Driver",
            "pw12345",
            UserRole.DRIVER,
            f"LIC{uid}",
            driver_approval_status="approved",
        )
        db.commit()
        token = create_access_token(user=user)
    finally:
        db.close()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset_engineering_assistant_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ENGINEERING_ASSISTANT_ENABLED", raising=False)


def test_status_without_provider_key(client, driver_headers):
    response = client.get("/engineering-assistant/status", headers=driver_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["configured"] is False
    assert body["provider"] is None
    assert "api_key" not in body
    assert "x-api-key" not in response.text.lower()


def test_chat_without_provider_key_returns_503(client, driver_headers):
    response = client.post(
        "/engineering-assistant/chat",
        headers=driver_headers,
        json={
            "prompt": "Summarize active product boundary.",
            "messages": [],
        },
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_chat_with_key_but_disabled_returns_503(client, driver_headers, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-secret-not-used")
    assert is_assistant_enabled() is False
    assert is_provider_configured() is False

    response = client.post(
        "/engineering-assistant/chat",
        headers=driver_headers,
        json={
            "prompt": "What is the active spine?",
            "messages": [],
        },
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_chat_proxies_to_provider_with_env_key(client, driver_headers, monkeypatch):
    import routes.engineering_assistant as route_mod

    monkeypatch.setattr(route_mod, "is_provider_configured", lambda: True)
    monkeypatch.setattr(route_mod, "provider_name", lambda: "anthropic")
    monkeypatch.setattr(route_mod, "chat_with_provider", lambda **kwargs: "Backend-only reply")

    response = client.post(
        "/engineering-assistant/chat",
        headers=driver_headers,
        json={
            "prompt": "What is the active spine?",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"] == "Backend-only reply"
    assert body["provider"] == "anthropic"
    assert "test-secret" not in response.text


def test_service_never_exposes_key_in_return_value(monkeypatch):
    monkeypatch.setenv("ENGINEERING_ASSISTANT_ENABLED", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "super-secret")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"content": [{"type": "text", "text": "ok"}]}

    class FakeClient:
        def post(self, url, json=None, headers=None):
            assert headers["x-api-key"] == "super-secret"
            assert "api.anthropic.com" in url
            return FakeResponse()

        def close(self):
            pass

    reply = chat_with_provider(
        history=[],
        prompt="ping",
        client=FakeClient(),
    )
    assert reply == "ok"
    assert "super-secret" not in reply


def test_service_raises_when_unconfigured():
    with pytest.raises(ProviderNotConfiguredError):
        chat_with_provider(history=[], prompt="ping", client=MagicMock())


def test_is_provider_configured_false_by_default():
    assert is_assistant_enabled() is False
    assert is_provider_configured() is False
