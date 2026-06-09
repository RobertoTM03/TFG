from typing import Dict, List, Set

from fastapi import WebSocket
from loguru import logger


class WebSocketManager:
    """Manages WebSocket connections grouped by user ID, with task subscriptions"""

    def __init__(self, max_connections_per_user: int = 5) -> None:
        self._max_connections_per_user = max_connections_per_user
        # user_id -> list of active WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}
        # id(ws) -> set of task_ids the connection is subscribed to
        self._subscriptions: Dict[int, Set[str]] = {}


    async def connect(self, ws: WebSocket, user_id: str) -> None:
        if len(self._connections.get(user_id, [])) >= self._max_connections_per_user:
            raise ConnectionError("Too many connections")
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(ws)
        self._subscriptions[id(ws)] = set()
        logger.info(
            f"WebSocket connected for user {user_id}. "
            f"Total connections: {self._total()}"
        )

    def disconnect(self, ws: WebSocket, user_id: str) -> None:
        if user_id in self._connections:
            self._connections[user_id] = [
                c for c in self._connections[user_id] if c is not ws
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]
        self._subscriptions.pop(id(ws), None)
        logger.info(
            f"WebSocket disconnected for user {user_id}. "
            f"Total connections: {self._total()}"
        )

    def subscribe(self, ws: WebSocket, task_id: str) -> None:
        """Register interest in events for a specific task."""
        if id(ws) in self._subscriptions:
            self._subscriptions[id(ws)].add(task_id)

    def unsubscribe(self, ws: WebSocket, task_id: str) -> None:
        """Remove interest in events for a specific task."""
        if id(ws) in self._subscriptions:
            self._subscriptions[id(ws)].discard(task_id)

    async def notify_task(self, task_id: str, user_id: str, message: dict) -> None:
        """Send a message to connections subscribed to task_id.

        A connection with no subscriptions receives all messages.
        """
        for ws in list(self._connections.get(user_id, [])):
            subs = self._subscriptions.get(id(ws), set())
            if subs and task_id not in subs:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws, user_id)

    async def notify_user(self, user_id: str, message: dict) -> None:
        """Broadcast a message to ALL connections of a user."""
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws, user_id)

    def _total(self) -> int:
        return sum(len(v) for v in self._connections.values())
