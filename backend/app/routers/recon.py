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

import json
import logging
import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.database import get_db
from app.models.osint import OSINTResult
from app.models.recon import ReconScanResult, InitialAccessResult
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
    response_model=ReconScanResult,
)
async def run_recon_scan(
    op_id: str,
    body: ReconScanRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> ReconScanResult:
    """Run an nmap recon scan against a target and optionally attempt initial access."""
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

    # ── 3. Insert recon_scans row with status="running" ───────────────────────
    scan_id = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """
        INSERT INTO recon_scans
            (id, operation_id, target_id, status, started_at)
        VALUES (?, ?, ?, 'running', ?)
        """,
        (scan_id, op_id, body.target_id, now_utc),
    )
    await db.commit()

    # ── 4–6. Scan + optional initial access, with error handling ─────────────
    try:
        # Step 4: Run the nmap scan
        recon_result = await ReconEngine().scan(db, op_id, body.target_id)

        # Step 5: Optional initial access when port 22 is open
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
                db, op_id, body.target_id, ip_address, port=22
            )

            # Step 5c: Bootstrap C2 agent if SSH succeeded and not in mock mode
            if ia_result.success and not settings.MOCK_C2_ENGINE:
                # Use C2_AGENT_CALLBACK_URL if set (external URL reachable from targets),
                # then request override, then fall back to C2_ENGINE_URL
                c2_host = (
                    body.c2_host
                    or settings.C2_AGENT_CALLBACK_URL
                    or settings.C2_ENGINE_URL
                )
                # credential format is "user:pass"
                cred_parts = (ia_result.credential or ":").split(":", 1)
                cred_tuple = (cred_parts[0], cred_parts[1] if len(cred_parts) > 1 else "")
                deployed = await ia_engine.bootstrap_caldera_agent(
                    ip_address, cred_tuple, c2_host
                )
                # ia_result is immutable (Pydantic), rebuild with updated field
                ia_result = InitialAccessResult(
                    success=ia_result.success,
                    method=ia_result.method,
                    credential=ia_result.credential,
                    agent_deployed=deployed,
                    error=ia_result.error,
                )

        # Step 6: Update recon_scans row as completed
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

        # Step 7: Build and return response
        return ReconScanResult(
            scan_id=scan_id,
            status="completed",
            target_id=body.target_id,
            operation_id=op_id,
            ip_address=recon_result.ip_address,
            os_guess=recon_result.os_guess,
            services_found=len(recon_result.services),
            facts_written=recon_result.facts_written,
            initial_access=ia_result,
            scan_duration_sec=recon_result.scan_duration_sec,
        )

    except Exception as exc:
        logger.exception("Recon scan %s failed: %s", scan_id, exc)

        # Mark scan as failed in DB
        try:
            await db.execute(
                """
                UPDATE recon_scans SET
                    status       = 'failed',
                    completed_at = ?
                WHERE id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), scan_id),
            )
            await db.commit()
        except Exception:
            logger.exception("Failed to update recon_scan status to 'failed' for %s", scan_id)

        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    response_model=OSINTResult,
)
async def run_osint_discover(
    op_id: str,
    body: OSINTDiscoverRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> OSINTResult:
    """Run OSINT subdomain discovery for a domain."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, op_id)

    try:
        result = await OSINTEngine().discover(
            db=db,
            operation_id=op_id,
            domain=body.domain,
            max_subdomains=body.max_subdomains,
        )
        return result
    except Exception as exc:
        logger.exception("OSINT discover failed for domain %s: %s", body.domain, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
