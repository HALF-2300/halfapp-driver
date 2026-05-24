"""SSE ride pool — event bus, auth gate, and SSE framing helpers."""

from __future__ import annotations

import asyncio
import json
import uuid

from database import SessionLocal
import models.user  # noqa: F401
import models.ride  # noqa: F401
import routes.notifications  # noqa: F401

from fastapi.testclient import TestClient
from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from services.event_bus import event_bus
from services.lifecycle import DriverStatus
from services.ride_pool_broadcast import (
    POOL_EVENT_CREATED,
    format_sse_event,
    pool_delta_payload,
)


def _driver_token(db) -> str:
    uid = uuid.uuid4().hex[:10]
    user = create_user(
        db,
        f"sse_driver_{uid}@example.com",
        "SSE Driver",
        "pw12345",
        UserRole.DRIVER,
        f"DL{uid}",
        driver_approval_status="approved",
    )
    user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return create_access_token(sub=user.email, role=user.role.value)


def test_sse_stream_requires_auth():
    with TestClient(app) as client:
        denied = client.get("/drivers/available-rides/stream")
        assert denied.status_code == 401


def test_sse_stream_accepts_access_token_query_param():
    db = SessionLocal()
    try:
        token = _driver_token(db)
    finally:
        db.close()

    with TestClient(app) as client:
        # Non-streaming probe: invalid token should 401 before hanging on body read.
        bad = client.get("/drivers/available-rides/stream?access_token=not-a-jwt")
        assert bad.status_code == 401

        # Valid token opens the stream (content-type only — body read is E2E / manual).
        with client.stream(
            "GET",
            f"/drivers/available-rides/stream?access_token={token}",
            timeout=3,
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")


def test_format_sse_event_snapshot_and_delta():
    snapshot = format_sse_event("snapshot", [{"id": 1}])
    assert snapshot.startswith("event: snapshot\n")
    assert "data:" in snapshot

    delta = format_sse_event(
        "delta",
        pool_delta_payload(event=POOL_EVENT_CREATED, ride_id=7, ride={"id": 7}, removed=False),
    )
    assert delta.startswith("event: delta\n")
    payload = json.loads(delta.split("data:", 1)[1].strip())
    assert payload["event"] == POOL_EVENT_CREATED


def test_event_bus_publish_subscribe():
    async def _run() -> None:
        async with event_bus.subscribe("ride_pool") as queue:
            await event_bus.publish("ride_pool", {"type": "ping", "ride_id": 1})
            raw = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert json.loads(raw)["type"] == "ping"

    asyncio.run(_run())
