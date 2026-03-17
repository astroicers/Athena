# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Centralized OODA auto-trigger — any router/service can call this."""

import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)


async def auto_trigger_ooda(
    operation_id: str,
    reason: str,
    delay_sec: int | None = None,
) -> None:
    """Delay then trigger one OODA cycle for *operation_id*.

    Parameters
    ----------
    operation_id:
        The operation whose OODA cycle to trigger.
    reason:
        Human-readable reason (e.g. ``"recon.completed:scan-abc"``).
        Broadcast in the ``ooda.auto_trigger`` WebSocket event.
    delay_sec:
        Optional override for the delay before triggering.
        Defaults to 5 seconds.
    """
    from app.database import db_manager
    from app.services.ooda_controller import build_ooda_controller
    from app.ws_manager import ws_manager

    delay = delay_sec if delay_sec is not None else 5
    if delay > 0:
        await asyncio.sleep(delay)

    logger.info(
        "Auto-triggering OODA cycle for operation %s (reason: %s)", operation_id, reason,
    )
    await ws_manager.broadcast(
        operation_id, "ooda.auto_trigger", {"reason": reason},
    )

    iteration_id = str(uuid.uuid4())
    async with db_manager.connection() as db:
        try:
            controller = build_ooda_controller()
            await controller.trigger_cycle(db, operation_id)
        except Exception as exc:
            logger.exception(
                "Auto-triggered OODA cycle %s failed: %s", iteration_id, exc,
            )
            await ws_manager.broadcast(
                operation_id, "ooda.failed",
                {"iteration_id": iteration_id, "error": str(exc)},
            )
