"""GET /drivers/stripe/connect/status — read-only Connect flags (product completion)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.driver_stripe_account import DriverStripeAccount
from models.user import UserRole
from services.auth import create_access_token, create_user


def test_connect_status_without_account(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "1")
    monkeypatch.setenv("PAYOUTS_ENABLED", "1")

    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"conn_{uid}@example.com",
            "Connect",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        token = create_access_token(user=driver)
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(
            "/drivers/stripe/connect/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["has_connect_account"] is False
    assert body["payments_enabled"] is True
    assert body["payouts_enabled_flag"] is True


def test_connect_status_with_account_row(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PAYMENTS_ENABLED", "1")

    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        driver = create_user(
            db,
            f"conn2_{uid}@example.com",
            "Connect2",
            "pw12345",
            UserRole.DRIVER,
            f"DL{uid}",
            driver_approval_status="approved",
        )
        db.add(
            DriverStripeAccount(
                driver_id=driver.id,
                stripe_account_id="acct_status_test",
                charges_enabled=True,
                payouts_enabled=False,
            )
        )
        db.commit()
        token = create_access_token(user=driver)
    finally:
        db.close()

    with TestClient(app) as client:
        response = client.get(
            "/drivers/stripe/connect/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    body = response.json()
    assert body["has_connect_account"] is True
    assert body["stripe_account_id"] == "acct_status_test"
    assert body["charges_enabled"] is True
    assert body["provider_payouts_enabled"] is False
