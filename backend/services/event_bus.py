"""
In-process pub/sub for SSE.
Single-instance only — when scaling to multiple API workers, swap for Redis pub/sub.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @asynccontextmanager
    async def subscribe(self, topic: str) -> AsyncIterator[asyncio.Queue[str]]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self._subscribers[topic].add(queue)
        try:
            yield queue
        finally:
            self._subscribers[topic].discard(queue)

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        payload = json.dumps(event, default=str)
        dead: list[asyncio.Queue[str]] = []
        for queue in self._subscribers.get(topic, set()):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(queue)
        for queue in dead:
            self._subscribers[topic].discard(queue)

    def publish_sync(self, topic: str, event: dict[str, Any]) -> None:
        """Emit from sync SQLAlchemy routes after commit."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.publish(topic, event), self._loop)
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(topic, event))
        except RuntimeError:
            payload = json.dumps(event, default=str)
            for queue in self._subscribers.get(topic, set()):
                try:
                    queue.put_nowait(payload)
                except Exception:
                    pass


event_bus = EventBus()
