// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

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

export interface OODATimelineEntry {
  iterationNumber: number;
  phase: string;
  summary: string;
  timestamp: string;
}
