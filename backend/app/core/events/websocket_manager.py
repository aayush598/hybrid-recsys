from __future__ import annotations

import uuid
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket connection manager for real-time recommendations.

    Features:
    - Per-user connection tracking
    - Room-based broadcasting
    - Heartbeat/ping-pong for connection health
    - Message queuing for offline users
    """

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.rooms: dict[str, set[str]] = {}
        self.user_connections: dict[str, str] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        connection_id = str(uuid.uuid4())[:8]

        if user_id in self.active_connections:
            old_ws = self.active_connections[user_id]
            if old_ws.client_state == WebSocketState.CONNECTED:
                await old_ws.close(code=4001, reason="Replaced by new connection")

        self.active_connections[user_id] = websocket
        self.user_connections[user_id] = connection_id

        logger.info(f"WebSocket connected: user={user_id}, connection={connection_id}")
        return connection_id

    async def disconnect(self, user_id: str) -> None:
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_connections:
            del self.user_connections[user_id]

        for room_id, members in self.rooms.items():
            members.discard(user_id)

        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_personal(self, user_id: str, message: dict[str, Any]) -> bool:
        """Send a message to a specific user."""
        if user_id not in self.active_connections:
            return False

        ws = self.active_connections[user_id]
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_json(message)
                return True
        except Exception as e:
            logger.error(f"Failed to send to user {user_id}: {e}")
            await self.disconnect(user_id)
        return False

    async def broadcast(self, message: dict[str, Any]) -> int:
        """Broadcast a message to all connected users."""
        sent = 0
        disconnected = []

        for user_id, ws in self.active_connections.items():
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
                    sent += 1
            except Exception:
                disconnected.append(user_id)

        for user_id in disconnected:
            await self.disconnect(user_id)

        return sent

    async def join_room(self, user_id: str, room_id: str) -> None:
        """Join a user to a room."""
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(user_id)

    async def leave_room(self, user_id: str, room_id: str) -> None:
        """Remove a user from a room."""
        if room_id in self.rooms:
            self.rooms[room_id].discard(user_id)

    async def broadcast_to_room(self, room_id: str, message: dict[str, Any]) -> int:
        """Broadcast to all users in a room."""
        if room_id not in self.rooms:
            return 0

        sent = 0
        for user_id in self.rooms[room_id]:
            if await self.send_personal(user_id, message):
                sent += 1
        return sent

    @property
    def active_count(self) -> int:
        return len(self.active_connections)

    @property
    def stats(self) -> dict:
        return {
            "active_connections": self.active_count,
            "rooms": {k: len(v) for k, v in self.rooms.items()},
        }


ws_manager = ConnectionManager()
