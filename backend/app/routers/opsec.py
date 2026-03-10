# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""OPSEC monitoring endpoints."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends

from app.database import get_db
from app.routers._deps import ensure_operation
from app.services import opsec_monitor, threat_level as tl_service

router = APIRouter()


@router.get("/operations/{operation_id}/opsec-status")
async def get_opsec_status(operation_id: str, db: asyncpg.Connection = Depends(get_db)):
    await ensure_operation(db, operation_id)
    status = await opsec_monitor.compute_status(db, operation_id)
    return status.model_dump()


@router.get("/operations/{operation_id}/threat-level")
async def get_threat_level(operation_id: str, db: asyncpg.Connection = Depends(get_db)):
    await ensure_operation(db, operation_id)
    result = await tl_service.compute_threat_level(db, operation_id)
    return result.model_dump()
