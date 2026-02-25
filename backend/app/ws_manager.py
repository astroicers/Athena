"""WebSocket connection manager — standalone module to avoid circular imports.

The WebSocketManager class and singleton ``ws_manager`` live here so that
both the ``routers.ws`` route module **and** the ``services.*`` layer can
import them without triggering ``routers.__init__`` (which would create a
circular dependency).
"""

import json
from datetime import datetime, timezone

from fastapi import WebSocket


class WebSocketManager:
    """Manage WebSocket connections grouped by operation_id."""

    def __init__(self):
        # operation_id -> set of active WebSocket connections
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, operation_id: str, ws: WebSocket):
        await ws.accept()
        if operation_id not in self._connections:
            self._connections[operation_id] = set()
        self._connections[operation_id].add(ws)

    def disconnect(self, operation_id: str, ws: WebSocket):
        if operation_id in self._connections:
            self._connections[operation_id].discard(ws)
            if not self._connections[operation_id]:
                del self._connections[operation_id]

    async def broadcast(self, operation_id: str, event: str, data: dict):
        """
        Broadcast an event to all connections for an operation.

        Supported event types:
            log.new, agent.beacon, execution.update, ooda.phase,
            c5isr.update, fact.new, recommendation
        """
        message = json.dumps({
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        connections = self._connections.get(operation_id, set()).copy()
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(operation_id, ws)


# Singleton manager instance (importable by other modules for broadcasting)
ws_manager = WebSocketManager()
