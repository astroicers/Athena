// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { OODAPhase } from "./enums";

export interface OODAIteration {
  id: string;
  operationId: string;
  iterationNumber: number;
  phase: OODAPhase;
  observeSummary: string | null;
  orientSummary: string | null;
  decideSummary: string | null;
  actSummary: string | null;
  recommendationId: string | null;
  techniqueExecutionId: string | null;
  startedAt: string;
  completedAt: string | null;
}

export interface PhaseDetail {
  factsCount?: number;
  facts?: Array<{ trait: string; value: string; category: string }>;
  rawSummary?: string;
  situationAssessment?: string;
  recommendedTechniqueId?: string;
  confidence?: number;
  reasoningText?: string;
  options?: Array<{
    techniqueId: string;
    techniqueName: string;
    reasoning: string;
    riskLevel: string;
    recommendedEngine: string;
    confidence: number;
    prerequisites: string[];
  }>;
  reason?: string;
  confidenceBreakdown?: Record<string, number>;
  noiseLevel?: string;
  riskLevel?: string;
  matrixAction?: string;
  techniqueId?: string;
  engine?: string;
  status?: string;
  resultSummary?: string;
  errorMessage?: string;
  factsCollectedCount?: number;
  failureCategory?: string;
}

export interface OODATimelineEntry {
  iterationNumber: number;
  phase: string;
  summary: string;
  timestamp: string;
  targetId?: string;
  targetHostname?: string;
  targetIp?: string;
  detail?: PhaseDetail;
}
