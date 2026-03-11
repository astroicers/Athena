# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Recon phase endpoints -- nmap scanning and initial access."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.database import db_manager, get_db
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
_REAL_SCAN_STEPS = 3  # nmap_scan, initial_access, finalizing
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
    db: asyncpg.Connection = Depends(get_db),
) -> ReconScanQueued:
    """Enqueue a recon scan -- returns immediately, executes in background."""

    # -- 1. Validate operation exists --
    await ensure_operation(db, op_id)

    # -- 2. Validate target exists and belongs to this operation --
    target_row = await db.fetchrow(
        "SELECT id, ip_address FROM targets WHERE id = $1 AND operation_id = $2",
        body.target_id, op_id,
    )
    if target_row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Target '{body.target_id}' not found in operation '{op_id}'",
        )
    ip_address: str = target_row["ip_address"]

    # -- 3. Insert recon_scans row with status="queued" --
    scan_id = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc)
    await db.execute(
        """
        INSERT INTO recon_scans
            (id, operation_id, target_id, ip_address, status, started_at)
        VALUES ($1, $2, $3, $4, 'queued', $5)
        """,
        scan_id, op_id, body.target_id, ip_address, now_utc,
    )

    # -- 4. Launch background task --
    _task = asyncio.create_task(
        _run_scan_background(scan_id, op_id, body.target_id, ip_address, body)
    )
    if _task is not None:
        _task.add_done_callback(
            lambda t: logger.warning("Recon background task cancelled for scan %s", scan_id)
            if t.cancelled() else None
        )

    # -- 5. Return immediately with 202 Accepted --
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

    total_steps = len(_MOCK_SCAN_PHASES) if settings.MOCK_C2_ENGINE else _REAL_SCAN_STEPS

    async def _broadcast_phase(phase: str, step: int) -> None:
        await ws_manager.broadcast(
            op_id,
            "recon.progress",
            {
                "scan_id": scan_id,
                "target_id": target_id,
                "phase": phase,
                "step": step,
                "total_steps": total_steps,
            },
        )

    async with db_manager.connection() as db:
        try:
            # Mark running
            await db.execute(
                "UPDATE recon_scans SET status='running' WHERE id=$1", scan_id
            )
            await ws_manager.broadcast(
                op_id, "recon.started", {"scan_id": scan_id, "target_id": target_id}
            )

            # -- Mock mode: simulate phased scan with delays --
            if settings.MOCK_C2_ENGINE:
                for idx, (phase_key, delay) in enumerate(_MOCK_SCAN_PHASES[:4]):
                    await _broadcast_phase(phase_key, idx + 1)
                    await asyncio.sleep(delay)
            else:
                await _broadcast_phase("nmap_scan", 1)

            # Run nmap scan
            recon_result = await ReconEngine().scan(db, op_id, target_id)

            if settings.MOCK_C2_ENGINE:
                await _broadcast_phase("credential_test", 5)
                await asyncio.sleep(1.5)
            else:
                await _broadcast_phase("initial_access", 2)

            # Optional initial access -- multi-protocol (SSH/RDP/WinRM)
            ia_result = InitialAccessResult(
                success=False,
                method="none",
                credential=None,
                agent_deployed=False,
                error=None,
            )
            if body.enable_initial_access:
                ia_engine = InitialAccessEngine()
                services_dicts = [
                    {"port": svc.port, "service": svc.service}
                    for svc in recon_result.services
                ]
                ia_result = await ia_engine.try_initial_access(
                    db, op_id, target_id, ip_address, services_dicts,
                )

                # Bootstrap C2 agent only for SSH success (RDP/WinRM can't deploy sandcat)
                if (
                    ia_result.success
                    and ia_result.method == "ssh_credential"
                    and not settings.MOCK_C2_ENGINE
                ):
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

            # Finalizing phase
            if settings.MOCK_C2_ENGINE:
                await _broadcast_phase("finalizing", 6)
                await asyncio.sleep(1.0)
            else:
                await _broadcast_phase("finalizing", 3)

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
            completed_at = datetime.now(timezone.utc)
            await db.execute(
                """
                UPDATE recon_scans SET
                    status                = 'completed',
                    open_ports            = $1,
                    os_guess              = $2,
                    initial_access_method = $3,
                    credential_found      = $4,
                    agent_deployed        = $5,
                    facts_written         = $6,
                    completed_at          = $7
                WHERE id = $8
                """,
                open_ports_json,
                recon_result.os_guess,
                ia_result.method,
                ia_result.credential,
                ia_result.agent_deployed,
                recon_result.facts_written,
                completed_at,
                scan_id,
            )

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

            # R1: Auto-trigger OODA cycle after recon completion
            try:
                from app.services.ooda_trigger import auto_trigger_ooda
                asyncio.create_task(
                    auto_trigger_ooda(
                        op_id,
                        reason=f"recon.completed:scan-{scan_id[:8]}",
                        delay_sec=5,
                    )
                )
            except Exception as ooda_exc:
                logger.warning(
                    "Failed to auto-trigger OODA after recon: %s", ooda_exc,
                )

        except Exception as exc:
            logger.exception("Background recon scan %s failed: %s", scan_id, exc)
            try:
                await db.execute(
                    "UPDATE recon_scans SET status='failed', completed_at=$1 WHERE id=$2",
                    datetime.now(timezone.utc), scan_id,
                )
            except Exception:
                logger.exception(
                    "Failed to update recon_scan status to 'failed' for %s", scan_id
                )
            await ws_manager.broadcast(
                op_id,
                "recon.failed",
                {"scan_id": scan_id, "target_id": target_id, "error": str(exc)},
            )


