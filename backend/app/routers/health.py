"""Health check endpoint."""

from fastapi import APIRouter, Depends
import aiosqlite

from app.config import settings
from app.database import get_db
from app.models.api_schemas import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check(db: aiosqlite.Connection = Depends(get_db)):
    """Return service health status."""
    # Check database connectivity
    db_status = "ok"
    try:
        cursor = await db.execute("SELECT 1")
        await cursor.fetchone()
    except Exception:
        db_status = "error"

    llm_status = "mock" if settings.MOCK_LLM else "unknown"

    return HealthStatus(
        status="ok",
        version="0.1.0",
        services={
            "database": db_status,
            "caldera": "unknown",
            "shannon": "unknown",
            "websocket": "ok",
            "llm": llm_status,
        },
    )
