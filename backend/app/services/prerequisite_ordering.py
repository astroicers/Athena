# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""SPEC-058: Swarm prerequisite ordering — DAG-based execution batching.

Prevents race conditions in agent_swarm by ordering techniques according to
the `enables` dependency graph in technique_rules.yaml. Techniques in the
same batch are safe to run in parallel; cross-batch dependencies must complete
before the next batch starts.

Usage (ooda_controller.py ACT phase)::

    from app.services.prerequisite_ordering import order_parallel_tasks

    ordered_batches = order_parallel_tasks(parallel_tasks)
    for batch in ordered_batches:
        await swarm.execute_swarm(..., batch)
"""

import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


def build_dependency_graph(technique_ids: list[str]) -> dict[str, list[str]]:
    """Build a directed dependency graph for the given technique IDs.

    Edges represent "must run before" relationships derived from the
    technique_rules.yaml `enables` field: if rule A enables B, then A → B
    (A must complete before B can start).

    Args:
        technique_ids: The techniques to consider. Only edges between members
                       of this set are included.

    Returns:
        Dict mapping each technique_id to the list of technique_ids that
        depend on it (i.e. successors that need it to complete first).
    """
    from app.services.attack_graph_engine import _RULE_BY_TECHNIQUE

    id_set = set(technique_ids)
    graph: dict[str, list[str]] = {tid: [] for tid in technique_ids}

    for tid in technique_ids:
        rule = _RULE_BY_TECHNIQUE.get(tid)
        if rule is None:
            continue
        for enabled in rule.enables:
            if enabled in id_set:
                # tid enables enabled → tid must run before enabled
                graph[tid].append(enabled)

    return graph


def topological_sort(graph: dict[str, list[str]]) -> list[list[str]]:
    """Kahn's algorithm: return execution batches (parallel within, sequential across).

    Args:
        graph: Adjacency list (predecessor → [successors]) as returned by
               build_dependency_graph().

    Returns:
        List of batches. All techniques in a batch may run in parallel.
        Each batch must complete before the next batch starts.
        Raises ValueError if the graph contains a cycle.
    """
    # Compute in-degree for each node
    in_degree: dict[str, int] = defaultdict(int)
    for node in graph:
        in_degree.setdefault(node, 0)
        for successor in graph[node]:
            in_degree[successor] += 1

    # Start with nodes that have no prerequisites
    queue: deque[str] = deque(
        node for node in graph if in_degree[node] == 0
    )

    batches: list[list[str]] = []
    visited = 0

    while queue:
        batch = list(queue)
        queue.clear()
        batches.append(batch)
        visited += len(batch)

        next_batch_candidates: list[str] = []
        for node in batch:
            for successor in graph.get(node, []):
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    next_batch_candidates.append(successor)

        queue.extend(next_batch_candidates)

    if visited != len(graph):
        cycle_nodes = [n for n in graph if in_degree[n] > 0]
        raise ValueError(
            f"Cycle detected in technique dependency graph: {cycle_nodes}"
        )

    return batches


def validate_execution_order(completed: set[str], next_technique: str) -> bool:
    """Check whether all prerequisites for next_technique are already completed.

    Intended as a lightweight guard in the swarm executor before dispatching
    an individual technique. Uses the `required_facts` model indirectly via
    the `enables` reverse-lookup: a technique is blocked if any other technique
    in _RULE_BY_TECHNIQUE explicitly enables it AND that enabler has not yet run.

    Args:
        completed: Set of technique_ids that have already succeeded.
        next_technique: The technique_id about to be dispatched.

    Returns:
        True if safe to proceed; False if a prerequisite enabler is pending.
    """
    from app.services.attack_graph_engine import _RULE_BY_TECHNIQUE

    for tid, rule in _RULE_BY_TECHNIQUE.items():
        if next_technique in rule.enables and tid not in completed:
            logger.debug(
                "SPEC-058: %s blocked — prerequisite enabler %s not yet completed",
                next_technique, tid,
            )
            return False
    return True


def order_parallel_tasks(
    parallel_tasks: list[dict],
) -> list[list[dict]]:
    """Top-level helper: take raw swarm task dicts and return ordered batches.

    Each task dict must have a "technique_id" key (matching agent_swarm format).
    Tasks without a known technique_id are placed in the first batch (no ordering
    information available).

    Args:
        parallel_tasks: List of task dicts as produced by DecisionEngine
                        (each has keys: technique_id, target_id, engine, ...).

    Returns:
        List of batches. Within each batch all tasks are parallel-safe.
    """
    if not parallel_tasks:
        return []

    if len(parallel_tasks) == 1:
        return [parallel_tasks]

    technique_ids = [t.get("technique_id", "") for t in parallel_tasks]
    known = [tid for tid in technique_ids if tid]

    if not known:
        return [parallel_tasks]

    try:
        graph = build_dependency_graph(known)
        ordered_ids = topological_sort(graph)
    except ValueError as exc:
        logger.warning("SPEC-058: DAG cycle detected (%s) — falling back to single batch", exc)
        return [parallel_tasks]

    # Map back from technique_id batches to original task dicts
    id_to_tasks: dict[str, list[dict]] = defaultdict(list)
    unordered: list[dict] = []
    for task in parallel_tasks:
        tid = task.get("technique_id", "")
        if tid in graph:
            id_to_tasks[tid].append(task)
        else:
            unordered.append(task)

    result: list[list[dict]] = []
    if unordered:
        result.append(unordered)

    for batch_ids in ordered_ids:
        batch_tasks: list[dict] = []
        for tid in batch_ids:
            batch_tasks.extend(id_to_tasks.get(tid, []))
        if batch_tasks:
            result.append(batch_tasks)

    return result if result else [parallel_tasks]
