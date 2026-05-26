"""
In-process pub/sub for SSE.
Single-instance only — when scaling to multiple API workers, swap for Redis pub/sub.
"""

from __future__ import annotations

import asyncio
import json
import queue as thread_queue
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self._sync_subscribers: dict[str, set[thread_queue.Queue[str]]] = defaultdict(set)
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

    def subscribe_sync(self, topic: str) -> thread_queue.Queue[str]:
        queue: thread_queue.Queue[str] = thread_queue.Queue(maxsize=100)
        self._sync_subscribers[topic].add(queue)
        return queue

    def unsubscribe_sync(self, topic: str, queue: thread_queue.Queue[str]) -> None:
        self._sync_subscribers[topic].discard(queue)

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        payload = json.dumps(event, default=str)
        dead_async: list[asyncio.Queue[str]] = []
        for queue in self._subscribers.get(topic, set()):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead_async.append(queue)
        for queue in dead_async:
            self._subscribers[topic].discard(queue)

    def publish_sync(self, topic: str, event: dict[str, Any]) -> None:
        """Emit from sync SQLAlchemy routes after commit."""
        payload = json.dumps(event, default=str)
        dead_sync: list[thread_queue.Queue[str]] = []
        for queue in self._sync_subscribers.get(topic, set()):
            try:
                queue.put_nowait(payload)
            except thread_queue.Full:
                dead_sync.append(queue)
        for queue in dead_sync:
            self._sync_subscribers[topic].discard(queue)

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.publish(topic, event), self._loop)
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(topic, event))
        except RuntimeError:
            dead_async: list[asyncio.Queue[str]] = []
            for queue in self._subscribers.get(topic, set()):
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    dead_async.append(queue)
            for queue in dead_async:
                self._subscribers[topic].discard(queue)


event_bus = EventBus()
