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

"""Recon phase endpoints — nmap scanning and initial access."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.database import get_db, _DB_FILE
from app.models.osint import OSINTDiscoverQueued, OSINTResult
from app.models.recon import ReconScanResult, InitialAccessResult, ReconScanQueued
from app.routers._deps import ensure_operation
from app.services.initial_access_engine import InitialAccessEngine
from app.services.osint_engine import OSINTEngine
from app.services.recon_engine import ReconEngine

logger = logging.getLogger(__name__)
router = APIRouter()


class ReconScanRequest(BaseModel):
    target_id: str
    enable_initial_access: bool = True
    c2_host: str | None = None  # defaults to settings.C2_ENGINE_URL


class OSINTDiscoverRequest(BaseModel):
    domain: str
    max_subdomains: int = 500


@router.post(
    "/operations/{op_id}/recon/scan",
    response_model=ReconScanQueued,
    status_code=202,
)
async def run_recon_scan(
    op_id: str,
    body: ReconScanRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> ReconScanQueued:
    """Enqueue a recon scan — returns immediately, executes in background."""
    db.row_factory = aiosqlite.Row

    # ── 1. Validate operation exists ─────────────────────────────────────────
    await ensure_operation(db, op_id)

    # ── 2. Validate target exists and belongs to this operation ──────────────
    cursor = await db.execute(
        "SELECT id, ip_address FROM targets WHERE id = ? AND operation_id = ?",
        (body.target_id, op_id),
    )
    target_row = await cursor.fetchone()
    if target_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Target '{body.target_id}' not found in operation '{op_id}'",
        )
    ip_address: str = target_row["ip_address"]

    # ── 3. Insert recon_scans row with status="queued" ────────────────────────
    scan_id = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        INSERT INTO recon_scans
            (id, operation_id, target_id, status, started_at)
        VALUES (?, ?, ?, 'queued', ?)
        """,
        (scan_id, op_id, body.target_id, now_utc),
    )
    await db.commit()

    # ── 4. Launch background task ─────────────────────────────────────────────
    _task = asyncio.create_task(
        _run_scan_background(scan_id, op_id, body.target_id, ip_address, body)
    )
    if _task is not None:
        _task.add_done_callback(
            lambda t: logger.warning("Recon background task cancelled for scan %s", scan_id)
            if t.cancelled() else None
        )

    # ── 5. Return immediately with 202 Accepted ───────────────────────────────
    return ReconScanQueued(
        scan_id=scan_id,
        status="queued",
        target_id=body.target_id,
        operation_id=op_id,
    )


