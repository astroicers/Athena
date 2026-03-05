# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

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
from fastapi.responses import ORJSONResponse

from app.config import settings
from app.database import _DB_FILE, get_db, init_db
from app.services.ooda_scheduler import start_scheduler, stop_scheduler
from app.routers import (
    admin,
    agents,
    c5isr,
    engagements,
    facts,
    health,
    logs,
    missions,
    ooda,
    operations,
    recon,
    recommendations,
    reports,
    targets,
    techniques,
    terminal,
    tools,
    ws,
)
from app.routers.playbooks import router as playbooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB and optionally seed demo data on startup."""
    await init_db()
    start_scheduler()

    # Seed if the operations table is empty
    async with aiosqlite.connect(_DB_FILE) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM operations")
        row = await cursor.fetchone()
        if row and row[0] == 0:
            from app.seed.demo_scenario import seed
            await seed()

    # MCP integration — only when opted in
    mcp_manager = None
    if settings.MCP_ENABLED:
        from app.services.mcp_client_manager import (
            MCPClientManager,
            set_mcp_manager,
        )

        from app.ws_manager import ws_manager as _ws_mgr

        mcp_manager = MCPClientManager(ws_manager=_ws_mgr)
        await mcp_manager.startup()
        app.state.mcp_manager = mcp_manager
        set_mcp_manager(mcp_manager)

    yield  # application runs here

    if mcp_manager is not None:
        await mcp_manager.shutdown()
        from app.services.mcp_client_manager import set_mcp_manager as _set
        _set(None)
    stop_scheduler()


app = FastAPI(
    title="Athena C5ISR API",
    version="0.1.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:58080",
    ],
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
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(recon.router, prefix="/api", tags=["Recon"])
app.include_router(engagements.router, prefix="/api", tags=["Engagements"])
app.include_router(tools.router, prefix="/api", tags=["Tools"])

app.include_router(playbooks_router)

# ── WebSocket (no /api prefix) ───────────────────────────────────────────
app.include_router(ws.router, tags=["WebSocket"])
app.include_router(terminal.router, tags=["Terminal"])
