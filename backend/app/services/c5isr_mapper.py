"""Cross-cutting concern — aggregate C5ISR six-domain health."""

import uuid
from datetime import datetime, timezone

import aiosqlite

from app.models.enums import C5ISRDomain, C5ISRDomainStatus
from app.ws_manager import WebSocketManager


class C5ISRMapper:
    """Aggregate C5ISR six-domain health after each OODA iteration."""

    def __init__(self, ws_manager: WebSocketManager):
        self._ws = ws_manager

    async def update(self, db: aiosqlite.Connection, operation_id: str) -> list[dict]:
        """
        Six-domain aggregation per ADR-012:
        - Command:   OODA iteration progress + commander activity
        - Control:   alive_agents / total_agents * 100
        - Comms:     WebSocket assumed operational (simplified for POC)
        - Computers: non-compromised targets / total_targets * 100
        - Cyber:     successful_executions / total_executions * 100
        - ISR:       latest recommendation confidence * 100
        """
        db.row_factory = aiosqlite.Row
        results: list[dict] = []

        # Command: based on OODA iteration count
        cursor = await db.execute(
            "SELECT ooda_iteration_count FROM operations WHERE id = ?",
            (operation_id,),
        )
        op = await cursor.fetchone()
        ooda_count = op["ooda_iteration_count"] if op else 0
        command_health = min(100.0, 80.0 + ooda_count * 5.0)

        # Control: alive agents / total agents
        cursor = await db.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'alive' THEN 1 ELSE 0 END) as alive "
            "FROM agents WHERE operation_id = ?",
            (operation_id,),
        )
        agent_row = await cursor.fetchone()
        total_agents = agent_row["total"] or 0
        alive_agents = agent_row["alive"] or 0
        control_health = (alive_agents / total_agents * 100) if total_agents > 0 else 0.0

        # Comms: simplified — assume operational at 60% baseline for POC
        comms_health = 60.0

        # Computers: non-compromised targets — for red team, health drops as we compromise more
        cursor = await db.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN is_compromised = 0 THEN 1 ELSE 0 END) as secure "
            "FROM targets WHERE operation_id = ?",
            (operation_id,),
        )
        target_row = await cursor.fetchone()
        total_targets = target_row["total"] or 0
        secure_targets = target_row["secure"] or 0
        computers_health = (secure_targets / total_targets * 100) if total_targets > 0 else 0.0

        # Cyber: success rate
        cursor = await db.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success "
            "FROM technique_executions WHERE operation_id = ?",
            (operation_id,),
        )
        exec_row = await cursor.fetchone()
        total_exec = exec_row["total"] or 0
        success_exec = exec_row["success"] or 0
        cyber_health = (success_exec / total_exec * 100) if total_exec > 0 else 0.0

        # ISR: latest recommendation confidence
        cursor = await db.execute(
            "SELECT confidence FROM recommendations "
            "WHERE operation_id = ? ORDER BY created_at DESC LIMIT 1",
            (operation_id,),
        )
        rec_row = await cursor.fetchone()
        isr_health = (rec_row["confidence"] * 100) if rec_row else 0.0

        domain_values = [
            (C5ISRDomain.COMMAND, command_health, "OODA cycle active"),
            (C5ISRDomain.CONTROL, control_health, f"{alive_agents}/{total_agents} agents alive"),
            (C5ISRDomain.COMMS, comms_health, "WebSocket channel active"),
            (C5ISRDomain.COMPUTERS, computers_health, f"{secure_targets}/{total_targets} targets secure"),
            (C5ISRDomain.CYBER, cyber_health, f"{success_exec}/{total_exec} executions successful"),
            (C5ISRDomain.ISR, isr_health, "PentestGPT intelligence confidence"),
        ]

        now = datetime.now(timezone.utc).isoformat()
        for domain, health, detail in domain_values:
            status = self._health_to_status(health)
            # Upsert
            cursor = await db.execute(
                "SELECT id FROM c5isr_statuses WHERE operation_id = ? AND domain = ?",
                (operation_id, domain.value),
            )
            existing = await cursor.fetchone()
            if existing:
                await db.execute(
                    "UPDATE c5isr_statuses SET status = ?, health_pct = ?, "
                    "detail = ?, updated_at = ? WHERE id = ?",
                    (status.value, round(health, 1), detail, now, existing["id"]),
                )
                row_id = existing["id"]
            else:
                row_id = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO c5isr_statuses "
                    "(id, operation_id, domain, status, health_pct, detail, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (row_id, operation_id, domain.value, status.value,
                     round(health, 1), detail, now),
                )

            result = {
                "id": row_id, "operation_id": operation_id,
                "domain": domain.value, "status": status.value,
                "health_pct": round(health, 1), "detail": detail,
            }
            results.append(result)

        await db.commit()
        await self._ws.broadcast(operation_id, "c5isr.update", {"domains": results})
        return results

    @staticmethod
    def _health_to_status(health_pct: float) -> C5ISRDomainStatus:
        if health_pct >= 95:
            return C5ISRDomainStatus.OPERATIONAL
        if health_pct >= 85:
            return C5ISRDomainStatus.ACTIVE
        if health_pct >= 75:
            return C5ISRDomainStatus.NOMINAL
        if health_pct >= 65:
            return C5ISRDomainStatus.ENGAGED
        if health_pct >= 50:
            return C5ISRDomainStatus.SCANNING
        if health_pct >= 30:
            return C5ISRDomainStatus.DEGRADED
        if health_pct >= 1:
            return C5ISRDomainStatus.OFFLINE
        return C5ISRDomainStatus.CRITICAL