async def _run_scan_background(
    scan_id: str,
    op_id: str,
    target_id: str,
    ip_address: str,
    body: ReconScanRequest,
) -> None:
    """Background task: run nmap + initial access, broadcast WS events."""
    from app.ws_manager import ws_manager  # local import to avoid circular

    async with aiosqlite.connect(_DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        try:
            # Mark running
            await db.execute(
                "UPDATE recon_scans SET status='running' WHERE id=?", (scan_id,)
            )
            await db.commit()
            await ws_manager.broadcast(
                op_id, "recon.started", {"scan_id": scan_id, "target_id": target_id}
            )

            # Run nmap scan
            recon_result = await ReconEngine().scan(db, op_id, target_id)
            await ws_manager.broadcast(
                op_id, "recon.progress", {"scan_id": scan_id, "phase": "initial_access"}
            )

            # Optional initial access
            ia_result = InitialAccessResult(
                success=False,
                method="none",
                credential=None,
                agent_deployed=False,
                error=None,
            )
            if body.enable_initial_access:
                ia_engine = InitialAccessEngine()
                ia_result = await ia_engine.try_ssh_login(
                    db, op_id, target_id, ip_address, port=22
                )

                # Bootstrap C2 agent if SSH succeeded and not in mock mode
                if ia_result.success and not settings.MOCK_C2_ENGINE:
                    c2_host = (
                        body.c2_host
                        or settings.C2_AGENT_CALLBACK_URL
                        or settings.C2_ENGINE_URL
                    )
                    cred_parts = (ia_result.credential or ":").split(":", 1)
                    cred_tuple = (cred_parts[0], cred_parts[1] if len(cred_parts) > 1 else "")
                    deployed = await ia_engine.bootstrap_c2_agent(
                        ip_address, cred_tuple, c2_host
                    )
                    ia_result = InitialAccessResult(
                        success=ia_result.success,
                        method=ia_result.method,
                        credential=ia_result.credential,
                        agent_deployed=deployed,
                        error=ia_result.error,
                    )

            # Update DB as completed
            open_ports_json = json.dumps(
                [{"port": svc.port, "service": svc.service} for svc in recon_result.services]
            )
            completed_at = datetime.now(timezone.utc).isoformat()
            await db.execute(
                """
                UPDATE recon_scans SET
                    status                = 'completed',
                    open_ports            = ?,
                    os_guess              = ?,
                    initial_access_method = ?,
                    credential_found      = ?,
                    agent_deployed        = ?,
                    completed_at          = ?
                WHERE id = ?
                """,
                (
                    open_ports_json,
                    recon_result.os_guess,
                    ia_result.method,
                    ia_result.credential,
                    1 if ia_result.agent_deployed else 0,
                    completed_at,
                    scan_id,
                ),
            )
            await db.commit()

            # Broadcast completion
            await ws_manager.broadcast(
                op_id,
                "recon.completed",
                {
                    "scan_id": scan_id,
                    "target_id": target_id,
                    "facts_written": recon_result.facts_written,
                    "credential_found": ia_result.credential,
                    "services_found": len(recon_result.services),
                },
            )

        except Exception as exc:
            logger.exception("Background recon scan %s failed: %s", scan_id, exc)
            try:
                await db.execute(
                    "UPDATE recon_scans SET status='failed', completed_at=? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), scan_id),
                )
                await db.commit()
            except Exception:
                logger.exception(
                    "Failed to update recon_scan status to 'failed' for %s", scan_id
                )
            await ws_manager.broadcast(
                op_id,
                "recon.failed",
                {"scan_id": scan_id, "target_id": target_id, "error": str(exc)},
            )


@router.get("/operations/{op_id}/recon/status")
async def get_recon_status(
    op_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Return the most recent recon scan row for this operation."""
    db.row_factory = aiosqlite.Row

    await ensure_operation(db, op_id)

    cursor = await db.execute(
        """
        SELECT id, operation_id, target_id, status,
               nmap_result, open_ports, os_guess,
               initial_access_method, credential_found,
               agent_deployed, started_at, completed_at
        FROM recon_scans
        WHERE operation_id = ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (op_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No recon scans found for operation '{op_id}'",
        )

    return dict(row)


@router.post(
    "/operations/{op_id}/osint/discover",
    response_model=OSINTDiscoverQueued,
    status_code=202,
)
async def run_osint_discover(
    op_id: str,
    body: OSINTDiscoverRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> OSINTDiscoverQueued:
    """Enqueue OSINT discovery — returns 202 immediately, executes in background."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, op_id)

    _task = asyncio.create_task(
        _run_osint_background(op_id, body.domain, body.max_subdomains)
    )
    if _task is not None:
        _task.add_done_callback(
            lambda t: logger.warning(
                "OSINT background task cancelled for op %s domain %s", op_id, body.domain
            )
            if t.cancelled() else None
        )

    return OSINTDiscoverQueued(
        status="queued",
        operation_id=op_id,
        domain=body.domain,
    )


async def _run_osint_background(op_id: str, domain: str, max_subdomains: int) -> None:
    """Background task: run OSINT subdomain discovery."""
    from app.ws_manager import ws_manager  # local import to avoid circular

    async with aiosqlite.connect(_DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        try:
            result = await OSINTEngine().discover(
                db=db,
                operation_id=op_id,
                domain=domain,
                max_subdomains=max_subdomains,
            )
            await ws_manager.broadcast(op_id, "osint.completed", {
                "domain": domain,
                "subdomains_found": result.subdomains_found,
            })
        except Exception as exc:
            logger.exception(
                "Background OSINT discover for domain %s failed: %s", domain, exc
            )
            await ws_manager.broadcast(op_id, "osint.failed", {
                "domain": domain,
                "error": str(exc),
            })