def _build_scan_result(row: asyncpg.Record) -> ReconScanResult:
    """Build a ReconScanResult from a recon_scans DB row (joined with targets)."""
    open_ports = json.loads(row["open_ports"] or "[]")
    started = row["started_at"] or ""
    completed = row["completed_at"] or ""
    scan_duration = 0.0
    if started and completed:
        try:
            t_start = (started if isinstance(started, datetime) else datetime.fromisoformat(started))
            t_end = (completed if isinstance(completed, datetime) else datetime.fromisoformat(completed))
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
        facts_written=row["facts_written"] or 0,
        initial_access=InitialAccessResult(
            success=bool(row["credential_found"]),
            method=row["initial_access_method"] or "none",
            credential=row["credential_found"],
            agent_deployed=bool(row["agent_deployed"]),
            error=None,
        ),
        scan_duration_sec=round(scan_duration, 1),
    )


_SCAN_SELECT = """
    SELECT s.id, s.operation_id, s.target_id, s.status,
           s.open_ports, s.os_guess,
           s.initial_access_method, s.credential_found,
           s.agent_deployed, s.facts_written, s.started_at, s.completed_at,
           t.ip_address
    FROM recon_scans s
    JOIN targets t ON t.id = s.target_id
"""


@router.get(
    "/operations/{op_id}/recon/scans/{scan_id}",
    response_model=ReconScanResult,
)


async def get_recon_scan_result(
    op_id: str,
    scan_id: str,
    db: asyncpg.Connection = Depends(get_db),
) -> ReconScanResult:
    """Return a full ReconScanResult for a completed scan (used by frontend modal)."""
    await ensure_operation(db, op_id)

    row = await db.fetchrow(
        _SCAN_SELECT + " WHERE s.id = $1 AND s.operation_id = $2",
        scan_id, op_id,
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Scan '{scan_id}' not found in operation '{op_id}'",
        )

    return _build_scan_result(row)


@router.get(
    "/operations/{op_id}/recon/scans/by-target/{target_id}",
    response_model=ReconScanResult | None,
)


async def get_latest_scan_by_target(
    op_id: str,
    target_id: str,
    db: asyncpg.Connection = Depends(get_db),
) -> ReconScanResult | None:
    """Return the latest completed scan for a specific target."""
    await ensure_operation(db, op_id)

    row = await db.fetchrow(
        _SCAN_SELECT
        + " WHERE s.operation_id = $1 AND s.target_id = $2 AND s.status = 'completed'"
        " ORDER BY s.completed_at DESC LIMIT 1",
        op_id, target_id,
    )
    if row is None:
        return None

    return _build_scan_result(row)


class InitialAccessRequest(BaseModel):
    target_id: str
    c2_host: str | None = None


