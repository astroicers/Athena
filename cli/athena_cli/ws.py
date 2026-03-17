"""WebSocket client for real-time event streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import websockets
from websockets.exceptions import ConnectionClosed

from athena_cli.config import get_config

logger = logging.getLogger(__name__)


async def stream_events(
    op_id: str,
    event_filter: set[str] | None = None,
    *,
    ws_url: str | None = None,
    max_reconnects: int = 5,
) -> AsyncIterator[tuple[str, dict, str]]:
    """Yield (event_type, data, timestamp) from the operation WebSocket.

    Auto-reconnects with exponential backoff up to *max_reconnects* times.
    If *event_filter* is provided, only matching event types are yielded.
    """
    cfg = get_config()
    base = ws_url or cfg.ws_url
    uri = f"{base}/ws/{op_id}"

    attempts = 0
    while attempts < max_reconnects:
        try:
            async with websockets.connect(uri) as ws:
                attempts = 0  # reset on successful connection
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    evt = msg.get("event", "")
                    if event_filter is None or evt in event_filter:
                        yield evt, msg.get("data", {}), msg.get("timestamp", "")
        except (ConnectionClosed, ConnectionRefusedError, OSError) as exc:
            attempts += 1
            if attempts >= max_reconnects:
                logger.warning("WebSocket max reconnects reached: %s", exc)
                return
            wait = min(2 ** attempts, 16)
            logger.debug("WebSocket reconnecting in %ds (%s)", wait, exc)
            await asyncio.sleep(wait)
