"""OODA loop endpoints."""

from fastapi import APIRouter, Depends
import aiosqlite

from app.config import settings
from app.database import get_db
from app.models import OODAIteration
from app.models.api_schemas import OODATimelineEntry
from app.routers._deps import ensure_operation
from app.ws_manager import ws_manager
from app.clients.mock_caldera_client import MockCalderaClient
from app.clients.caldera_client import CalderaClient
from app.clients.shannon_client import ShannonClient
from app.services.fact_collector import FactCollector
from app.services.orient_engine import OrientEngine
from app.services.decision_engine import DecisionEngine
from app.services.engine_router import EngineRouter
from app.services.c5isr_mapper import C5ISRMapper
from app.services.ooda_controller import OODAController

router = APIRouter()


def _build_controller() -> OODAController:
    """Build the OODA controller with all dependencies."""
    fc = FactCollector(ws_manager)
    orient = OrientEngine(ws_manager)
    decision = DecisionEngine()
    c5isr = C5ISRMapper(ws_manager)

    # Engine clients
    caldera = MockCalderaClient()
    if not settings.MOCK_LLM:
        try:
            real = CalderaClient(settings.CALDERA_URL, settings.CALDERA_API_KEY)
            caldera = real  # type: ignore[assignment]
        except Exception:
            pass  # fallback to mock

    shannon = ShannonClient(settings.SHANNON_URL)
    router_svc = EngineRouter(caldera, shannon if shannon.enabled else None, fc, ws_manager)

    return OODAController(fc, orient, decision, router_svc, c5isr, ws_manager)


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

    controller = _build_controller()
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