@router.post(
    "/operations/{op_id}/recon/initial-access",
    status_code=202,
)
async def run_initial_access(
    op_id: str,
    body: InitialAccessRequest,
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    """Run initial access on a target (requires a prior completed recon scan)."""
    await ensure_operation(db, op_id)

    # Validate target
    target_row = await db.fetchrow(
        "SELECT id, ip_address FROM targets WHERE id = $1 AND operation_id = $2",
        body.target_id, op_id,
    )
    if target_row is None:
        raise HTTPException(404, f"Target '{body.target_id}' not found in operation '{op_id}'")
    ip_address: str = target_row["ip_address"]

    # Require a completed scan with services
    scan_row = await db.fetchrow(
        "SELECT open_ports FROM recon_scans "
        "WHERE target_id = $1 AND operation_id = $2 AND status = 'completed' "
        "ORDER BY completed_at DESC LIMIT 1",
        body.target_id, op_id,
    )
    if scan_row is None:
        raise HTTPException(400, "No completed recon scan found -- run recon scan first")

    services_json = json.loads(scan_row["open_ports"] or "[]")
    if not services_json:
        raise HTTPException(400, "Recon scan found no open ports -- nothing to attack")

    # Launch background task
    _task = asyncio.create_task(
        _run_initial_access_background(op_id, body.target_id, ip_address, services_json, body.c2_host)
    )
    if _task is not None:
        _task.add_done_callback(
            lambda t: logger.warning("Initial access task cancelled for target %s", body.target_id)
            if t.cancelled() else None
        )

    return {"status": "queued", "target_id": body.target_id, "operation_id": op_id}


async def _run_initial_access_background(
    op_id: str,
    target_id: str,
    ip_address: str,
    services: list[dict],
    c2_host: str | None,
) -> None:
    """Background task: attempt initial access on a target using known services."""
    from app.ws_manager import ws_manager

    async with db_manager.connection() as db:
        try:
            await ws_manager.broadcast(
                op_id, "initial_access.started", {"target_id": target_id}
            )

            ia_engine = InitialAccessEngine()
            ia_result = await ia_engine.try_initial_access(
                db, op_id, target_id, ip_address, services,
            )

            # Bootstrap C2 agent for SSH success
            if (
                ia_result.success
                and ia_result.method == "ssh_credential"
                and not settings.MOCK_C2_ENGINE
            ):
                c2 = c2_host or settings.C2_AGENT_CALLBACK_URL or settings.C2_ENGINE_URL
                cred_parts = (ia_result.credential or ":").split(":", 1)
                cred_tuple = (cred_parts[0], cred_parts[1] if len(cred_parts) > 1 else "")
                deployed = await ia_engine.bootstrap_c2_agent(ip_address, cred_tuple, c2)
                ia_result = InitialAccessResult(
                    success=ia_result.success,
                    method=ia_result.method,
                    credential=ia_result.credential,
                    agent_deployed=deployed,
                    error=ia_result.error,
                )

            await ws_manager.broadcast(
                op_id,
                "initial_access.completed",
                {
                    "target_id": target_id,
                    "success": ia_result.success,
                    "method": ia_result.method,
                    "credential_found": ia_result.credential,
                    "agent_deployed": ia_result.agent_deployed,
                },
            )
        except Exception as exc:
            logger.exception("Initial access for target %s failed: %s", target_id, exc)
            await ws_manager.broadcast(
                op_id,
                "initial_access.failed",
                {"target_id": target_id, "error": str(exc)},
            )


@router.get("/operations/{op_id}/recon/status")


async def get_recon_status(
    op_id: str,
    db: asyncpg.Connection = Depends(get_db),
) -> dict:
    """Return the most recent recon scan row for this operation.

    Auto-fails scans stuck in 'running'/'queued' for more than 10 minutes.
    """

    await ensure_operation(db, op_id)

    row = await db.fetchrow(
        """
        SELECT id, operation_id, target_id, status,
               nmap_result, open_ports, os_guess,
               initial_access_method, credential_found,
               agent_deployed, started_at, completed_at
        FROM recon_scans
        WHERE operation_id = $1
        ORDER BY started_at DESC
        LIMIT 1
        """,
        op_id,
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No recon scans found for operation '{op_id}'",
        )

    result = dict(row)

    # Auto-fail stuck scans (running/queued > 10 minutes)
    if result["status"] in ("running", "queued") and result.get("started_at"):
        try:
            started = (result["started_at"] if isinstance(result["started_at"], datetime) else datetime.fromisoformat(result["started_at"]))
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            if elapsed > 600:  # 10 minutes
                now_iso = datetime.now(timezone.utc)
                await db.execute(
                    "UPDATE recon_scans SET status='failed', completed_at=$1 WHERE id=$2",
                    now_iso, result["id"],
                )
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
    db: asyncpg.Connection = Depends(get_db),
) -> OSINTDiscoverQueued:
    """Enqueue OSINT discovery -- returns 202 immediately, executes in background."""
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

    async with db_manager.connection() as db:
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

            # R1: Auto-trigger recon on newly discovered targets, then OODA
            try:
                new_targets = await db.fetch(
                    "SELECT id, ip_address FROM targets "
                    "WHERE operation_id = $1 AND is_active = TRUE "
                    "ORDER BY created_at DESC LIMIT 5",
                    op_id,
                )
                recon = ReconEngine()
                for t in new_targets:
                    if not t["ip_address"]:
                        continue
                    try:
                        await recon.scan(db, op_id, t["id"])
                    except Exception as recon_exc:
                        logger.warning(
                            "Auto-recon after OSINT failed for target %s: %s",
                            t["id"], recon_exc,
                        )
                # Trigger OODA after recon chain completes
                from app.services.ooda_trigger import auto_trigger_ooda
                asyncio.create_task(
                    auto_trigger_ooda(
                        op_id,
                        reason=f"osint.completed:{domain}",
                        delay_sec=5,
                    )
                )
            except Exception as chain_exc:
                logger.warning(
                    "OSINT->Recon->OODA chain failed: %s", chain_exc,
                )

        except Exception as exc:
            logger.exception(
                "Background OSINT discover for domain %s failed: %s", domain, exc
            )
            await ws_manager.broadcast(op_id, "osint.failed", {
                "domain": domain,
                "error": str(exc),
            })
