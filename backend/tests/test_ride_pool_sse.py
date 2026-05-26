"""SSE ride pool — event bus, auth gate, and SSE framing helpers."""

from __future__ import annotations

import asyncio
import json

import models.user  # noqa: F401
import models.ride  # noqa: F401
import routes.notifications  # noqa: F401

from fastapi.testclient import TestClient
from main import app
from services.event_bus import event_bus
from services.ride_pool_broadcast import (
    POOL_EVENT_CREATED,
    emit_pool_delta,
    format_sse_event,
    pool_delta_payload,
)


def test_sse_stream_requires_auth():
    with TestClient(app) as client:
        denied = client.get("/drivers/available-rides/stream")
        assert denied.status_code == 401
        bad = client.get("/drivers/available-rides/stream?access_token=not-a-jwt")
        assert bad.status_code == 401


def test_emit_pool_delta_reaches_sync_subscriber():
    sync_queue = event_bus.subscribe_sync("ride_pool")
    try:
        emit_pool_delta(
            event=POOL_EVENT_CREATED,
            ride_id=99,
            ride={"id": 99},
            removed=False,
        )
        raw = sync_queue.get(timeout=1.0)
        payload = json.loads(raw)
        assert payload["event"] == POOL_EVENT_CREATED
        assert payload["ride_id"] == 99
    finally:
        event_bus.unsubscribe_sync("ride_pool", sync_queue)


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
