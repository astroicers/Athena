# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Tests for SPEC-039: Attack Graph YAML Externalization and 50+ Rules."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from pydantic import ValidationError

from app.models.attack_graph import (
    AttackEdge,
    AttackGraph,
    AttackNode,
    EdgeRelationship,
    NodeStatus,
    TechniqueRule,
    TechniqueRuleSchema,
    TechniqueRulesFile,
)


# ---------------------------------------------------------------------------
# Phase 1 — YAML loading and Pydantic validation
# ---------------------------------------------------------------------------


class TestYAMLLoading:
    """Test that YAML loads successfully with correct structure."""

    def test_yaml_loads_at_least_50_rules(self):
        """YAML file loads >= 50 rules."""
        from app.services.attack_graph_engine import _PREREQUISITE_RULES
        assert len(_PREREQUISITE_RULES) >= 50

    def test_distinct_tactic_ids_at_least_8(self):
        """Rules cover at least 8 distinct tactic IDs."""
        from app.services.attack_graph_engine import _PREREQUISITE_RULES
        tactic_ids = {r.tactic_id for r in _PREREQUISITE_RULES}
        assert len(tactic_ids) >= 8

    def test_technique_rule_has_platforms_field(self):
        """TechniqueRule dataclass includes platforms field."""
        from app.services.attack_graph_engine import _PREREQUISITE_RULES
        for rule in _PREREQUISITE_RULES:
            assert hasattr(rule, "platforms")
            assert len(rule.platforms) >= 1

    def test_technique_rule_has_description_field(self):
        """TechniqueRule dataclass includes description field."""
        from app.services.attack_graph_engine import _PREREQUISITE_RULES
        for rule in _PREREQUISITE_RULES:
            assert hasattr(rule, "description")
            assert len(rule.description) > 0


class TestPydanticValidation:
    """Test Pydantic validation catches invalid data."""

    def _valid_rule_dict(self, **overrides):
        """Return a valid rule dict that can be overridden."""
        base = {
            "technique_id": "T1595.001",
            "tactic_id": "TA0043",
            "required_facts": [],
            "produced_facts": ["network.host.ip"],
            "risk_level": "low",
            "base_confidence": 0.95,
            "information_gain": 0.9,
            "effort": 1,
            "enables": [],
            "alternatives": [],
            "platforms": ["linux"],
            "description": "Test rule",
        }
        base.update(overrides)
        return base

    def test_confidence_above_1_rejected(self):
        """base_confidence > 1.0 raises ValidationError."""
        with pytest.raises(ValidationError):
            TechniqueRuleSchema(**self._valid_rule_dict(base_confidence=1.5))

    def test_invalid_risk_level_rejected(self):
        """risk_level 'extreme' raises ValidationError."""
        with pytest.raises(ValidationError):
            TechniqueRuleSchema(**self._valid_rule_dict(risk_level="extreme"))

    def test_invalid_technique_id_rejected(self):
        """technique_id 'INVALID' raises ValidationError."""
        with pytest.raises(ValidationError):
            TechniqueRuleSchema(**self._valid_rule_dict(technique_id="INVALID"))

    def test_empty_produced_facts_rejected(self):
        """produced_facts=[] raises ValidationError."""
        with pytest.raises(ValidationError):
            TechniqueRuleSchema(**self._valid_rule_dict(produced_facts=[]))

    def test_empty_platforms_rejected(self):
        """platforms=[] raises ValidationError."""
        with pytest.raises(ValidationError):
            TechniqueRuleSchema(**self._valid_rule_dict(platforms=[]))

    def test_empty_rules_list_rejected(self):
        """TechniqueRulesFile with empty rules list raises ValidationError."""
        with pytest.raises(ValidationError):
            TechniqueRulesFile(version="1.0", rules=[])

    def test_valid_rule_accepted(self):
        """A fully valid rule passes validation."""
        rule = TechniqueRuleSchema(**self._valid_rule_dict())
        assert rule.technique_id == "T1595.001"


# ---------------------------------------------------------------------------
# Phase 2 — Cost formula
# ---------------------------------------------------------------------------


