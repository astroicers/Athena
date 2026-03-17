# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

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
        self._broadcast_total: int = 0
        self._broadcast_success: int = 0

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

    def active_connection_count(self) -> int:
        """Return total active WebSocket connections across all operations."""
        return sum(len(conns) for conns in self._connections.values())

    async def broadcast(self, operation_id: str, event: str, data: dict):
        """
        Broadcast an event to all connections for an operation.

        Supported event types:
            log.new, agent.beacon, execution.update, ooda.phase,
            c5isr.update, fact.new, recommendation
        """
        self._broadcast_total += 1
        message = json.dumps({
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, default=str)
        connections = self._connections.get(operation_id, set()).copy()
        any_success = False
        for ws in connections:
            try:
                await ws.send_text(message)
                any_success = True
            except Exception:
                self.disconnect(operation_id, ws)
        if any_success:
            self._broadcast_success += 1

    async def broadcast_global(self, event: str, data: dict):
        """Broadcast an event to ALL active connections across all operations."""
        message = json.dumps({
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, default=str)
        for op_id, connections in list(self._connections.items()):
            for ws in connections.copy():
                try:
                    await ws.send_text(message)
                except Exception:
                    self.disconnect(op_id, ws)


# Singleton manager instance (importable by other modules for broadcasting)
ws_manager = WebSocketManager()
