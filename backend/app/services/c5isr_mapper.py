# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Cross-cutting concern — aggregate C5ISR six-domain health."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum

import asyncpg

from app.models.enums import C5ISRDomain, C5ISRDomainStatus
from app.ws_manager import WebSocketManager


# ---------------------------------------------------------------------------
#  Data structures (SPEC-038)
# ---------------------------------------------------------------------------

class RiskSeverity(str, Enum):
    CRIT = "CRIT"
    WARN = "WARN"
    INFO = "INFO"


@dataclass
class DomainMetric:
    """Single weighted metric."""
    name: str                # e.g. "decision_throughput"
    value: float             # 0.0-100.0
    weight: float            # 0.0-1.0
    numerator: int | None = None
    denominator: int | None = None


@dataclass
class RiskVector:
    """Risk item."""
    severity: RiskSeverity   # CRIT / WARN / INFO
    message: str


@dataclass
class DomainReport:
    """Structured domain assessment report."""
    executive_summary: str
    health_pct: float
    status: str                          # C5ISRDomainStatus.value
    metrics: list[DomainMetric] = field(default_factory=list)
    asset_roster: list[dict] = field(default_factory=list)
    tactical_assessment: str = ""
    risk_vectors: list[RiskVector] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    cross_domain_impacts: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to JSON string (stored in DB detail column)."""
        def _default(o: object) -> object:
            if isinstance(o, datetime):
                return o.isoformat()
            raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")
        return json.dumps(asdict(self), ensure_ascii=False, default=_default)

    @classmethod
    def from_json(cls, raw: str) -> "DomainReport":
        """Deserialize from JSON string. Returns empty report on corruption."""
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return cls(executive_summary="", health_pct=0.0, status="critical")
        data["metrics"] = [DomainMetric(**m) for m in data.get("metrics", [])]
        data["risk_vectors"] = [RiskVector(**r) for r in data.get("risk_vectors", [])]
        return cls(**data)


# Kill chain stage -> score mapping
_KILLCHAIN_SCORES = {
    "recon": 20, "weaponize": 30, "deliver": 40,
    "exploit": 50, "install": 70, "c2": 85, "action": 100,
}


class C5ISRMapper:
    """Aggregate C5ISR six-domain health after each OODA iteration."""

    def __init__(self, ws_manager: WebSocketManager):
        self._ws = ws_manager

    # ------------------------------------------------------------------
    #  _build_command_report
    # ------------------------------------------------------------------
    async def _build_command_report(
        self, db: asyncpg.Connection, operation_id: str,
    ) -> DomainReport:
        risks: list[RiskVector] = []
        actions: list[str] = []
        cross: list[str] = []

        # Decision throughput
        op = await db.fetchrow(
            "SELECT ooda_iteration_count, max_iterations FROM operations WHERE id = $1",
            operation_id,
        )
        ooda_count = op["ooda_iteration_count"] if op else 0
        expected = (op["max_iterations"] if op and op["max_iterations"] else 20)
        dt_value = min(100.0, ooda_count / max(1, expected) * 100)

        # Stall penalty: check last 3 recommendations
        rec_rows = await db.fetch(
            "SELECT created_at FROM recommendations "
            "WHERE operation_id = $1 ORDER BY created_at DESC LIMIT 3",
            operation_id,
        )
        if rec_rows and ooda_count > 0:
            oldest_ts = rec_rows[-1]["created_at"]
            try:
                oldest_dt = (oldest_ts if isinstance(oldest_ts, datetime) else datetime.fromisoformat(oldest_ts))
                if oldest_dt.tzinfo is None:
                    oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
                stall_threshold = ooda_count * 30 * 3  # seconds
                elapsed = (datetime.now(timezone.utc) - oldest_dt).total_seconds()
                if elapsed > stall_threshold:
                    dt_value = max(0.0, dt_value - 20)
                    risks.append(RiskVector(
                        severity=RiskSeverity.WARN,
                        message="Decision stall detected: no new recommendations in 3+ iteration cycles",
                    ))
            except (ValueError, TypeError):
                pass

        # Acceptance rate
        rec_row = await db.fetchrow(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN accepted = TRUE THEN 1 ELSE 0 END) as accepted "
            "FROM recommendations WHERE operation_id = $1",
            operation_id,
        )
        total_recs = rec_row["total"] or 0
        accepted_recs = rec_row["accepted"] or 0
        if total_recs > 0:
            ar_value = accepted_recs / total_recs * 100
        else:
            ar_value = 50.0  # baseline

        # Directive consumption
        dir_row = await db.fetchrow(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN consumed_at IS NOT NULL THEN 1 ELSE 0 END) as consumed "
            "FROM ooda_directives WHERE operation_id = $1",
            operation_id,
        )
        total_dirs = dir_row["total"] or 0
        consumed_dirs = dir_row["consumed"] or 0
        if total_dirs > 0:
            dc_value = consumed_dirs / total_dirs * 100
        else:
            dc_value = 100.0  # no directives = 100%

        if total_dirs > 0 and dc_value < 70:
            risks.append(RiskVector(
                severity=RiskSeverity.WARN,
                message=f"Directive consumption rate {dc_value:.0f}% below 70% threshold",
            ))
            actions.append("Review unconsumed directives and confirm their relevance")

        if ooda_count == 0:
            actions.append("Trigger first OODA iteration to begin decision cycle")

        cross.append("ISR: decision throughput affects intelligence collection depth")
        cross.append("Control: acceptance rate affects agent dispatch frequency")

        metrics = [
            DomainMetric("decision_throughput", round(dt_value, 1), 0.40, ooda_count, expected),
            DomainMetric("acceptance_rate", round(ar_value, 1), 0.35, accepted_recs, total_recs if total_recs > 0 else None),
            DomainMetric("directive_consumption", round(dc_value, 1), 0.25, consumed_dirs, total_dirs if total_dirs > 0 else None),
        ]

        health = round(sum(m.value * m.weight for m in metrics), 1)
        status = self._health_to_status(health)

        summary_parts = []
        summary_parts.append(f"OODA iteration {ooda_count}/{expected}")
        if total_recs > 0:
            summary_parts.append(f"acceptance rate {ar_value:.0f}%")
        else:
            summary_parts.append("no recommendations yet")
        executive = ", ".join(summary_parts)

        tactical = (
            f"OODA cycle at iteration {ooda_count} of {expected}. "
            f"Directive consumption at {dc_value:.0f}%. "
            + ("Recommendation pipeline active." if total_recs > 0 else "Awaiting first OODA iteration.")
        )

        # Asset roster: ooda_directives
        directive_rows = await db.fetch(
            "SELECT id, directive, consumed_at FROM ooda_directives WHERE operation_id = $1",
            operation_id,
        )
        roster = [
            {
                "type": "directive",
                "id": r["id"],
                "directive": (r["directive"] or "")[:80],
                "status": "consumed" if r["consumed_at"] else "pending",
            }
            for r in directive_rows
        ]

        return DomainReport(
            executive_summary=executive,
            health_pct=health,
            status=status.value,
            metrics=metrics,
            asset_roster=roster,
            tactical_assessment=tactical,
            risk_vectors=risks,
            recommended_actions=actions,
            cross_domain_impacts=cross,
        )

    # ------------------------------------------------------------------
    #  _build_control_report
    # ------------------------------------------------------------------
    async def _build_control_report(
        self, db: asyncpg.Connection, operation_id: str,
    ) -> DomainReport:
        risks: list[RiskVector] = []
        actions: list[str] = []
        cross: list[str] = []

        # Agent liveness
        agent_row = await db.fetchrow(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'alive' THEN 1 ELSE 0 END) as alive "
            "FROM agents WHERE operation_id = $1",
            operation_id,
        )
        total_agents = agent_row["total"] or 0
        alive_agents = agent_row["alive"] or 0
        al_value = (alive_agents / total_agents * 100) if total_agents > 0 else 0.0

        # Access stability
        access_row = await db.fetchrow(
            "SELECT SUM(CASE WHEN access_status = 'active' THEN 1 ELSE 0 END) as active_count, "
            "SUM(CASE WHEN access_status IN ('active', 'lost') THEN 1 ELSE 0 END) as total_accessed "
            "FROM targets WHERE operation_id = $1",
            operation_id,
        )
        active_count = access_row["active_count"] or 0
        total_accessed = access_row["total_accessed"] or 0
        as_value = (active_count / total_accessed * 100) if total_accessed > 0 else 0.0

        # Beacon freshness
        beacon_rows = await db.fetch(
            "SELECT last_beacon FROM agents "
            "WHERE operation_id = $1 AND status = 'alive' AND last_beacon IS NOT NULL",
            operation_id,
        )
        now = datetime.now(timezone.utc)
        if beacon_rows:
            staleness_values = []
            stale_count = 0
            for row in beacon_rows:
                try:
                    beacon_dt = (row["last_beacon"] if isinstance(row["last_beacon"], datetime) else datetime.fromisoformat(row["last_beacon"]))
                    if beacon_dt.tzinfo is None:
                        beacon_dt = beacon_dt.replace(tzinfo=timezone.utc)
                    staleness_sec = (now - beacon_dt).total_seconds()
                    staleness_values.append(staleness_sec)
                    if staleness_sec > 300:
                        stale_count += 1
                except (ValueError, TypeError):
                    pass
            if staleness_values:
                avg_staleness = sum(staleness_values) / len(staleness_values)
                bf_value = max(0.0, 100 - avg_staleness / 60 * 10)
                # Stale beacon penalty
                bf_value = max(0.0, bf_value - stale_count * 5)
            else:
                bf_value = 0.0
        else:
            bf_value = 0.0

        if total_agents == 0:
            risks.append(RiskVector(severity=RiskSeverity.CRIT, message="No agents deployed"))
            actions.append("Deploy agents to establish control")

        if total_agents > 0 and alive_agents < total_agents:
            dead = total_agents - alive_agents
            risks.append(RiskVector(
                severity=RiskSeverity.WARN,
                message=f"{dead} agent(s) not alive",
            ))

        cross.append("Comms: agent beacons depend on C2 channel availability")
        cross.append("Computers: agent liveness required for technique execution")

        metrics = [
            DomainMetric("agent_liveness", round(al_value, 1), 0.50, alive_agents, total_agents if total_agents > 0 else None),
            DomainMetric("access_stability", round(as_value, 1), 0.30, active_count, total_accessed if total_accessed > 0 else None),
            DomainMetric("beacon_freshness", round(bf_value, 1), 0.20),
        ]

        health = round(sum(m.value * m.weight for m in metrics), 1)
        status = self._health_to_status(health)

        executive = f"{alive_agents}/{total_agents} agents alive, access stability {as_value:.0f}%"

        tactical = (
            f"Agent pool: {alive_agents} alive of {total_agents} total. "
            f"Access stability at {as_value:.0f}%. "
            f"Beacon freshness at {bf_value:.0f}%."
        )

        # Asset roster: agents
        agent_rows = await db.fetch(
            "SELECT paw, status, host_id, last_beacon, privilege FROM agents WHERE operation_id = $1",
            operation_id,
        )
        roster = [
            {
                "type": "agent",
                "paw": r["paw"],
                "status": r["status"],
                "host_id": r["host_id"],
                "last_beacon": r["last_beacon"],
                "privilege": r["privilege"],
            }
            for r in agent_rows
        ]

        return DomainReport(
            executive_summary=executive,
            health_pct=health,
            status=status.value,
            metrics=metrics,
            asset_roster=roster,
            tactical_assessment=tactical,
            risk_vectors=risks,
            recommended_actions=actions,
            cross_domain_impacts=cross,
        )

    # ------------------------------------------------------------------
    #  _build_comms_report
    # ------------------------------------------------------------------
    async def _build_comms_report(
        self, db: asyncpg.Connection, operation_id: str,
    ) -> DomainReport:
        risks: list[RiskVector] = []
        actions: list[str] = []
        cross: list[str] = []

        # WebSocket connections
        ws_count = self._ws.active_connection_count()
        ws_value = min(100.0, ws_count * 50)  # 2+ connections = 100%

        # MCP availability
        tool_row = await db.fetchrow(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN enabled = TRUE THEN 1 ELSE 0 END) as enabled_count "
            "FROM tool_registry WHERE kind = 'tool'",
        )
        total_tools = tool_row["total"] or 0
        enabled_tools = tool_row["enabled_count"] or 0
        mcp_value = (enabled_tools / total_tools * 100) if total_tools > 0 else 0.0

        # Broadcast success
        bt = self._ws._broadcast_total
        bs = self._ws._broadcast_success
        if bt == 0:
            bc_value = 100.0  # no failures = assume success
        else:
            bc_value = bs / bt * 100

        if ws_count == 0:
            risks.append(RiskVector(
                severity=RiskSeverity.WARN,
                message="No active WebSocket connections (headless mode)",
            ))
        if total_tools > 0 and enabled_tools < total_tools:
            disabled = total_tools - enabled_tools
            risks.append(RiskVector(
                severity=RiskSeverity.INFO,
                message=f"{disabled} MCP tool(s) disabled",
            ))

        cross.append("Control: C2 channel affects agent beacon reliability")
        cross.append("Cyber: MCP tool availability affects technique execution options")

        metrics = [
            DomainMetric("ws_connections", round(ws_value, 1), 0.40, ws_count, 2),
            DomainMetric("mcp_availability", round(mcp_value, 1), 0.30, enabled_tools, total_tools if total_tools > 0 else None),
            DomainMetric("broadcast_success", round(bc_value, 1), 0.30, bs, bt if bt > 0 else None),
        ]

        health = round(sum(m.value * m.weight for m in metrics), 1)
        status = self._health_to_status(health)

        executive = f"WS connections: {ws_count}, MCP tools: {enabled_tools}/{total_tools}"

        tactical = (
            f"WebSocket connections: {ws_count}. "
            f"MCP tool availability: {enabled_tools}/{total_tools}. "
            f"Broadcast success rate: {bc_value:.0f}%."
        )

        # Asset roster: enabled MCP tools
        tool_rows = await db.fetch(
            "SELECT id, tool_id, name, enabled FROM tool_registry WHERE kind = 'tool'",
        )
        roster = [
            {
                "type": "mcp_tool",
                "tool_id": r["tool_id"],
                "name": r["name"],
                "enabled": bool(r["enabled"]),
            }
            for r in tool_rows
        ]

        return DomainReport(
            executive_summary=executive,
            health_pct=health,
            status=status.value,
            metrics=metrics,
            asset_roster=roster,
            tactical_assessment=tactical,
            risk_vectors=risks,
            recommended_actions=actions,
            cross_domain_impacts=cross,
        )

    # ------------------------------------------------------------------
    #  _build_computers_report
    # ------------------------------------------------------------------
    async def _build_computers_report(
        self, db: asyncpg.Connection, operation_id: str,
    ) -> DomainReport:
        risks: list[RiskVector] = []
        actions: list[str] = []
        cross: list[str] = []

        # Compromise rate + privilege depth
        target_row = await db.fetchrow(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN is_compromised = TRUE THEN 1 ELSE 0 END) as compromised, "
            "SUM(CASE WHEN is_compromised = TRUE AND privilege_level = 'Root' THEN 1 ELSE 0 END) as root_count "
            "FROM targets WHERE operation_id = $1",
            operation_id,
        )
        total_targets = target_row["total"] or 0
        compromised = target_row["compromised"] or 0
        root_count = target_row["root_count"] or 0

        cr_value = (compromised / total_targets * 100) if total_targets > 0 else 0.0
        pd_value = (root_count / max(1, compromised) * 100)

        # Kill chain advancement
        kc_rows = await db.fetch(
            "SELECT DISTINCT t.kill_chain_stage "
            "FROM technique_executions te "
            "JOIN techniques t ON te.technique_id = t.mitre_id "
            "WHERE te.operation_id = $1 AND te.status = 'success'",
            operation_id,
        )
        kc_score = 0
        for row in kc_rows:
            stage = row["kill_chain_stage"]
            if stage in _KILLCHAIN_SCORES:
                kc_score = max(kc_score, _KILLCHAIN_SCORES[stage])

        if total_targets > 0 and compromised == total_targets and root_count == total_targets:
            risks.append(RiskVector(
                severity=RiskSeverity.INFO,
                message="All targets fully controlled, consider expanding attack surface",
            ))

        if total_targets == 0:
            actions.append("Add target hosts to begin engagement")

        cross.append("Control: compromised targets enable agent deployment")
        cross.append("Cyber: kill chain advancement drives technique selection")

        metrics = [
            DomainMetric("compromise_rate", round(cr_value, 1), 0.40, compromised, total_targets if total_targets > 0 else None),
            DomainMetric("privilege_depth", round(pd_value, 1), 0.35, root_count, compromised if compromised > 0 else None),
            DomainMetric("killchain_advancement", float(kc_score), 0.25),
        ]

        health = round(sum(m.value * m.weight for m in metrics), 1)
        status = self._health_to_status(health)

        executive = f"{compromised}/{total_targets} targets pwned, {root_count} root"

        tactical = (
            f"Compromise rate: {compromised}/{total_targets}. "
            f"Root access: {root_count}. "
            f"Kill chain highest stage score: {kc_score}."
        )

        # Asset roster: targets
        t_rows = await db.fetch(
            "SELECT hostname, ip_address, is_compromised, privilege_level, access_status "
            "FROM targets WHERE operation_id = $1",
            operation_id,
        )
        roster = [
            {
                "type": "target",
                "hostname": r["hostname"],
                "ip_address": r["ip_address"],
                "is_compromised": bool(r["is_compromised"]),
                "privilege_level": r["privilege_level"],
                "access_status": r["access_status"],
            }
            for r in t_rows
        ]

        return DomainReport(
            executive_summary=executive,
            health_pct=health,
            status=status.value,
            metrics=metrics,
            asset_roster=roster,
            tactical_assessment=tactical,
            risk_vectors=risks,
            recommended_actions=actions,
            cross_domain_impacts=cross,
        )

    # ------------------------------------------------------------------
    #  _build_cyber_report
    # ------------------------------------------------------------------
    async def _build_cyber_report(
        self, db: asyncpg.Connection, operation_id: str,
    ) -> DomainReport:
        risks: list[RiskVector] = []
        actions: list[str] = []
        cross: list[str] = []

        # Category stats: recon vs exploit
        cat_rows = await db.fetch(
            "SELECT "
            "CASE WHEN t.tactic IN ('Reconnaissance', 'Discovery') THEN 'recon' ELSE 'exploit' END as category, "
            "COUNT(*) as total, "
            "SUM(CASE WHEN te.status = 'success' THEN 1 ELSE 0 END) as success "
            "FROM technique_executions te "
            "LEFT JOIN techniques t ON te.technique_id = t.mitre_id "
            "WHERE te.operation_id = $1 "
            "GROUP BY category",
            operation_id,
        )
        recon_total = recon_success = 0
        exploit_total = exploit_success = 0
        for row in cat_rows:
            cat = row["category"]
            if cat == "recon":
                recon_total = row["total"] or 0
                recon_success = row["success"] or 0
            else:
                exploit_total = row["total"] or 0
                exploit_success = row["success"] or 0

        rs_value = (recon_success / recon_total * 100) if recon_total > 0 else 0.0
        es_value = (exploit_success / exploit_total * 100) if exploit_total > 0 else 0.0

        # Overall success rate
        overall_row = await db.fetchrow(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success "
            "FROM technique_executions WHERE operation_id = $1",
            operation_id,
        )
        overall_total = overall_row["total"] or 0
        overall_success = overall_row["success"] or 0
        overall_rate = (overall_success / overall_total) if overall_total > 0 else 0.0

        # Recent 5 trend
        recent_rows = await db.fetch(
            "SELECT status FROM technique_executions "
            "WHERE operation_id = $1 ORDER BY created_at DESC LIMIT 5",
            operation_id,
        )
        if recent_rows:
            recent_success = sum(1 for r in recent_rows if r["status"] == "success")
            recent_rate = recent_success / len(recent_rows)
        else:
            recent_rate = 0.0

        # Trend calculation
        if overall_total > 0:
            base = overall_rate * 100
            delta = (recent_rate - overall_rate) * 100
            rt_value = max(0.0, min(100.0, base + delta))
            # Declining trend detection
            if recent_rate < overall_rate - 0.20:
                rt_value = 0.0
                risks.append(RiskVector(
                    severity=RiskSeverity.WARN,
                    message="Declining success trend: recent success rate 20%+ below overall",
                ))
        else:
            rt_value = 0.0

        cross.append("Computers: exploit success drives compromise rate")
        cross.append("ISR: recon success feeds intelligence collection")

        metrics = [
            DomainMetric("recon_success", round(rs_value, 1), 0.25, recon_success, recon_total if recon_total > 0 else None),
            DomainMetric("exploit_success", round(es_value, 1), 0.45, exploit_success, exploit_total if exploit_total > 0 else None),
            DomainMetric("recent_trend", round(rt_value, 1), 0.30),
        ]

        health = round(sum(m.value * m.weight for m in metrics), 1)
        status = self._health_to_status(health)

        total_exec = recon_total + exploit_total
        total_success = recon_success + exploit_success
        executive = f"{total_success}/{total_exec} attacks succeeded"

        tactical = (
            f"Recon success: {recon_success}/{recon_total}. "
            f"Exploit success: {exploit_success}/{exploit_total}. "
            f"Recent trend: {'declining' if rt_value == 0 and overall_total > 0 else 'stable'}."
        )

        return DomainReport(
            executive_summary=executive,
            health_pct=health,
            status=status.value,
            metrics=metrics,
            asset_roster=[],
            tactical_assessment=tactical,
            risk_vectors=risks,
            recommended_actions=actions,
            cross_domain_impacts=cross,
        )

    # ------------------------------------------------------------------
    #  _build_isr_report
    # ------------------------------------------------------------------
    async def _build_isr_report(
        self, db: asyncpg.Connection, operation_id: str,
    ) -> DomainReport:
        risks: list[RiskVector] = []
        actions: list[str] = []
        cross: list[str] = []

        # Confidence trend: average of last 5 recommendations
        conf_rows = await db.fetch(
            "SELECT confidence FROM recommendations "
            "WHERE operation_id = $1 ORDER BY created_at DESC LIMIT 5",
            operation_id,
        )
        if conf_rows:
            avg_conf = sum(r["confidence"] for r in conf_rows) / len(conf_rows)
            ct_value = avg_conf * 100
        else:
            ct_value = 0.0

        # Fact coverage: distinct categories / 7
        fact_row = await db.fetchrow(
            "SELECT COUNT(DISTINCT category) as distinct_categories "
            "FROM facts WHERE operation_id = $1",
            operation_id,
        )
        distinct_cats = fact_row["distinct_categories"] or 0
        fc_value = distinct_cats / 7 * 100

        # Graph coverage
        graph_row = await db.fetchrow(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status IN ('reachable', 'completed') THEN 1 ELSE 0 END) as covered "
            "FROM attack_graph_nodes WHERE operation_id = $1",
            operation_id,
        )
        total_nodes = graph_row["total"] or 0
        covered_nodes = graph_row["covered"] or 0
        gc_value = (covered_nodes / total_nodes * 100) if total_nodes > 0 else 0.0

        if distinct_cats < 3:
            risks.append(RiskVector(
                severity=RiskSeverity.INFO,
                message=f"Low fact diversity: only {distinct_cats}/7 categories covered",
            ))
            actions.append("Expand reconnaissance to cover more fact categories")

        cross.append("Command: intelligence quality affects decision confidence")
        cross.append("Cyber: fact coverage informs technique selection")

        metrics = [
            DomainMetric("confidence_trend", round(ct_value, 1), 0.35),
            DomainMetric("fact_coverage", round(fc_value, 1), 0.35, distinct_cats, 7),
            DomainMetric("graph_coverage", round(gc_value, 1), 0.30, covered_nodes, total_nodes if total_nodes > 0 else None),
        ]

        health = round(sum(m.value * m.weight for m in metrics), 1)
        status = self._health_to_status(health)

        executive = f"Intel confidence {ct_value:.0f}%, {distinct_cats}/7 categories covered"

        tactical = (
            f"Confidence trend: {ct_value:.0f}%. "
            f"Fact coverage: {distinct_cats}/7 categories. "
            f"Graph coverage: {covered_nodes}/{total_nodes} nodes reachable/completed."
        )

        # Asset roster: last 10 facts
        fact_rows = await db.fetch(
            "SELECT trait, value, category, collected_at FROM facts "
            "WHERE operation_id = $1 ORDER BY collected_at DESC LIMIT 10",
            operation_id,
        )
        roster = [
            {
                "type": "fact",
                "trait": r["trait"],
                "value": (r["value"] or "")[:60],
                "category": r["category"],
                "collected_at": r["collected_at"],
            }
            for r in fact_rows
        ]

        return DomainReport(
            executive_summary=executive,
            health_pct=health,
            status=status.value,
            metrics=metrics,
            asset_roster=roster,
            tactical_assessment=tactical,
            risk_vectors=risks,
            recommended_actions=actions,
            cross_domain_impacts=cross,
        )

    # ------------------------------------------------------------------
    #  update (main entry point)
    # ------------------------------------------------------------------
    async def update(self, db: asyncpg.Connection, operation_id: str) -> list[dict]:
        """
        Six-domain aggregation per ADR-012 / SPEC-038:
        Each domain produces a structured DomainReport with weighted metrics.
        """
        results: list[dict] = []

        reports = {
            C5ISRDomain.COMMAND: await self._build_command_report(db, operation_id),
            C5ISRDomain.CONTROL: await self._build_control_report(db, operation_id),
            C5ISRDomain.COMMS: await self._build_comms_report(db, operation_id),
            C5ISRDomain.COMPUTERS: await self._build_computers_report(db, operation_id),
            C5ISRDomain.CYBER: await self._build_cyber_report(db, operation_id),
            C5ISRDomain.ISR: await self._build_isr_report(db, operation_id),
        }

        # SPEC-048: Apply OPSEC cross-domain penalty to all C5ISR health values
        from app.services.opsec_monitor import compute_opsec_penalty, compute_status

        try:
            opsec_st = await compute_status(db, operation_id)
            opsec_multiplier = compute_opsec_penalty(opsec_st.detection_risk)
        except Exception:
            opsec_multiplier = 1.0  # graceful degradation

        now = datetime.now(timezone.utc)
        for domain, report in reports.items():
            health = report.health_pct * opsec_multiplier
            status = self._health_to_status(health)

            # Use first metric for backward-compatible numerator/denominator
            first_metric = report.metrics[0] if report.metrics else None
            numerator = first_metric.numerator if first_metric else None
            denominator = first_metric.denominator if first_metric else None
            metric_label = first_metric.name if first_metric else ""

            detail_json = report.to_json()

            # Upsert
            existing = await db.fetchrow(
                "SELECT id FROM c5isr_statuses WHERE operation_id = $1 AND domain = $2",
                operation_id, domain.value,
            )
            if existing:
                await db.execute(
                    "UPDATE c5isr_statuses SET status = $1, health_pct = $2, "
                    "detail = $3, numerator = $4, denominator = $5, metric_label = $6, "
                    "updated_at = $7 WHERE id = $8",
                    status.value, round(health, 1), detail_json,
                    numerator, denominator, metric_label, now, existing["id"],
                )
                row_id = existing["id"]
            else:
                row_id = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO c5isr_statuses "
                    "(id, operation_id, domain, status, health_pct, detail, "
                    "numerator, denominator, metric_label, updated_at) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
                    row_id, operation_id, domain.value, status.value,
                    round(health, 1), detail_json, numerator, denominator,
                    metric_label, now,
                )

            # SPEC-047: Record history for time-series analysis
            hist_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO c5isr_status_history "
                "(id, operation_id, domain, health_pct, status, metrics) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                hist_id, operation_id, domain.value, round(health, 1),
                status.value, detail_json,
            )

            result = {
                "id": row_id, "operation_id": operation_id,
                "domain": domain.value, "status": status.value,
                "health_pct": round(health, 1),
                "detail": report.executive_summary,
                "numerator": numerator, "denominator": denominator,
                "metric_label": metric_label,
                "report": asdict(report),
            }
            results.append(result)

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
