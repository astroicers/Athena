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

"""OODA loop endpoints."""

import logging

import aiosqlite
from fastapi import APIRouter, Depends

from app.clients.c2_client import C2EngineClient
from app.clients.mock_c2_client import MockC2Client
from app.clients.ai_engine_client import AiEngineClient
from app.config import settings
from app.database import get_db, _DB_FILE
from app.models import OODAIteration
from app.models.api_schemas import OODATimelineEntry
from app.routers._deps import ensure_operation
from app.services.c5isr_mapper import C5ISRMapper
from app.services.decision_engine import DecisionEngine
from app.services.engine_router import EngineRouter
from app.services.fact_collector import FactCollector
from app.services.ooda_controller import OODAController
from app.services.orient_engine import OrientEngine
from app.ws_manager import ws_manager
from app.services.ooda_scheduler import start_auto_loop, stop_auto_loop, get_loop_status

logger = logging.getLogger(__name__)
router = APIRouter()

# Module-level singleton — built once, reused across requests
_controller: OODAController | None = None


def _get_controller() -> OODAController:
    """Return singleton OODAController, building it on first call."""
    global _controller
    if _controller is not None:
        return _controller

    fc = FactCollector(ws_manager)
    orient = OrientEngine(ws_manager)
    decision = DecisionEngine()
    c5isr = C5ISRMapper(ws_manager)

    # Engine clients — MOCK_C2_ENGINE controls mock vs real C2 engine independently of MOCK_LLM
    c2_engine: MockC2Client | C2EngineClient = MockC2Client()
    if not settings.MOCK_C2_ENGINE:
        try:
            c2_engine = C2EngineClient(settings.C2_ENGINE_URL, settings.C2_ENGINE_API_KEY)
        except Exception:
            logger.warning("Failed to connect to C2 engine, falling back to mock")

    ai_engine = AiEngineClient(settings.AI_ENGINE_URL)
    router_svc = EngineRouter(c2_engine, ai_engine if ai_engine.enabled else None, fc, ws_manager)

    _controller = OODAController(fc, orient, decision, router_svc, c5isr, ws_manager)
    return _controller


def _row_to_ooda(row: aiosqlite.Row) -> OODAIteration:
    return OODAIteration(
        id=row["id"],
        operation_id=row["operation_id"],
        iteration_number=row["iteration_number"],
        phase=row["phase"],
        observe_summary=row["observe_summary"],
        orient_summary=row["orient_summary"],
        decide_summary=row["decide_summary"],
        act_summary=row["act_summary"],
        recommendation_id=row["recommendation_id"],
        technique_execution_id=row["technique_execution_id"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


@router.post("/operations/{operation_id}/ooda/trigger")
async def trigger_ooda(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Trigger a full OODA cycle: Observe -> Orient -> Decide -> Act."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    controller = _get_controller()
    result = await controller.trigger_cycle(db, operation_id)
    return result


@router.get("/operations/{operation_id}/ooda/current", response_model=OODAIteration | None)
async def get_current_ooda(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM ooda_iterations WHERE operation_id = ? "
        "ORDER BY iteration_number DESC LIMIT 1",
        (operation_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return _row_to_ooda(row)


@router.get("/operations/{operation_id}/ooda/history", response_model=list[OODAIteration])
async def get_ooda_history(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM ooda_iterations WHERE operation_id = ? "
        "ORDER BY iteration_number ASC",
        (operation_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_ooda(r) for r in rows]


@router.get(
    "/operations/{operation_id}/ooda/timeline",
    response_model=list[OODATimelineEntry],
)
async def get_ooda_timeline(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Flatten iterations into per-phase timeline entries."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM ooda_iterations WHERE operation_id = ? "
        "ORDER BY iteration_number ASC",
        (operation_id,),
    )
    rows = await cursor.fetchall()

    entries: list[OODATimelineEntry] = []
    phase_map = [
        ("observe", "observe_summary"),
        ("orient", "orient_summary"),
        ("decide", "decide_summary"),
        ("act", "act_summary"),
    ]
    for row in rows:
        for phase_name, summary_col in phase_map:
            summary = row[summary_col]
            if summary:
                entries.append(
                    OODATimelineEntry(
                        iteration_number=row["iteration_number"],
                        phase=phase_name,
                        summary=summary,
                        timestamp=row["started_at"] or "",
                    )
                )
    return entries


@router.post("/operations/{operation_id}/ooda/auto-start")
async def start_ooda_auto_loop(
    operation_id: str,
    interval_sec: int = 30,
    max_iterations: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Start automated OODA loop (APScheduler). Runs every interval_sec until max_iterations or stopped."""
    await ensure_operation(db, operation_id)  # raises 404 if not found
    return await start_auto_loop(
        operation_id=operation_id,
        db_path=str(_DB_FILE),
        interval_sec=interval_sec,
        max_iterations=max_iterations,
    )


@router.delete("/operations/{operation_id}/ooda/auto-stop")
async def stop_ooda_auto_loop(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Stop automated OODA loop for this operation."""
    await ensure_operation(db, operation_id)  # raises 404 if not found
    return await stop_auto_loop(operation_id)


@router.get("/operations/{operation_id}/ooda/auto-status")
async def get_ooda_auto_status(operation_id: str):
    """Get auto loop status for this operation (purely in-memory, no DB check needed)."""
    return get_loop_status(operation_id)
