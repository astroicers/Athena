# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Attack path, attack graph, and agent swarm schemas."""

from __future__ import annotations

from pydantic import BaseModel


class AttackPathEntry(BaseModel):
    execution_id: str
    mitre_id: str
    technique_name: str
    tactic: str         # "Reconnaissance", "Initial Access"
    tactic_id: str      # "TA0043", "TA0001"
    kill_chain_stage: str
    risk_level: str
    status: str         # queued|running|success|partial|failed
    engine: str
    started_at: str | None
    completed_at: str | None
    duration_sec: float | None   # computed in Python
    result_summary: str | None
    error_message: str | None
    facts_collected_count: int
    target_hostname: str | None
    target_ip: str | None


class AttackPathResponse(BaseModel):
    operation_id: str
    entries: list[AttackPathEntry]
    highest_tactic_idx: int          # 0-13, index of furthest reached tactic
    tactic_coverage: dict[str, int]  # tactic_id -> success count


class AttackGraphNode(BaseModel):
    node_id: str
    target_id: str
    technique_id: str
    tactic_id: str
    status: str
    confidence: float
    risk_level: str
    information_gain: float
    effort: int
    prerequisites: list[str]
    satisfied_prerequisites: list[str]
    source: str
    execution_id: str | None
    depth: int


class AttackGraphEdge(BaseModel):
    edge_id: str
    source: str
    target: str
    weight: float
    relationship: str
    required_facts: list[str]
    source_type: str


class AttackGraphStats(BaseModel):
    total_nodes: int
    explored_nodes: int
    pending_nodes: int
    failed_nodes: int
    pruned_nodes: int
    total_edges: int
    path_count: int
    max_depth: int


class AttackGraphResponse(BaseModel):
    graph_id: str
    operation_id: str
    nodes: list[AttackGraphNode]
    edges: list[AttackGraphEdge]
    recommended_path: list[str]
    explored_paths: list[list[str]]
    unexplored_branches: list[str]
    coverage_score: float
    updated_at: str
    stats: AttackGraphStats


class SwarmTaskSchema(BaseModel):
    task_id: str
    technique_id: str
    target_id: str
    engine: str
    status: str
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class SwarmBatchResponse(BaseModel):
    ooda_iteration_id: str
    total: int
    completed: int
    failed: int
    timed_out: int
    tasks: list[SwarmTaskSchema]
