"""WebSocket route for real-time operation events."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws_manager import WebSocketManager, ws_manager  # noqa: F401 — re-export

router = APIRouter()


@router.websocket("/ws/{operation_id}")
async def websocket_endpoint(websocket: WebSocket, operation_id: str):
    await ws_manager.connect(operation_id, websocket)
    try:
        while True:
            # Keep the connection alive; handle incoming messages if needed
            data = await websocket.receive_text()
            # Echo back for debug / heartbeat
            await websocket.send_text(
                json.dumps({
                    "event": "echo",
                    "data": {"received": data},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(operation_id, websocket)
