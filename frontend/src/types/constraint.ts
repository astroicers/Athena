// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

export interface ConstraintWarning {
  domain: string;
  healthPct: number;
  message: string;
}

export interface ConstraintLimit {
  domain: string;
  healthPct: number;
  rule: string;
  effect: Record<string, unknown>;
  suggestedAction: string;
}

export interface OperationalConstraints {
  warnings: ConstraintWarning[];
  hardLimits: ConstraintLimit[];
  orientMaxOptions: number;
  minConfidenceOverride: number | null;
  maxParallelOverride: number | null;
  blockedTargets: string[];
  forcedMode: string | null;
  noiseBudgetRemaining: number;
  activeOverrides: string[];
}
