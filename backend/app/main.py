# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""
Athena C5ISR API — FastAPI entry point.

Lifespan:
    - on startup  → init_db() (asyncpg pool + Alembic migrations + seed)
    - on shutdown → close pool
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings, _init_task_model_map

logger = logging.getLogger(__name__)


class MockModeMiddleware(BaseHTTPMiddleware):
    """Inject X-Athena-Mock header when any mock mode is active."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        mock_flags = []
        if settings.MOCK_LLM:
            mock_flags.append("llm")
        if settings.MOCK_C2_ENGINE:
            mock_flags.append("c2")
        if settings.MOCK_METASPLOIT:
            mock_flags.append("metasploit")
        if mock_flags:
            response.headers["X-Athena-Mock"] = ",".join(mock_flags)
        return response

from app.database import db_manager, get_db, init_db
from app.services.ooda_scheduler import start_scheduler, stop_scheduler
from app.routers import (
    admin,
    agents,
    attack_graph,
    c5isr,
    engagements,
    facts,
    health,
    logs,
    missions,
    ooda,
    operations,
    poc,
    recon,
    recommendations,
    reports,
    targets,
    techniques,
    terminal,
    tools,
    vulnerabilities,
    ws,
)
from app.routers import constraints, dashboard, objectives, opsec
from app.routers.playbooks import router as playbooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB and optionally seed demo data on startup."""
    _init_task_model_map()
    await init_db()
    start_scheduler()

    # --- Engine Registry ---
    from app.services import engine_registry as _engine_registry
    from app.clients.c2_client import C2EngineClient
    from app.clients.metasploit_client import MetasploitEngineAdapter

    _engine_registry.register(
        "c2", C2EngineClient(settings.C2_ENGINE_URL, settings.C2_ENGINE_API_KEY)
    )
    _engine_registry.register(
        "mock", C2EngineClient(settings.C2_ENGINE_URL, settings.C2_ENGINE_API_KEY)
    )
    _engine_registry.register("metasploit", MetasploitEngineAdapter())
    logger.info("Engine registry initialized: %s", _engine_registry.list_engines())

    # Seed playbook knowledge base + techniques + tools (no demo operations)
    from app.database.seed import seed_if_empty
    await seed_if_empty(db_manager)

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

        if mcp_manager:
            from app.clients.mcp_engine_client import MCPEngineClient
            _mcp_client = MCPEngineClient(mcp_manager)
            _engine_registry.register("mcp", _mcp_client)
            _engine_registry.register("mcp_ssh", _mcp_client)
            logger.info("MCP engines registered in engine_registry")

    yield  # application runs here

    if mcp_manager is not None:
        await mcp_manager.shutdown()
        from app.services.mcp_client_manager import set_mcp_manager as _set
        _set(None)
    stop_scheduler()
    await db_manager.shutdown()


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
    expose_headers=["X-Athena-Mock"],
)

# ── Mock Mode indicator ──────────────────────────────────────────────────
app.add_middleware(MockModeMiddleware)

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
app.include_router(attack_graph.router, prefix="/api", tags=["AttackGraph"])
app.include_router(vulnerabilities.router, tags=["Vulnerabilities"])
app.include_router(poc.router, tags=["PoC"])

app.include_router(playbooks_router)

# ── New Phase 2-4 routers ────────────────────────────────────────────────
app.include_router(constraints.router, prefix="/api", tags=["Constraints"])
app.include_router(opsec.router, prefix="/api", tags=["OPSEC"])
app.include_router(objectives.router, prefix="/api", tags=["Objectives"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])

# ── WebSocket (no /api prefix) ───────────────────────────────────────────
app.include_router(ws.router, tags=["WebSocket"])
app.include_router(terminal.router, tags=["Terminal"])
