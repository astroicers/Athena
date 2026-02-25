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
    db_status = "error"
    try:
        cursor = await db.execute("SELECT 1")
        await cursor.fetchone()
        db_status = "connected"
    except Exception:
        db_status = "error"

    # Caldera status: mock mode or connected
    caldera_status = "mock" if settings.MOCK_CALDERA else "connected"

    # Shannon status: disabled by default (no SHANNON_URL set for POC)
    # If SHANNON_URL is configured, report disconnected (no live ping for POC)
    if settings.SHANNON_URL:
        shannon_status = "disconnected"
    else:
        shannon_status = "disabled"

    # LLM status: mock > claude > openai > unavailable
    if settings.MOCK_LLM:
        llm_status = "mock"
    elif settings.ANTHROPIC_API_KEY:
        llm_status = "claude"
    elif settings.OPENAI_API_KEY:
        llm_status = "openai"
    else:
        llm_status = "unavailable"

    return HealthStatus(
        status="ok",
        version="0.1.0",
        services={
            "database": db_status,
            "caldera": caldera_status,
            "shannon": shannon_status,
            "websocket": "active",
            "llm": llm_status,
        },
    )
