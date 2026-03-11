# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Health check endpoint."""

import asyncio
import logging

import asyncpg
from fastapi import APIRouter, Depends

from app.config import settings
from app.database import get_db
from app.models.api_schemas import HealthStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthStatus)


async def health_check(db: asyncpg.Connection = Depends(get_db)):
    """Return service health status."""
    # Check database connectivity
    db_status = "error"
    try:
        await db.fetchval("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "error"

    # C2 engine status: mock or real connectivity check
    if settings.MOCK_C2_ENGINE:
        c2_engine_status = "mock"
    else:
        try:
            from app.clients.c2_client import C2EngineClient
            client = C2EngineClient(settings.C2_ENGINE_URL, settings.C2_ENGINE_API_KEY)
            available = await asyncio.wait_for(client.is_available(), timeout=2.0)
            c2_engine_status = "connected" if available else "unreachable"
            await client.aclose()
        except (Exception, asyncio.TimeoutError):
            c2_engine_status = "unreachable"

    # LLM status: mock > claude (api_key) > claude (oauth) > openai > unavailable
    if settings.MOCK_LLM:
        llm_status = "mock"
    elif settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_AUTH_TOKEN:
        llm_status = "claude"
    elif settings.LLM_BACKEND in ("oauth", "auto"):
        from app.services.oauth_token_manager import OAuthTokenManager
        mgr = OAuthTokenManager()
        llm_status = "claude (oauth)" if mgr.is_available() else "unavailable"
    elif settings.OPENAI_API_KEY:
        llm_status = "openai"
    else:
        llm_status = "unavailable"

    services = {
        "database": db_status,
        "c2_engine": c2_engine_status,
        "websocket": "active",
        "llm": llm_status,
    }

    if settings.MCP_ENABLED:
        from app.services.mcp_client_manager import get_mcp_manager

        mcp_mgr = get_mcp_manager()
        mcp_list = mcp_mgr.list_servers() if mcp_mgr else []

        # Append non-MCP containers that tools depend on
        if not settings.MOCK_METASPLOIT:
            msf_connected = False
            try:
                import socket
                s = socket.create_connection(
                    (settings.MSF_RPC_HOST, settings.MSF_RPC_PORT), timeout=1,
                )
                s.close()
                msf_connected = True
            except Exception:
                pass
            mcp_list.append({
                "name": "msf-rpc",
                "transport": "rpc",
                "enabled": True,
                "connected": msf_connected,
                "tool_count": 0,
                "description": "Metasploit Framework RPC",
                "circuit_state": "closed" if msf_connected else "open",
                "failure_count": 0 if msf_connected else 1,
            })

        services["mcp_servers"] = mcp_list

    # Mock mode indicators for frontend awareness
    mock_modes = {}
    if settings.MOCK_LLM:
        mock_modes["llm"] = True
    if settings.MOCK_C2_ENGINE:
        mock_modes["c2"] = True
    if settings.MOCK_METASPLOIT:
        mock_modes["metasploit"] = True
    if mock_modes:
        services["mock_mode"] = mock_modes

    return HealthStatus(
        status="ok",
        version="0.1.0",
        services=services,
    )


@router.get("/mcp/status")


async def mcp_status():
    """Return MCP subsystem status with circuit breaker states."""
    if not settings.MCP_ENABLED:
        return {"enabled": False, "servers": [], "tool_count": 0}

    from app.services.mcp_client_manager import get_mcp_manager

    mcp_mgr = get_mcp_manager()
    if mcp_mgr is None:
        return {"enabled": True, "servers": [], "tool_count": 0}

    servers = mcp_mgr.list_servers()
    total_tools = sum(s.get("tool_count", 0) for s in servers)
    return {
        "enabled": True,
        "servers": servers,
        "tool_count": total_tools,
    }
