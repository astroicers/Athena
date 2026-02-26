// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

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
