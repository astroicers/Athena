# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Attack graph engine — deterministic prerequisite-rule-based graph construction.

SPEC-031: Builds and maintains an in-memory attack graph from targets, facts,
and technique executions. Uses Dijkstra for recommended path, DFS for cycle
detection, and dead-branch pruning for failed techniques.

No external dependencies (no networkx). Uses stdlib: heapq, collections, uuid.
"""

import heapq
import json
import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import yaml

from app.models.attack_graph import (
    AttackEdge,
    AttackGraph,
    AttackNode,
    EdgeRelationship,
    NodeStatus,
    TechniqueRule,
    TechniqueRulesFile,
)
from app.ws_manager import WebSocketManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# YAML-based rule loading — SPEC-039
# ---------------------------------------------------------------------------

_DEFAULT_RULES_PATH = Path(__file__).parent.parent / "data" / "technique_rules.yaml"


def _load_rules(path: Path | None = None) -> list[TechniqueRule]:
    """Load technique rules from YAML file with Pydantic validation.

    Args:
        path: YAML file path. Defaults to backend/app/data/technique_rules.yaml.
              Can be overridden via TECHNIQUE_RULES_PATH env var.

    Returns:
        List of validated TechniqueRule objects.

    Raises:
        FileNotFoundError: YAML file does not exist.
        ValueError: YAML content fails Pydantic validation.
    """
    if path is None:
        env_path = os.environ.get("TECHNIQUE_RULES_PATH")
        path = Path(env_path) if env_path else _DEFAULT_RULES_PATH

    start = time.perf_counter()

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Pydantic validation
    validated = TechniqueRulesFile(**raw)

    rules = []
    seen_ids: set[str] = set()
    for r in validated.rules:
        if r.technique_id in seen_ids:
            logger.warning(
                "Duplicate technique_id %s in rules file; later entry overwrites.",
                r.technique_id,
            )
        seen_ids.add(r.technique_id)
        rules.append(TechniqueRule(
            technique_id=r.technique_id,
            tactic_id=r.tactic_id,
            required_facts=r.required_facts,
            produced_facts=r.produced_facts,
            risk_level=r.risk_level,
            base_confidence=r.base_confidence,
            information_gain=r.information_gain,
            effort=r.effort,
            enables=r.enables,
            alternatives=r.alternatives,
            platforms=r.platforms,
            description=r.description,
        ))

    # Warn about enables references to non-existent technique_ids
    all_ids = {r.technique_id for r in rules}
    for r in rules:
        for enabled in r.enables:
            if enabled not in all_ids:
                logger.warning(
                    "Rule %s enables non-existent technique %s",
                    r.technique_id, enabled,
                )

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info("Loaded %d technique rules from %s in %.1fms", len(rules), path, elapsed_ms)

    return rules


def reload_rules(path: Path | None = None) -> None:
    """Hot-reload rules without restart. Thread-safe via module-level replacement."""
    global _PREREQUISITE_RULES, _RULE_BY_TECHNIQUE
    new_rules = _load_rules(path)
    new_lookup = {r.technique_id: r for r in new_rules}
    # Atomic swap
    _PREREQUISITE_RULES = new_rules
    _RULE_BY_TECHNIQUE = new_lookup
    logger.info("Hot-reloaded %d technique rules", len(new_rules))


# Module-level initialization
_PREREQUISITE_RULES: list[TechniqueRule] = _load_rules()
_RULE_BY_TECHNIQUE: dict[str, TechniqueRule] = {r.technique_id: r for r in _PREREQUISITE_RULES}

# ---------------------------------------------------------------------------
# Cost map for risk levels — SPEC-039
# ---------------------------------------------------------------------------

RISK_COST_MAP: dict[str, float] = {
    "low": 0.1,
    "medium": 0.3,
    "high": 0.6,
    "critical": 1.0,
}

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
        self, db: asyncpg.Connection, operation_id: str
    ) -> AttackGraph:
        """Full rebuild: query DB, build graph, persist, broadcast."""
        # 1. Query data
        targets = await self._query_targets(db, operation_id)
        facts = await self._query_facts(db, operation_id)
        executions = await self._query_executions(db, operation_id)

        # 2. Clear old graph data
        await db.execute(
            "DELETE FROM attack_graph_edges WHERE operation_id = $1",
            operation_id,
        )
        await db.execute(
            "DELETE FROM attack_graph_nodes WHERE operation_id = $1",
            operation_id,
        )

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
                "recommended_path": graph.recommended_path,  # SPEC-042
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
    def compute_edge_cost(target_node: AttackNode) -> float:
        """Direct cost formula -- lower value = better path.

        cost = 0.35*(1-confidence) + 0.25*(1-information_gain)
             + 0.25*risk_cost + 0.15*effort_norm

        Designed for Dijkstra shortest-path: semantically intuitive,
        no desirability-inversion needed.
        """
        risk_cost = RISK_COST_MAP.get(target_node.risk_level, 0.3)
        effort_norm = min(target_node.effort / 5.0, 1.0)
        return (
            0.35 * (1.0 - target_node.confidence)
            + 0.25 * (1.0 - target_node.information_gain)
            + 0.25 * risk_cost
            + 0.15 * effort_norm
        )

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
                cost = edge.weight  # weight IS cost (SPEC-039)
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

        SPEC-039: Siblings listed in the failed node's `alternatives` are protected
        from pruning (they represent different attack vectors).

        Returns the number of pruned nodes.
        """
        pruned_count = 0
        failed_nodes = [n for n in graph.nodes.values() if n.status == NodeStatus.FAILED]

        for failed in failed_nodes:
            # Get the failed node's rule to find its alternatives list
            failed_rule = _RULE_BY_TECHNIQUE.get(failed.technique_id)
            protected_techniques: set[str] = set()
            if failed_rule:
                protected_techniques = set(failed_rule.alternatives)

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
                # Protect alternative techniques from pruning
                if sibling.technique_id in protected_techniques:
                    logger.debug(
                        "Protecting alternative technique %s from pruning "
                        "(alternative of failed %s)",
                        sibling.technique_id, failed.technique_id,
                    )
                    continue

                shared_prereqs = set(sibling.prerequisites) & set(failed.prerequisites)
                if shared_prereqs:
                    sibling.status = NodeStatus.PRUNED
                    pruned_count += 1

        # Recursively prune downstream UNREACHABLE nodes
        pruned_count += self._propagate_prune(graph)
        return pruned_count

    def _propagate_prune(self, graph: AttackGraph) -> int:
        """Mark downstream nodes as PRUNED if all incoming edges are from PRUNED/FAILED.

        SPEC-039: Also checks ALTERNATIVE incoming edges. If at least one
        alive alternative source exists, the node is protected from pruning.

        Returns the number of additionally pruned nodes.
        """
        count = 0
        changed = True
        while changed:
            changed = False
            # Build incoming edge maps: normal and alternative
            incoming_normal: dict[str, list[str]] = defaultdict(list)
            incoming_alt: dict[str, list[str]] = defaultdict(list)
            for edge in graph.edges:
                if edge.relationship == EdgeRelationship.ALTERNATIVE:
                    incoming_alt[edge.target].append(edge.source)
                else:
                    incoming_normal[edge.target].append(edge.source)

            for nid, node in graph.nodes.items():
                if node.status in (NodeStatus.PRUNED, NodeStatus.FAILED, NodeStatus.EXPLORED):
                    continue
                normal_sources = incoming_normal.get(nid, [])
                if not normal_sources:
                    continue

                # Check if ALL normal incoming sources are PRUNED or FAILED
                all_normal_dead = all(
                    graph.nodes[s].status in (NodeStatus.PRUNED, NodeStatus.FAILED)
                    for s in normal_sources
                    if s in graph.nodes
                )

                if not all_normal_dead:
                    continue

                # Check if any alive alternative incoming source exists
                alt_sources = incoming_alt.get(nid, [])
                has_alive_alt = any(
                    graph.nodes[s].status not in (NodeStatus.PRUNED, NodeStatus.FAILED)
                    for s in alt_sources
                    if s in graph.nodes
                )

                if has_alive_alt:
                    # At least one alternative path is alive, do not prune
                    continue

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
        now = datetime.now(timezone.utc)
        graph = AttackGraph(
            graph_id=str(uuid.uuid4()),
            operation_id=operation_id,
            updated_at=now,
        )

        if not targets:
            return graph

        # Build fact set and execution map
        # SPEC-037: exclude invalidated credentials so dependent nodes become UNREACHABLE
        fact_traits: set[str] = {
            f["trait"] for f in facts if ".invalidated" not in f["trait"]
        }
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
                        weight = self.compute_edge_cost(target_node)
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
                        weight = self.compute_edge_cost(alt_node)
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
                                    weight = self.compute_edge_cost(lateral_node)
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
        rows = await db.fetch(
            "SELECT id, hostname, ip_address, os, role, operation_id "
            "FROM targets WHERE operation_id = $1",
            operation_id,
        )
        return [dict(r) for r in rows]

    async def _query_facts(self, db, operation_id: str) -> list[dict]:
        rows = await db.fetch(
            "SELECT id, trait, value, category, source_technique_id, "
            "source_target_id, operation_id FROM facts WHERE operation_id = $1",
            operation_id,
        )
        return [dict(r) for r in rows]

    async def _query_executions(self, db, operation_id: str) -> list[dict]:
        rows = await db.fetch(
            "SELECT id, technique_id, target_id, operation_id, status "
            "FROM technique_executions WHERE operation_id = $1",
            operation_id,
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    async def _persist_graph(self, db, graph: AttackGraph) -> None:
        """Persist graph nodes and edges to PostgreSQL."""
        now = datetime.now(timezone.utc)

        for node in graph.nodes.values():
            await db.execute(
                "INSERT INTO attack_graph_nodes "
                "(id, operation_id, target_id, technique_id, tactic_id, "
                "status, confidence, risk_level, information_gain, effort, "
                "prerequisites, satisfied_prerequisites, source, execution_id, "
                "depth, created_at, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)",
                node.node_id, graph.operation_id, node.target_id,
                node.technique_id, node.tactic_id, node.status.value,
                node.confidence, node.risk_level, node.information_gain,
                node.effort, json.dumps(node.prerequisites),
                json.dumps(node.satisfied_prerequisites), node.source,
                node.execution_id, node.depth, now, now,
            )

        for edge in graph.edges:
            await db.execute(
                "INSERT INTO attack_graph_edges "
                "(id, operation_id, source_node_id, target_node_id, "
                "weight, relationship, required_facts, source_type, created_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                edge.edge_id, graph.operation_id, edge.source,
                edge.target, edge.weight, edge.relationship.value,
                json.dumps(edge.required_facts), edge.source_type, now,
            )

    # ------------------------------------------------------------------
    # Load from DB
    # ------------------------------------------------------------------

    async def load_from_db(self, db, operation_id: str) -> AttackGraph | None:
        """Load a previously persisted attack graph from DB."""
        node_rows = await db.fetch(
            "SELECT * FROM attack_graph_nodes WHERE operation_id = $1",
            operation_id,
        )

        if not node_rows:
            return None

        graph = AttackGraph(
            graph_id=str(uuid.uuid4()),
            operation_id=operation_id,
            updated_at=datetime.now(timezone.utc),
        )

        for row in node_rows:
            r = dict(row)
            node = AttackNode(
                node_id=r["id"],
                target_id=r["target_id"],
                technique_id=r["technique_id"],
                tactic_id=r["tactic_id"],
                status=NodeStatus(r["status"]),
                confidence=r["confidence"],
                risk_level=r["risk_level"],
                information_gain=r["information_gain"],
                effort=r["effort"],
                prerequisites=json.loads(r["prerequisites"]),
                satisfied_prerequisites=json.loads(r["satisfied_prerequisites"]),
                source=r["source"],
                execution_id=r["execution_id"],
                depth=r["depth"],
            )
            graph.nodes[node.node_id] = node

        edge_rows = await db.fetch(
            "SELECT * FROM attack_graph_edges WHERE operation_id = $1",
            operation_id,
        )

        for row in edge_rows:
            r = dict(row)
            edge = AttackEdge(
                edge_id=r["id"],
                source=r["source_node_id"],
                target=r["target_node_id"],
                weight=r["weight"],
                relationship=EdgeRelationship(r["relationship"]),
                required_facts=json.loads(r["required_facts"]),
                source_type=r["source_type"],
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
