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

"""Health check endpoint."""

import logging

import aiosqlite
from fastapi import APIRouter, Depends

from app.config import settings
from app.database import get_db
from app.models.api_schemas import HealthStatus

logger = logging.getLogger(__name__)

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

    # C2 engine status: mock or real connectivity check
    if settings.MOCK_C2_ENGINE:
        c2_engine_status = "mock"
    else:
        try:
            from app.clients.c2_client import C2EngineClient
            client = C2EngineClient(settings.C2_ENGINE_URL, settings.C2_ENGINE_API_KEY)
            c2_engine_status = "connected" if await client.is_available() else "unreachable"
            await client.aclose()
        except Exception:
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

    return HealthStatus(
        status="ok",
        version="0.1.0",
        services={
            "database": db_status,
            "c2_engine": c2_engine_status,
            "websocket": "active",
            "llm": llm_status,
        },
    )
