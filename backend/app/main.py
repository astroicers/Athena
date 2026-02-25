"""
Athena C5ISR API — FastAPI entry point.

Lifespan:
    - on startup  → init_db(), then seed if tables are empty
    - on shutdown → (nothing special for POC)

Routers are mounted under ``/api`` prefix.
WebSocket is mounted at ``/ws/{operation_id}`` (no ``/api`` prefix).
"""

from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import _DB_FILE, get_db, init_db
from app.routers import (
    agents,
    c5isr,
    facts,
    health,
    logs,
    missions,
    ooda,
    operations,
    recommendations,
    targets,
    techniques,
    ws,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB and optionally seed demo data on startup."""
    await init_db()

    # Seed if the operations table is empty
    async with aiosqlite.connect(_DB_FILE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM operations")
        row = await cursor.fetchone()
        if row and row[0] == 0:
            from app.seed.demo_scenario import seed
            await seed()

    yield  # application runs here


app = FastAPI(
    title="Athena C5ISR API",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ── Routers (all prefixed with /api) ─────────────────────────────────────
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(operations.router, prefix="/api", tags=["Operations"])
app.include_router(ooda.router, prefix="/api", tags=["OODA"])
app.include_router(techniques.router, prefix="/api", tags=["Techniques"])
app.include_router(missions.router, prefix="/api", tags=["Missions"])
app.include_router(targets.router, prefix="/api", tags=["Targets"])
app.include_router(agents.router, prefix="/api", tags=["Agents"])
app.include_router(facts.router, prefix="/api", tags=["Facts"])
app.include_router(c5isr.router, prefix="/api", tags=["C5ISR"])
app.include_router(logs.router, prefix="/api", tags=["Logs"])
app.include_router(recommendations.router, prefix="/api", tags=["Recommendations"])

# ── WebSocket (no /api prefix) ───────────────────────────────────────────
app.include_router(ws.router, tags=["WebSocket"])
