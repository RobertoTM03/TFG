from typing import Dict, List

from fastapi import WebSocket
from loguru import logger

class WebSocketManager:
    """Manages WebSocket connections grouped by user ID."""

    def __init__(self) -> None:
        # user_id (str) -> list of active WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, ws: WebSocket, user_id: str) -> None:
        await ws.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(ws)
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
        logger.info(
            f"WebSocket disconnected for user {user_id}. "
            f"Total connections: {self._total()}"
        )

    async def notify_user(self, user_id: str, message: dict) -> None:
        """Send a JSON message to all connections of a given user."""
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                # Connection already closed; clean up silently
                self.disconnect(ws, user_id)

    def _total(self) -> int:
        return sum(len(v) for v in self._connections.values())
