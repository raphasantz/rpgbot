"""WebSocket connection manager for Mesanerd Web."""
from typing import Dict, List
import asyncio
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger("mezzarpg.ws")


MAX_CONNECTIONS_PER_PARTY = 20


class ConnectionManager:
    def __init__(self):
        # party_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, party_id: str, websocket: WebSocket):
        # Enforce a per-party connection cap to limit resource exhaustion
        if len(self.active_connections.get(party_id, [])) >= MAX_CONNECTIONS_PER_PARTY:
            await websocket.close(code=1013)  # Try Again Later
            return False
        await websocket.accept()
        if party_id not in self.active_connections:
            self.active_connections[party_id] = []
        self.active_connections[party_id].append(websocket)
        return True

    def disconnect(self, party_id: str, websocket: WebSocket):
        if party_id in self.active_connections:
            if websocket in self.active_connections[party_id]:
                self.active_connections[party_id].remove(websocket)
            if not self.active_connections[party_id]:
                del self.active_connections[party_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def _safe_send(self, websocket: WebSocket, message: str) -> bool:
        """Send a text message; return True on success, False on failure."""
        try:
            await websocket.send_text(message)
            return True
        except Exception:
            return False

    async def broadcast(self, party_id: str, message: str):
        """Broadcast message to all connections in a party (parallel, safe)."""
        if party_id not in self.active_connections:
            return
        # Snapshot the list so iteration isn't affected by mutations mid-broadcast
        connections = list(self.active_connections[party_id])
        if not connections:
            return
        results = await asyncio.gather(
            *[self._safe_send(conn, message) for conn in connections]
        )
        # Remove any connections that failed to receive
        for conn, ok in zip(connections, results):
            if not ok:
                self.disconnect(party_id, conn)

    async def broadcast_json(self, party_id: str, data: dict):
        """Broadcast JSON data to all connections in a party."""
        try:
            message = json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as exc:
            logger.warning("[ws_manager] Failed to serialize broadcast JSON: %s", exc)
            return
        await self.broadcast(party_id, message)

    def get_connection_count(self, party_id: str) -> int:
        return len(self.active_connections.get(party_id, []))


ws_manager = ConnectionManager()