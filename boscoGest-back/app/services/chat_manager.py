"""
Singleton WebSocket connection manager for real-time chat message dispatch.

Mirrors the pattern of NotificationManager:
  sync ChatService → enqueue() → asyncio.Queue → _dispatch_loop() → WebSocket
"""

import asyncio
import logging
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ChatManager:
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
        logger.info("ChatManager started")

    # ── WebSocket connection management ──────────────────────────────

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self._connections[user_id].append(websocket)
        logger.info(
            "Chat WS connected: user_id=%s (total=%s)",
            user_id,
            len(self._connections[user_id]),
        )

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self._connections:
            try:
                self._connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("Chat WS disconnected: user_id=%s", user_id)

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
            for ws in connections[:]:
                try:
                    await ws.send_json(payload)
                except Exception:
                    self.disconnect(user_id, ws)


# Global singleton
chat_manager = ChatManager()
