# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
