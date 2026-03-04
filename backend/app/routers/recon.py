# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

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
from app.models.recon import ReconScanResult, InitialAccessResult, ReconScanQueued, ServiceInfo
from app.routers._deps import ensure_operation
from app.services.initial_access_engine import InitialAccessEngine
from app.services.osint_engine import OSINTEngine
from app.services.recon_engine import ReconEngine

logger = logging.getLogger(__name__)
router = APIRouter()

# Mock scan phases with delays (only used when MOCK_C2_ENGINE=True)
_MOCK_SCAN_PHASES: list[tuple[str, float]] = [
    ("host_discovery", 1.0),
    ("port_scan", 2.0),
    ("service_detection", 1.5),
    ("os_fingerprint", 1.0),
    ("credential_test", 1.5),
    ("finalizing", 1.0),
]


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
            (id, operation_id, target_id, ip_address, status, started_at)
        VALUES (?, ?, ?, ?, 'queued', ?)
        """,
        (scan_id, op_id, body.target_id, ip_address, now_utc),
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

    total_mock_steps = len(_MOCK_SCAN_PHASES)

    async def _broadcast_phase(phase: str, step: int) -> None:
        await ws_manager.broadcast(
            op_id,
            "recon.progress",
            {
                "scan_id": scan_id,
                "target_id": target_id,
                "phase": phase,
                "step": step,
                "total_steps": total_mock_steps,
            },
        )

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

            # ── Mock mode: simulate phased scan with delays ─────────────
            if settings.MOCK_C2_ENGINE:
                for idx, (phase_key, delay) in enumerate(_MOCK_SCAN_PHASES[:4]):
                    await _broadcast_phase(phase_key, idx + 1)
                    await asyncio.sleep(delay)

            # Run nmap scan
            recon_result = await ReconEngine().scan(db, op_id, target_id)

            if settings.MOCK_C2_ENGINE:
                await _broadcast_phase("credential_test", 5)
                await asyncio.sleep(1.5)
            else:
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
                # Only attempt SSH if port 22 was found open by nmap
                ssh_open = any(
                    svc.port == 22 and svc.service in ("ssh", "unknown")
                    for svc in recon_result.services
                )
                if ssh_open:
                    ia_engine = InitialAccessEngine()
                    ia_result = await ia_engine.try_ssh_login(
                        db, op_id, target_id, ip_address, port=22
                    )
                else:
                    logger.info(
                        "Skipping initial access for %s — port 22 not open (%d services found)",
                        ip_address, len(recon_result.services),
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

            # Mock mode: finalizing phase
            if settings.MOCK_C2_ENGINE:
                await _broadcast_phase("finalizing", 6)
                await asyncio.sleep(1.0)

            # Update DB as completed
            open_ports_json = json.dumps([
                {
                    "port": svc.port,
                    "protocol": svc.protocol,
                    "service": svc.service,
                    "version": svc.version,
                }
                for svc in recon_result.services
            ])
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


@router.get(
    "/operations/{op_id}/recon/scans/{scan_id}",
    response_model=ReconScanResult,
)
async def get_recon_scan_result(
    op_id: str,
    scan_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> ReconScanResult:
    """Return a full ReconScanResult for a completed scan (used by frontend modal)."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, op_id)

    cursor = await db.execute(
        """
        SELECT s.id, s.operation_id, s.target_id, s.status,
               s.open_ports, s.os_guess,
               s.initial_access_method, s.credential_found,
               s.agent_deployed, s.started_at, s.completed_at,
               t.ip_address
        FROM recon_scans s
        JOIN targets t ON t.id = s.target_id
        WHERE s.id = ? AND s.operation_id = ?
        """,
        (scan_id, op_id),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Scan '{scan_id}' not found in operation '{op_id}'",
        )

    open_ports = json.loads(row["open_ports"] or "[]")
    started = row["started_at"] or ""
    completed = row["completed_at"] or ""
    # Calculate duration from timestamps
    scan_duration = 0.0
    if started and completed:
        try:
            t_start = datetime.fromisoformat(started)
            t_end = datetime.fromisoformat(completed)
            scan_duration = (t_end - t_start).total_seconds()
        except ValueError:
            pass

    services = [
        ServiceInfo(
            port=p["port"],
            protocol=p.get("protocol", "tcp"),
            service=p.get("service", "unknown"),
            version=p.get("version", ""),
            state="open",
        )
        for p in open_ports
    ]

    return ReconScanResult(
        scan_id=row["id"],
        status=row["status"],
        target_id=row["target_id"],
        operation_id=row["operation_id"],
        ip_address=row["ip_address"],
        os_guess=row["os_guess"],
        services_found=len(open_ports),
        services=services,
        facts_written=0,  # not stored in DB; already reflected in facts table
        initial_access=InitialAccessResult(
            success=bool(row["credential_found"]),
            method=row["initial_access_method"] or "none",
            credential=row["credential_found"],
            agent_deployed=bool(row["agent_deployed"]),
            error=None,
        ),
        scan_duration_sec=round(scan_duration, 1),
    )


@router.get("/operations/{op_id}/recon/status")
async def get_recon_status(
    op_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Return the most recent recon scan row for this operation.

    Auto-fails scans stuck in 'running'/'queued' for more than 10 minutes.
    """
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

    result = dict(row)

    # Auto-fail stuck scans (running/queued > 10 minutes)
    if result["status"] in ("running", "queued") and result.get("started_at"):
        try:
            started = datetime.fromisoformat(result["started_at"])
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            if elapsed > 600:  # 10 minutes
                now_iso = datetime.now(timezone.utc).isoformat()
                await db.execute(
                    "UPDATE recon_scans SET status='failed', completed_at=? WHERE id=?",
                    (now_iso, result["id"]),
                )
                await db.commit()
                result["status"] = "failed"
                result["completed_at"] = now_iso
                logger.warning("Auto-failed stuck recon scan %s (>10 min)", result["id"])
        except (ValueError, TypeError):
            pass

    return result


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
