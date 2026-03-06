# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Attack graph domain models — SPEC-031."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeStatus(str, Enum):
    EXPLORED = "explored"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    UNREACHABLE = "unreachable"
    FAILED = "failed"
    PRUNED = "pruned"


class EdgeRelationship(str, Enum):
    ENABLES = "enables"
    REQUIRES = "requires"
    ALTERNATIVE = "alternative"
    LATERAL = "lateral"


@dataclass
class TechniqueRule:
    technique_id: str
    tactic_id: str
    required_facts: list[str]
    produced_facts: list[str]
    risk_level: str
    base_confidence: float
    information_gain: float
    effort: int
    enables: list[str]
    alternatives: list[str]


@dataclass
class AttackNode:
    node_id: str
    target_id: str
    technique_id: str
    tactic_id: str
    status: NodeStatus
    confidence: float
    risk_level: str
    information_gain: float
    effort: int
    prerequisites: list[str]
    satisfied_prerequisites: list[str]
    source: str = "deterministic"
    execution_id: Optional[str] = None
    depth: int = 0


@dataclass
class AttackEdge:
    edge_id: str
    source: str  # AttackNode.node_id
    target: str  # AttackNode.node_id
    weight: float
    relationship: EdgeRelationship
    required_facts: list[str]
    source_type: str = "deterministic"


@dataclass
class AttackGraph:
    graph_id: str
    operation_id: str
    nodes: dict[str, AttackNode] = field(default_factory=dict)
    edges: list[AttackEdge] = field(default_factory=list)
    recommended_path: list[str] = field(default_factory=list)
    explored_paths: list[list[str]] = field(default_factory=list)
    unexplored_branches: list[str] = field(default_factory=list)
    coverage_score: float = 0.0
    updated_at: str = ""
