"""
Singleton WebSocket connection manager for real-time notification dispatch.

Bridges sync services (thread pool) → async WebSocket delivery via an
asyncio.Queue and loop.call_soon_threadsafe().
"""

import asyncio
import logging
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self):
        self._connections: Dict[int, List[WebSocket]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue | None = None

    # ── Lifecycle ────────────────────────────────────────────────────

    async def start(self):
        """Called once during app startup to capture the event loop."""
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        asyncio.create_task(self._dispatch_loop())
        logger.info("NotificationManager started")

    # ── WebSocket connection management ──────────────────────────────

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self._connections[user_id].append(websocket)
        logger.info("WS connected: user_id=%s (total=%s)", user_id, len(self._connections[user_id]))

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self._connections:
            try:
                self._connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("WS disconnected: user_id=%s", user_id)

    def is_online(self, user_id: int) -> bool:
        return user_id in self._connections

    # ── Dispatch (thread-safe bridge sync → async) ───────────────────

    def enqueue(self, user_id: int, payload: dict):
        """Thread-safe: can be called from sync services running in the thread pool."""
        if self._loop and self._queue:
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, (user_id, payload)
            )

    async def _dispatch_loop(self):
        """Background task that drains the queue and pushes to WebSockets."""
        while True:
            user_id, payload = await self._queue.get()
            connections = self._connections.get(user_id, [])
            for ws in connections[:]:  # iterate over copy
                try:
                    await ws.send_json(payload)
                except Exception:
                    self.disconnect(user_id, ws)


# Global singleton — imported by services and the WebSocket router
notification_manager = NotificationManager()
