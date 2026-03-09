# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""SPEC-044: Vulnerability management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite

from app.database import get_db
from app.routers._deps import ensure_operation
from app.services.vulnerability_manager import VulnerabilityManager

router = APIRouter(prefix="/api", tags=["vulnerabilities"])
_vuln_mgr = VulnerabilityManager()


class StatusTransitionRequest(BaseModel):
    status: str


@router.get("/operations/{op_id}/vulnerabilities")
async def list_vulnerabilities(
    op_id: str,
    severity: str | None = None,
    status: str | None = None,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    await ensure_operation(db, op_id)
    vulns = await _vuln_mgr.list_by_operation(db, op_id, severity, status)
    summary = await _vuln_mgr.get_summary(db, op_id)
    return {"vulnerabilities": vulns, "summary": summary}


@router.put("/operations/{op_id}/vulnerabilities/{vuln_id}/status")
async def update_vulnerability_status(
    op_id: str,
    vuln_id: str,
    body: StatusTransitionRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    await ensure_operation(db, op_id)
    try:
        return await _vuln_mgr.transition_status(db, vuln_id, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/operations/{op_id}/vulnerabilities/summary")
async def get_vulnerability_summary(
    op_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    await ensure_operation(db, op_id)
    return await _vuln_mgr.get_summary(db, op_id)
