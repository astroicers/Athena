// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

/**
 * Attack graph types — SPEC-031.
 */

export interface AttackGraphNode {
  nodeId: string;
  targetId: string;
  techniqueId: string;
  tacticId: string;
  status: "explored" | "in_progress" | "pending" | "unreachable" | "failed" | "pruned";
  confidence: number;
  riskLevel: string;
  informationGain: number;
  effort: number;
  prerequisites: string[];
  satisfiedPrerequisites: string[];
  source: "deterministic" | "llm_suggested";
  executionId: string | null;
  depth: number;
}

export interface AttackGraphEdge {
  edgeId: string;
  source: string;
  target: string;
  weight: number;
  relationship: "enables" | "requires" | "alternative" | "lateral";
  requiredFacts: string[];
  sourceType: "deterministic" | "llm_suggested";
}

export interface AttackGraphStats {
  totalNodes: number;
  exploredNodes: number;
  pendingNodes: number;
  failedNodes: number;
  prunedNodes: number;
  totalEdges: number;
  pathCount: number;
  maxDepth: number;
}

export interface AttackGraphResponse {
  graphId: string;
  operationId: string;
  nodes: AttackGraphNode[];
  edges: AttackGraphEdge[];
  recommendedPath: string[];
  exploredPaths: string[][];
  unexploredBranches: string[];
  coverageScore: number;
  updatedAt: string;
  stats: AttackGraphStats;
}