class TestCostFormula:
    """Test the new compute_edge_cost formula."""

    def _make_node(self, **kwargs):
        defaults = {
            "node_id": "n1",
            "target_id": "t1",
            "technique_id": "T1595.001",
            "tactic_id": "TA0043",
            "status": NodeStatus.PENDING,
            "confidence": 0.5,
            "risk_level": "medium",
            "information_gain": 0.5,
            "effort": 1,
            "prerequisites": [],
            "satisfied_prerequisites": [],
        }
        defaults.update(kwargs)
        return AttackNode(**defaults)

    def test_high_confidence_low_risk_low_cost(self):
        """High confidence + high IG + low risk + effort 1 => low cost (~0.08)."""
        from app.services.attack_graph_engine import AttackGraphEngine
        node = self._make_node(
            confidence=0.95, information_gain=0.9,
            risk_level="low", effort=1,
        )
        cost = AttackGraphEngine.compute_edge_cost(node)
        # 0.35*(1-0.95) + 0.25*(1-0.9) + 0.25*0.1 + 0.15*(1/5)
        # = 0.35*0.05 + 0.25*0.1 + 0.25*0.1 + 0.15*0.2
        # = 0.0175 + 0.025 + 0.025 + 0.03 = 0.0975
        assert cost < 0.15

    def test_low_confidence_high_risk_high_cost(self):
        """Low confidence + low IG + high risk + effort 4 => high cost (~0.53)."""
        from app.services.attack_graph_engine import AttackGraphEngine
        node = self._make_node(
            confidence=0.4, information_gain=0.3,
            risk_level="high", effort=4,
        )
        cost = AttackGraphEngine.compute_edge_cost(node)
        # 0.35*(1-0.4) + 0.25*(1-0.3) + 0.25*0.6 + 0.15*(4/5)
        # = 0.35*0.6 + 0.25*0.7 + 0.25*0.6 + 0.15*0.8
        # = 0.21 + 0.175 + 0.15 + 0.12 = 0.655
        assert cost > 0.4

    def test_cost_ordering(self):
        """Good node has lower cost than bad node."""
        from app.services.attack_graph_engine import AttackGraphEngine

        good = self._make_node(
            confidence=0.95, information_gain=0.9,
            risk_level="low", effort=1,
        )
        bad = self._make_node(
            confidence=0.4, information_gain=0.3,
            risk_level="high", effort=4,
        )
        cost_good = AttackGraphEngine.compute_edge_cost(good)
        cost_bad = AttackGraphEngine.compute_edge_cost(bad)
        assert cost_good < cost_bad

    def test_risk_cost_map_values(self):
        """RISK_COST_MAP contains expected values."""
        from app.services.attack_graph_engine import RISK_COST_MAP
        assert RISK_COST_MAP == {
            "low": 0.1,
            "medium": 0.3,
            "high": 0.6,
            "critical": 1.0,
        }


# ---------------------------------------------------------------------------
# Phase 3 — Pruning fixes
# ---------------------------------------------------------------------------


