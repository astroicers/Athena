// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

export interface ApiError {
  status: number;
  detail: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface TopologyNode {
  id: string;
  label: string;
  type: string;
  x?: number;
  y?: number;
  data: Record<string, unknown>;
}

export interface TopologyEdge {
  source: string;
  target: string;
  label?: string;
  data?: Record<string, unknown>;
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface WebSocketEvent {
  event: string;
  data: unknown;
  timestamp: string;
}

export interface NodeSummaryContent {
  attackSurface: string;
  credentialChain: string;
  lateralMovement: string;
  persistence: string;
  riskAssessment: string;
  recommendedNext: string;
}

export interface NodeSummary {
  summary: NodeSummaryContent;
  factCount: number;
  cached: boolean;
  generatedAt: string;
  model: string;
}
