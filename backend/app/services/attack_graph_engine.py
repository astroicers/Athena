# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Attack graph engine — deterministic prerequisite-rule-based graph construction.

SPEC-031: Builds and maintains an in-memory attack graph from targets, facts,
and technique executions. Uses Dijkstra for recommended path, DFS for cycle
detection, and dead-branch pruning for failed techniques.

No external dependencies (no networkx). Uses stdlib: heapq, collections, uuid.
"""

import heapq
import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone

import aiosqlite

from app.models.attack_graph import (
    AttackEdge,
    AttackGraph,
    AttackNode,
    EdgeRelationship,
    NodeStatus,
    TechniqueRule,
)
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prerequisite Rule Registry — deterministic attack technique rules
# ---------------------------------------------------------------------------

_PREREQUISITE_RULES: list[TechniqueRule] = [
    TechniqueRule(
        technique_id="T1595.001", tactic_id="TA0043",
        required_facts=[], produced_facts=["network.host.ip", "service.open_port"],
        risk_level="low", base_confidence=0.95, information_gain=0.9, effort=1,
        enables=["T1595.002", "T1190", "T1110.001"], alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1595.002", tactic_id="TA0043",
        required_facts=["network.host.ip"], produced_facts=["vuln.cve"],
        risk_level="low", base_confidence=0.85, information_gain=0.8, effort=1,
        enables=["T1190"], alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1190", tactic_id="TA0001",
        required_facts=["service.open_port"], produced_facts=["service.web"],
        risk_level="medium", base_confidence=0.6, information_gain=0.7, effort=2,
        enables=["T1059.004"], alternatives=["T1110.001"],
    ),
    TechniqueRule(
        technique_id="T1110.001", tactic_id="TA0001",
        required_facts=["service.open_port"], produced_facts=["credential.ssh"],
        risk_level="medium", base_confidence=0.7, information_gain=0.6, effort=1,
        enables=["T1059.004", "T1078.001"], alternatives=["T1190"],
    ),
    TechniqueRule(
        technique_id="T1059.004", tactic_id="TA0002",
        required_facts=["credential.ssh"],
        produced_facts=["host.os", "host.user", "host.process"],
        risk_level="medium", base_confidence=0.85, information_gain=0.5, effort=1,
        enables=["T1003.001", "T1087", "T1083", "T1046"], alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1003.001", tactic_id="TA0006",
        required_facts=["credential.ssh", "host.user"],
        produced_facts=["credential.hash"],
        risk_level="high", base_confidence=0.75, information_gain=0.9, effort=1,
        enables=["T1021.004", "T1558.003"], alternatives=["T1003.003"],
    ),
    TechniqueRule(
        technique_id="T1087", tactic_id="TA0007",
        required_facts=["credential.ssh"], produced_facts=["host.user"],
        risk_level="low", base_confidence=0.9, information_gain=0.4, effort=1,
        enables=["T1078.001"], alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1083", tactic_id="TA0007",
        required_facts=["credential.ssh"], produced_facts=["host.file"],
        risk_level="low", base_confidence=0.9, information_gain=0.3, effort=1,
        enables=[], alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1046", tactic_id="TA0007",
        required_facts=["credential.ssh"], produced_facts=["service.open_port"],
        risk_level="low", base_confidence=0.9, information_gain=0.5, effort=1,
        enables=["T1021.004"], alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1021.004", tactic_id="TA0008",
        required_facts=["credential.ssh", "network.host.ip"],
        produced_facts=["host.session"],
        risk_level="medium", base_confidence=0.65, information_gain=0.8, effort=2,
        enables=["T1059.004"], alternatives=["T1021.001"],
    ),
    TechniqueRule(
        technique_id="T1053.003", tactic_id="TA0003",
        required_facts=["credential.ssh", "host.os"],
        produced_facts=["host.persistence"],
        risk_level="medium", base_confidence=0.7, information_gain=0.2, effort=1,
        enables=[], alternatives=["T1543.002"],
    ),
    TechniqueRule(
        technique_id="T1560.001", tactic_id="TA0009",
        required_facts=["credential.ssh", "host.file"],
        produced_facts=["host.file"],
        risk_level="medium", base_confidence=0.8, information_gain=0.3, effort=1,
        enables=["T1105"], alternatives=[],
    ),
    TechniqueRule(
        technique_id="T1105", tactic_id="TA0011",
        required_facts=["credential.ssh", "host.binary"],
        produced_facts=["host.binary"],
        risk_level="medium", base_confidence=0.75, information_gain=0.2, effort=1,
        enables=[], alternatives=[],
    ),
]

# Lookup maps for O(1) access
_RULE_BY_TECHNIQUE: dict[str, TechniqueRule] = {r.technique_id: r for r in _PREREQUISITE_RULES}

# Kill-chain tactic order for depth calculation
_TACTIC_ORDER = [
    "TA0043", "TA0042", "TA0001", "TA0002", "TA0003", "TA0004",
    "TA0005", "TA0006", "TA0007", "TA0008", "TA0009", "TA0011",
    "TA0010", "TA0040",
]
_TACTIC_DEPTH: dict[str, int] = {t: i for i, t in enumerate(_TACTIC_ORDER)}

_TACTIC_NAMES: dict[str, str] = {
    "TA0043": "Reconnaissance", "TA0042": "Resource Development",
    "TA0001": "Initial Access", "TA0002": "Execution",
    "TA0003": "Persistence", "TA0004": "Privilege Escalation",
    "TA0005": "Defense Evasion", "TA0006": "Credential Access",
    "TA0007": "Discovery", "TA0008": "Lateral Movement",
    "TA0009": "Collection", "TA0011": "Command and Control",
    "TA0010": "Exfiltration", "TA0040": "Impact",
}


class AttackGraphEngine:
    """Deterministic attack graph engine — SPEC-031."""

    def __init__(self, ws_manager: WebSocketManager):
        self._ws = ws_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def rebuild(
        self, db: aiosqlite.Connection, operation_id: str
    ) -> AttackGraph:
        """Full rebuild: query DB, build graph, persist, broadcast."""
        # 1. Query data
        targets = await self._query_targets(db, operation_id)
        facts = await self._query_facts(db, operation_id)
        executions = await self._query_executions(db, operation_id)

        # 2. Clear old graph data
        await db.execute(
            "DELETE FROM attack_graph_edges WHERE operation_id = ?",
            (operation_id,),
        )
        await db.execute(
            "DELETE FROM attack_graph_nodes WHERE operation_id = ?",
            (operation_id,),
        )
        await db.commit()

        # 3. Build in-memory graph
        graph = self._build_graph_in_memory(operation_id, targets, facts, executions)

        # 4. Persist to DB
        await self._persist_graph(db, graph)

        # 5. Broadcast WebSocket event
        try:
            explored = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.EXPLORED)
            pending = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.PENDING)
            await self._ws.broadcast(operation_id, "graph.updated", {
                "operation_id": operation_id,
                "graph_id": graph.graph_id,
                "stats": {
                    "total_nodes": len(graph.nodes),
                    "explored_nodes": explored,
                    "pending_nodes": pending,
                    "coverage_score": graph.coverage_score,
                },
                "updated_at": graph.updated_at,
            })
        except Exception:
            pass  # fire-and-forget

        return graph

    async def get_graph(
        self, db, operation_id: str,
    ) -> AttackGraph | None:
        """Load persisted graph from SQLite. Returns None if no graph exists."""
        return await self.load_from_db(db, operation_id)

    def build_orient_summary(self, graph: AttackGraph) -> str:
        """Build a human-readable summary for the Orient phase prompt.

        Format follows ADR-028 Section 10 specification.
        """
        if not graph.nodes:
            return "Attack graph: empty (no nodes generated)."

        total = len(graph.nodes)
        explored = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.EXPLORED)
        pending = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.PENDING)
        failed = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.FAILED)
        pruned = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.PRUNED)

        lines = [
            f"Graph coverage: {graph.coverage_score * 100:.0f}% ({explored}/{total} nodes explored)",
        ]

        # Recommended path with total weight
        if graph.recommended_path:
            path_parts = []
            total_weight = 0.0
            for nid in graph.recommended_path:
                node = graph.nodes.get(nid)
                if node:
                    path_parts.append(node.technique_id)
            # Sum edge weights along path
            for i in range(len(graph.recommended_path) - 1):
                src, tgt = graph.recommended_path[i], graph.recommended_path[i + 1]
                for e in graph.edges:
                    if e.source == src and e.target == tgt:
                        total_weight += e.weight
                        break
            lines.append(
                f"Recommended path: {' → '.join(path_parts)} (W={total_weight:.2f})"
            )

        # Current position: deepest EXPLORED node
        explored_nodes = [n for n in graph.nodes.values() if n.status == NodeStatus.EXPLORED]
        if explored_nodes:
            current = max(explored_nodes, key=lambda n: n.depth)
            tactic_name = _TACTIC_NAMES.get(current.tactic_id, current.tactic_id)
            lines.append(
                f"Current position: {current.technique_id} ({tactic_name}) [explored]"
            )

        # Next best node: highest-IG PENDING node
        pending_nodes = [n for n in graph.nodes.values() if n.status == NodeStatus.PENDING]
        if pending_nodes:
            best = max(pending_nodes, key=lambda n: n.information_gain)
            tactic_name = _TACTIC_NAMES.get(best.tactic_id, best.tactic_id)
            lines.append(
                f"Next best node: {best.technique_id} ({tactic_name}) "
                f"confidence={best.confidence:.2f}"
            )

        # Unexplored high-value branches
        if graph.unexplored_branches:
            lines.append("Unexplored high-value branches:")
            for nid in graph.unexplored_branches[:5]:
                node = graph.nodes.get(nid)
                if node:
                    tactic_name = _TACTIC_NAMES.get(node.tactic_id, node.tactic_id)
                    lines.append(
                        f"  - {node.technique_id} ({tactic_name}) "
                        f"confidence={node.confidence:.2f}, info_gain={node.information_gain}"
                    )

        # Dead branches (pruned)
        pruned_nodes = [n for n in graph.nodes.values() if n.status == NodeStatus.PRUNED]
        if pruned_nodes:
            lines.append("Dead branches (pruned):")
            for node in pruned_nodes[:5]:
                tactic_name = _TACTIC_NAMES.get(node.tactic_id, node.tactic_id)
                lines.append(f"  - {node.technique_id} ({tactic_name}) — pruned")

        if not pending_nodes and not graph.unexplored_branches:
            lines.append("All known paths explored.")

        return "\n".join(lines)

    @staticmethod
    def compute_edge_weight(
        target_node: AttackNode,
        alpha: float = 0.5,
        beta: float = 0.3,
        gamma: float = 0.2,
    ) -> float:
        """Compute edge weight: W = alpha*C + beta*IG + gamma*(1 - E_norm)."""
        e_norm = min(target_node.effort / 5.0, 1.0)
        return alpha * target_node.confidence + beta * target_node.information_gain + gamma * (1.0 - e_norm)

    def compute_recommended_path(self, graph: AttackGraph) -> list[str]:
        """Dijkstra shortest path from entry nodes to highest-IG PENDING node."""
        if not graph.nodes or not graph.edges:
            return []

        # Source: all depth==0 nodes
        sources = [nid for nid, n in graph.nodes.items() if n.depth == 0]
        if not sources:
            return []

        # Destination: highest information_gain PENDING node
        pending_nodes = [
            (n.information_gain, nid)
            for nid, n in graph.nodes.items()
            if n.status == NodeStatus.PENDING
        ]
        if not pending_nodes:
            return []

        pending_nodes.sort(reverse=True)
        destination = pending_nodes[0][1]

        # Build adjacency list (exclude ALTERNATIVE edges)
        adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for edge in graph.edges:
            if edge.relationship == EdgeRelationship.ALTERNATIVE:
                continue
            target_node = graph.nodes.get(edge.target)
            if not target_node:
                continue
            # FAILED/PRUNED nodes have infinite cost
            if target_node.status in (NodeStatus.FAILED, NodeStatus.PRUNED):
                cost = float("inf")
            else:
                cost = 1.0 - edge.weight
            adj[edge.source].append((edge.target, cost))

        # Dijkstra
        dist: dict[str, float] = {nid: float("inf") for nid in graph.nodes}
        prev: dict[str, str | None] = {nid: None for nid in graph.nodes}

        heap: list[tuple[float, str]] = []
        for src in sources:
            dist[src] = 0.0
            heapq.heappush(heap, (0.0, src))

        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            if u == destination:
                break
            for v, w in adj[u]:
                new_dist = d + w
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(heap, (new_dist, v))

        # Reconstruct path
        if dist[destination] == float("inf"):
            return []

        path = []
        current: str | None = destination
        while current is not None:
            path.append(current)
            current = prev[current]
        path.reverse()
        return path

    def detect_cycles(self, graph: AttackGraph) -> list[list[str]]:
        """DFS color-marking cycle detection. ALTERNATIVE edges excluded."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {nid: WHITE for nid in graph.nodes}
        parent: dict[str, str | None] = {nid: None for nid in graph.nodes}
        cycles: list[list[str]] = []

        # Build adjacency (exclude ALTERNATIVE)
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.relationship == EdgeRelationship.ALTERNATIVE:
                continue
            adj[edge.source].append(edge.target)

        def dfs(u: str):
            color[u] = GRAY
            for v in adj[u]:
                if color[v] == GRAY:
                    # Found cycle — reconstruct
                    cycle = [v, u]
                    # Walk back from u to v through parent chain
                    curr = parent.get(u)
                    while curr and curr != v:
                        cycle.append(curr)
                        curr = parent.get(curr)
                    cycle.reverse()
                    cycles.append(cycle)
                elif color[v] == WHITE:
                    parent[v] = u
                    dfs(v)
            color[u] = BLACK

        for nid in graph.nodes:
            if color[nid] == WHITE:
                dfs(nid)

        return cycles

    def _break_cycles(self, graph: AttackGraph, cycles: list[list[str]]) -> None:
        """Break cycles by removing the lowest-weight edge in each cycle."""
        for cycle in cycles:
            if len(cycle) < 2:
                continue
            # Find edges in this cycle
            cycle_edges = []
            cycle_set = set(cycle)
            for edge in graph.edges:
                if edge.source in cycle_set and edge.target in cycle_set:
                    if edge.relationship != EdgeRelationship.ALTERNATIVE:
                        cycle_edges.append(edge)

            if cycle_edges:
                # Remove the lowest-weight edge
                lowest = min(cycle_edges, key=lambda e: e.weight)
                graph.edges = [e for e in graph.edges if e.edge_id != lowest.edge_id]
                logger.warning(
                    "Cycle detected and broken: removed edge %s (%s->%s, w=%.3f)",
                    lowest.edge_id, lowest.source, lowest.target, lowest.weight,
                )

    def prune_dead_branches(self, graph: AttackGraph) -> int:
        """When technique fails, prune siblings (same tactic+target, shared prereqs) and downstream.

        Returns the number of pruned nodes.
        """
        pruned_count = 0
        failed_nodes = [n for n in graph.nodes.values() if n.status == NodeStatus.FAILED]

        for failed in failed_nodes:
            # Find siblings: same tactic_id, same target_id, not the failed node itself
            siblings = [
                n for n in graph.nodes.values()
                if n.tactic_id == failed.tactic_id
                and n.target_id == failed.target_id
                and n.node_id != failed.node_id
                and n.status not in (NodeStatus.EXPLORED, NodeStatus.FAILED, NodeStatus.PRUNED)
            ]

            # Prune siblings that share at least one prerequisite with the failed node
            for sibling in siblings:
                shared_prereqs = set(sibling.prerequisites) & set(failed.prerequisites)
                if shared_prereqs:
                    sibling.status = NodeStatus.PRUNED
                    pruned_count += 1

        # Recursively prune downstream UNREACHABLE nodes
        pruned_count += self._propagate_prune(graph)
        return pruned_count

    def _propagate_prune(self, graph: AttackGraph) -> int:
        """Mark downstream nodes as PRUNED if all incoming edges are from PRUNED/FAILED.

        Returns the number of additionally pruned nodes.
        """
        count = 0
        changed = True
        while changed:
            changed = False
            # Build incoming edge map (non-ALTERNATIVE)
            incoming: dict[str, list[str]] = defaultdict(list)
            for edge in graph.edges:
                if edge.relationship != EdgeRelationship.ALTERNATIVE:
                    incoming[edge.target].append(edge.source)

            for nid, node in graph.nodes.items():
                if node.status in (NodeStatus.PRUNED, NodeStatus.FAILED, NodeStatus.EXPLORED):
                    continue
                sources = incoming.get(nid, [])
                if not sources:
                    continue
                # If ALL incoming sources are PRUNED or FAILED → prune this node
                all_dead = all(
                    graph.nodes[s].status in (NodeStatus.PRUNED, NodeStatus.FAILED)
                    for s in sources
                    if s in graph.nodes
                )
                if all_dead and sources:
                    node.status = NodeStatus.PRUNED
                    count += 1
                    changed = True
        return count

    # ------------------------------------------------------------------
    # Internal: in-memory graph construction
    # ------------------------------------------------------------------

    def _build_graph_in_memory(
        self,
        operation_id: str,
        targets: list[dict],
        facts: list[dict],
        executions: list[dict],
    ) -> AttackGraph:
        """Build the full graph from raw data. Pure function (no DB access)."""
        now = datetime.now(timezone.utc).isoformat()
        graph = AttackGraph(
            graph_id=str(uuid.uuid4()),
            operation_id=operation_id,
            updated_at=now,
        )

        if not targets:
            return graph

        # Build fact set and execution map
        fact_traits: set[str] = {f["trait"] for f in facts}
        exec_map: dict[tuple[str, str], str] = {}  # (technique_id, target_id) -> status
        exec_id_map: dict[tuple[str, str], str] = {}  # -> execution_id

        # Track which techniques succeeded on any target (for cross-target boost)
        technique_success: set[str] = set()
        # Track which (tactic_id, target_id) has a failed technique
        tactic_failures: set[tuple[str, str]] = set()

        for ex in executions:
            key = (ex["technique_id"], ex["target_id"])
            exec_map[key] = ex["status"]
            exec_id_map[key] = ex["id"]
            if ex["status"] == "success":
                technique_success.add(ex["technique_id"])
            if ex["status"] == "failed":
                rule = _RULE_BY_TECHNIQUE.get(ex["technique_id"])
                if rule:
                    tactic_failures.add((rule.tactic_id, ex["target_id"]))

        # Step 3: For each target x TechniqueRule: create AttackNode
        for target in targets:
            target_id = target["id"]
            for rule in _PREREQUISITE_RULES:
                node_id = self._make_node_id(rule.technique_id, target_id)

                # Calculate satisfied prerequisites
                satisfied = [f for f in rule.required_facts if f in fact_traits]
                total_required = len(rule.required_facts)

                # Determine status
                exec_key = (rule.technique_id, target_id)
                exec_status = exec_map.get(exec_key)

                if exec_status == "success":
                    status = NodeStatus.EXPLORED
                elif exec_status == "running":
                    status = NodeStatus.IN_PROGRESS
                elif exec_status == "failed":
                    status = NodeStatus.FAILED
                elif total_required == 0 or len(satisfied) == total_required:
                    status = NodeStatus.PENDING
                else:
                    status = NodeStatus.UNREACHABLE

                # Calculate confidence
                if total_required > 0:
                    confidence = rule.base_confidence * (len(satisfied) / total_required)
                else:
                    confidence = rule.base_confidence

                # Cross-target boost: +0.1 if same technique succeeded on another target
                if rule.technique_id in technique_success and exec_status != "success":
                    confidence = min(confidence + 0.1, 1.0)

                # Failed tactic penalty: -0.05 if same tactic has failed technique
                if (rule.tactic_id, target_id) in tactic_failures and exec_status != "failed":
                    confidence = max(confidence - 0.05, 0.0)

                # Depth based on tactic position in kill chain
                depth = _TACTIC_DEPTH.get(rule.tactic_id, 0)

                node = AttackNode(
                    node_id=node_id,
                    target_id=target_id,
                    technique_id=rule.technique_id,
                    tactic_id=rule.tactic_id,
                    status=status,
                    confidence=confidence,
                    risk_level=rule.risk_level,
                    information_gain=rule.information_gain,
                    effort=rule.effort,
                    prerequisites=list(rule.required_facts),
                    satisfied_prerequisites=satisfied,
                    execution_id=exec_id_map.get(exec_key),
                    depth=depth,
                )
                graph.nodes[node_id] = node

        # Step 4: Build edges
        self._build_edges(graph, targets)

        # Step 5: Compute edge weights (already done in _build_edges)

        # Step 6: Dead branch pruning
        self.prune_dead_branches(graph)

        # Step 7: Cycle detection and breaking
        cycles = self.detect_cycles(graph)
        if cycles:
            self._break_cycles(graph, cycles)

        # Step 8: Compute recommended path, explored paths, unexplored branches
        graph.recommended_path = self.compute_recommended_path(graph)

        graph.explored_paths = self._compute_explored_paths(graph)
        graph.unexplored_branches = [
            nid for nid, n in graph.nodes.items()
            if n.status == NodeStatus.PENDING
        ]

        # Step 9: Coverage score
        total = len(graph.nodes)
        explored = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.EXPLORED)
        graph.coverage_score = explored / total if total > 0 else 0.0

        return graph

    def _build_edges(self, graph: AttackGraph, targets: list[dict]) -> None:
        """Build edges between nodes: enables, requires, alternative, lateral."""
        target_ids = [t["id"] for t in targets]

        for rule in _PREREQUISITE_RULES:
            for target_id in target_ids:
                source_nid = self._make_node_id(rule.technique_id, target_id)
                if source_nid not in graph.nodes:
                    continue

                # ENABLES edges
                for enabled_tech in rule.enables:
                    target_nid = self._make_node_id(enabled_tech, target_id)
                    if target_nid in graph.nodes:
                        target_node = graph.nodes[target_nid]
                        weight = self.compute_edge_weight(target_node)
                        edge = AttackEdge(
                            edge_id=self._make_edge_id(source_nid, target_nid, "enables"),
                            source=source_nid,
                            target=target_nid,
                            weight=weight,
                            relationship=EdgeRelationship.ENABLES,
                            required_facts=list(
                                _RULE_BY_TECHNIQUE.get(enabled_tech, rule).required_facts
                            ),
                        )
                        graph.edges.append(edge)

                # ALTERNATIVE edges
                for alt_tech in rule.alternatives:
                    alt_nid = self._make_node_id(alt_tech, target_id)
                    if alt_nid in graph.nodes:
                        alt_node = graph.nodes[alt_nid]
                        weight = self.compute_edge_weight(alt_node)
                        edge = AttackEdge(
                            edge_id=self._make_edge_id(source_nid, alt_nid, "alternative"),
                            source=source_nid,
                            target=alt_nid,
                            weight=weight,
                            relationship=EdgeRelationship.ALTERNATIVE,
                            required_facts=[],
                        )
                        graph.edges.append(edge)

                # LATERAL edges — same technique on different targets
                if len(target_ids) > 1:
                    # Only create lateral edges for techniques that produce host.session
                    if "host.session" in rule.produced_facts:
                        for other_tid in target_ids:
                            if other_tid != target_id:
                                lateral_nid = self._make_node_id(rule.technique_id, other_tid)
                                if lateral_nid in graph.nodes:
                                    lateral_node = graph.nodes[lateral_nid]
                                    weight = self.compute_edge_weight(lateral_node)
                                    edge = AttackEdge(
                                        edge_id=self._make_edge_id(
                                            source_nid, lateral_nid, "lateral"
                                        ),
                                        source=source_nid,
                                        target=lateral_nid,
                                        weight=weight,
                                        relationship=EdgeRelationship.LATERAL,
                                        required_facts=list(rule.required_facts),
                                    )
                                    graph.edges.append(edge)

    def _compute_explored_paths(self, graph: AttackGraph) -> list[list[str]]:
        """Find all paths consisting entirely of EXPLORED nodes."""
        explored_ids = {nid for nid, n in graph.nodes.items() if n.status == NodeStatus.EXPLORED}
        if not explored_ids:
            return []

        # Build adjacency among explored nodes (non-ALTERNATIVE edges only)
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.relationship == EdgeRelationship.ALTERNATIVE:
                continue
            if edge.source in explored_ids and edge.target in explored_ids:
                adj[edge.source].append(edge.target)

        # Find roots (explored nodes with no incoming explored edge)
        has_incoming = set()
        for edge in graph.edges:
            if edge.relationship != EdgeRelationship.ALTERNATIVE:
                if edge.source in explored_ids and edge.target in explored_ids:
                    has_incoming.add(edge.target)

        roots = explored_ids - has_incoming
        if not roots:
            roots = explored_ids  # fallback: use all explored

        paths = []
        for root in roots:
            path = [root]
            current = root
            visited = {root}
            while True:
                neighbors = [n for n in adj.get(current, []) if n not in visited]
                if not neighbors:
                    break
                next_node = neighbors[0]
                path.append(next_node)
                visited.add(next_node)
                current = next_node
            if len(path) > 0:
                paths.append(path)

        return paths

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_node_id(technique_id: str, target_id: str) -> str:
        """Deterministic node ID from technique + target."""
        return f"{technique_id}::{target_id}"

    @staticmethod
    def _make_edge_id(source_nid: str, target_nid: str, rel: str) -> str:
        """Deterministic edge ID."""
        return f"{source_nid}--{rel}-->{target_nid}"

    # ------------------------------------------------------------------
    # DB queries
    # ------------------------------------------------------------------

    async def _query_targets(self, db, operation_id: str) -> list[dict]:
        cursor = await db.execute(
            "SELECT id, hostname, ip_address, os, role, operation_id "
            "FROM targets WHERE operation_id = ?",
            (operation_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) if hasattr(r, "keys") else {
            "id": r[0], "hostname": r[1], "ip_address": r[2],
            "os": r[3], "role": r[4], "operation_id": r[5],
        } for r in rows]

    async def _query_facts(self, db, operation_id: str) -> list[dict]:
        cursor = await db.execute(
            "SELECT id, trait, value, category, source_technique_id, "
            "source_target_id, operation_id FROM facts WHERE operation_id = ?",
            (operation_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) if hasattr(r, "keys") else {
            "id": r[0], "trait": r[1], "value": r[2], "category": r[3],
            "source_technique_id": r[4], "source_target_id": r[5],
            "operation_id": r[6],
        } for r in rows]

    async def _query_executions(self, db, operation_id: str) -> list[dict]:
        cursor = await db.execute(
            "SELECT id, technique_id, target_id, operation_id, status "
            "FROM technique_executions WHERE operation_id = ?",
            (operation_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) if hasattr(r, "keys") else {
            "id": r[0], "technique_id": r[1], "target_id": r[2],
            "operation_id": r[3], "status": r[4],
        } for r in rows]

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    async def _persist_graph(self, db, graph: AttackGraph) -> None:
        """Persist graph nodes and edges to SQLite."""
        now = datetime.now(timezone.utc).isoformat()

        for node in graph.nodes.values():
            await db.execute(
                "INSERT INTO attack_graph_nodes "
                "(id, operation_id, target_id, technique_id, tactic_id, "
                "status, confidence, risk_level, information_gain, effort, "
                "prerequisites, satisfied_prerequisites, source, execution_id, "
                "depth, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    node.node_id, graph.operation_id, node.target_id,
                    node.technique_id, node.tactic_id, node.status.value,
                    node.confidence, node.risk_level, node.information_gain,
                    node.effort, json.dumps(node.prerequisites),
                    json.dumps(node.satisfied_prerequisites), node.source,
                    node.execution_id, node.depth, now, now,
                ),
            )

        for edge in graph.edges:
            await db.execute(
                "INSERT INTO attack_graph_edges "
                "(id, operation_id, source_node_id, target_node_id, "
                "weight, relationship, required_facts, source_type, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    edge.edge_id, graph.operation_id, edge.source,
                    edge.target, edge.weight, edge.relationship.value,
                    json.dumps(edge.required_facts), edge.source_type, now,
                ),
            )

        await db.commit()

    # ------------------------------------------------------------------
    # Load from DB
    # ------------------------------------------------------------------

    async def load_from_db(self, db, operation_id: str) -> AttackGraph | None:
        """Load a previously persisted attack graph from DB."""
        cursor = await db.execute(
            "SELECT * FROM attack_graph_nodes WHERE operation_id = ?",
            (operation_id,),
        )
        node_rows = await cursor.fetchall()

        if not node_rows:
            return None

        graph = AttackGraph(
            graph_id=str(uuid.uuid4()),
            operation_id=operation_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        for row in node_rows:
            r = dict(row) if hasattr(row, "keys") else row
            node = AttackNode(
                node_id=r["id"] if isinstance(r, dict) else r[0],
                target_id=r["target_id"] if isinstance(r, dict) else r[2],
                technique_id=r["technique_id"] if isinstance(r, dict) else r[3],
                tactic_id=r["tactic_id"] if isinstance(r, dict) else r[4],
                status=NodeStatus(r["status"] if isinstance(r, dict) else r[5]),
                confidence=r["confidence"] if isinstance(r, dict) else r[6],
                risk_level=r["risk_level"] if isinstance(r, dict) else r[7],
                information_gain=r["information_gain"] if isinstance(r, dict) else r[8],
                effort=r["effort"] if isinstance(r, dict) else r[9],
                prerequisites=json.loads(
                    r["prerequisites"] if isinstance(r, dict) else r[10]
                ),
                satisfied_prerequisites=json.loads(
                    r["satisfied_prerequisites"] if isinstance(r, dict) else r[11]
                ),
                source=r["source"] if isinstance(r, dict) else r[12],
                execution_id=r["execution_id"] if isinstance(r, dict) else r[13],
                depth=r["depth"] if isinstance(r, dict) else r[14],
            )
            graph.nodes[node.node_id] = node

        cursor = await db.execute(
            "SELECT * FROM attack_graph_edges WHERE operation_id = ?",
            (operation_id,),
        )
        edge_rows = await cursor.fetchall()

        for row in edge_rows:
            r = dict(row) if hasattr(row, "keys") else row
            edge = AttackEdge(
                edge_id=r["id"] if isinstance(r, dict) else r[0],
                source=r["source_node_id"] if isinstance(r, dict) else r[2],
                target=r["target_node_id"] if isinstance(r, dict) else r[3],
                weight=r["weight"] if isinstance(r, dict) else r[4],
                relationship=EdgeRelationship(r["relationship"] if isinstance(r, dict) else r[5]),
                required_facts=json.loads(
                    r["required_facts"] if isinstance(r, dict) else r[6]
                ),
                source_type=r["source_type"] if isinstance(r, dict) else r[7],
            )
            graph.edges.append(edge)

        # Recompute derived fields
        graph.recommended_path = self.compute_recommended_path(graph)
        graph.explored_paths = self._compute_explored_paths(graph)
        graph.unexplored_branches = [
            nid for nid, n in graph.nodes.items()
            if n.status == NodeStatus.PENDING
        ]
        total = len(graph.nodes)
        explored = sum(1 for n in graph.nodes.values() if n.status == NodeStatus.EXPLORED)
        graph.coverage_score = explored / total if total > 0 else 0.0

        return graph