class TestPruningFixes:
    """Test that pruning correctly protects alternatives."""

    def _make_engine(self):
        from app.services.attack_graph_engine import AttackGraphEngine
        ws = MagicMock()
        ws.broadcast = MagicMock()
        return AttackGraphEngine(ws)

    def test_alternative_not_pruned_when_sibling_fails(self):
        """T1110.001 fails -> T1190 (its alternative) is NOT pruned."""
        engine = self._make_engine()

        graph = AttackGraph(
            graph_id="g-prune", operation_id="op-1",
        )

        prereq = AttackNode(
            node_id="prereq", target_id="t1", technique_id="T1595.001",
            tactic_id="TA0043", status=NodeStatus.EXPLORED,
            confidence=0.95, risk_level="low", information_gain=0.9,
            effort=1, prerequisites=[], satisfied_prerequisites=[], depth=0,
        )
        failed_node = AttackNode(
            node_id="T1110.001::t1", target_id="t1", technique_id="T1110.001",
            tactic_id="TA0001", status=NodeStatus.FAILED,
            confidence=0.0, risk_level="medium", information_gain=0.6,
            effort=1, prerequisites=["service.open_port"],
            satisfied_prerequisites=["service.open_port"], depth=1,
        )
        alternative_node = AttackNode(
            node_id="T1190::t1", target_id="t1", technique_id="T1190",
            tactic_id="TA0001", status=NodeStatus.PENDING,
            confidence=0.6, risk_level="medium", information_gain=0.7,
            effort=2, prerequisites=["service.open_port"],
            satisfied_prerequisites=["service.open_port"], depth=1,
        )

        graph.nodes = {
            "prereq": prereq,
            "T1110.001::t1": failed_node,
            "T1190::t1": alternative_node,
        }
        graph.edges = [
            AttackEdge(
                edge_id="e1", source="prereq", target="T1110.001::t1",
                weight=0.5, relationship=EdgeRelationship.ENABLES,
                required_facts=[],
            ),
            AttackEdge(
                edge_id="e2", source="prereq", target="T1190::t1",
                weight=0.5, relationship=EdgeRelationship.ENABLES,
                required_facts=[],
            ),
            AttackEdge(
                edge_id="e3", source="T1110.001::t1", target="T1190::t1",
                weight=0.4, relationship=EdgeRelationship.ALTERNATIVE,
                required_facts=[],
            ),
        ]

        engine.prune_dead_branches(graph)

        # T1190 is an alternative of T1110.001 -> should NOT be pruned
        assert graph.nodes["T1190::t1"].status == NodeStatus.PENDING

    def test_non_alternative_sibling_pruned(self):
        """A sibling that shares prereqs but is NOT an alternative IS pruned."""
        engine = self._make_engine()

        graph = AttackGraph(
            graph_id="g-prune2", operation_id="op-1",
        )

        failed_node = AttackNode(
            node_id="T1190::t1", target_id="t1", technique_id="T1190",
            tactic_id="TA0001", status=NodeStatus.FAILED,
            confidence=0.0, risk_level="medium", information_gain=0.7,
            effort=2, prerequisites=["service.open_port"],
            satisfied_prerequisites=["service.open_port"], depth=1,
        )
        # A hypothetical sibling in same tactic with shared prereqs, NOT in alternatives
        sibling = AttackNode(
            node_id="T1133::t1", target_id="t1", technique_id="T1133",
            tactic_id="TA0001", status=NodeStatus.PENDING,
            confidence=0.75, risk_level="medium", information_gain=0.65,
            effort=1, prerequisites=["service.open_port", "credential.ssh"],
            satisfied_prerequisites=["service.open_port"], depth=1,
        )

        graph.nodes = {
            "T1190::t1": failed_node,
            "T1133::t1": sibling,
        }
        graph.edges = []

        engine.prune_dead_branches(graph)

        # T1133 shares "service.open_port" with T1190 and is NOT in T1190's
        # alternatives (T1190 alternatives = ["T1110.001"]), so it gets pruned
        assert graph.nodes["T1133::t1"].status == NodeStatus.PRUNED

    def test_propagate_prune_alive_alternative_protects_node(self):
        """Node with all normal incoming dead but alive alternative incoming is NOT pruned."""
        engine = self._make_engine()

        graph = AttackGraph(
            graph_id="g-prop", operation_id="op-1",
        )

        dead_source = AttackNode(
            node_id="dead", target_id="t1", technique_id="T0001",
            tactic_id="TA0001", status=NodeStatus.FAILED,
            confidence=0.0, risk_level="low", information_gain=0.5,
            effort=1, prerequisites=[], satisfied_prerequisites=[], depth=0,
        )
        alive_alt_source = AttackNode(
            node_id="alive", target_id="t1", technique_id="T0002",
            tactic_id="TA0001", status=NodeStatus.PENDING,
            confidence=0.8, risk_level="low", information_gain=0.5,
            effort=1, prerequisites=[], satisfied_prerequisites=[], depth=0,
        )
        target_node = AttackNode(
            node_id="target", target_id="t1", technique_id="T0003",
            tactic_id="TA0002", status=NodeStatus.PENDING,
            confidence=0.7, risk_level="medium", information_gain=0.6,
            effort=1, prerequisites=[], satisfied_prerequisites=[], depth=1,
        )

        graph.nodes = {
            "dead": dead_source,
            "alive": alive_alt_source,
            "target": target_node,
        }
        graph.edges = [
            AttackEdge(
                edge_id="e1", source="dead", target="target",
                weight=0.5, relationship=EdgeRelationship.ENABLES,
                required_facts=[],
            ),
            AttackEdge(
                edge_id="e2", source="alive", target="target",
                weight=0.4, relationship=EdgeRelationship.ALTERNATIVE,
                required_facts=[],
            ),
        ]

        count = engine._propagate_prune(graph)

        # target has alive alternative incoming -> not pruned
        assert graph.nodes["target"].status == NodeStatus.PENDING
        assert count == 0

    def test_propagate_prune_all_dead_including_alt(self):
        """Node with all incoming (normal + alternative) dead IS pruned."""
        engine = self._make_engine()

        graph = AttackGraph(
            graph_id="g-prop2", operation_id="op-1",
        )

        dead_source = AttackNode(
            node_id="dead", target_id="t1", technique_id="T0001",
            tactic_id="TA0001", status=NodeStatus.FAILED,
            confidence=0.0, risk_level="low", information_gain=0.5,
            effort=1, prerequisites=[], satisfied_prerequisites=[], depth=0,
        )
        dead_alt = AttackNode(
            node_id="dead_alt", target_id="t1", technique_id="T0002",
            tactic_id="TA0001", status=NodeStatus.PRUNED,
            confidence=0.0, risk_level="low", information_gain=0.5,
            effort=1, prerequisites=[], satisfied_prerequisites=[], depth=0,
        )
        target_node = AttackNode(
            node_id="target", target_id="t1", technique_id="T0003",
            tactic_id="TA0002", status=NodeStatus.PENDING,
            confidence=0.7, risk_level="medium", information_gain=0.6,
            effort=1, prerequisites=[], satisfied_prerequisites=[], depth=1,
        )

        graph.nodes = {
            "dead": dead_source,
            "dead_alt": dead_alt,
            "target": target_node,
        }
        graph.edges = [
            AttackEdge(
                edge_id="e1", source="dead", target="target",
                weight=0.5, relationship=EdgeRelationship.ENABLES,
                required_facts=[],
            ),
            AttackEdge(
                edge_id="e2", source="dead_alt", target="target",
                weight=0.4, relationship=EdgeRelationship.ALTERNATIVE,
                required_facts=[],
            ),
        ]

        count = engine._propagate_prune(graph)

        assert graph.nodes["target"].status == NodeStatus.PRUNED
        assert count == 1
