// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import { C5ISRDomain, C5ISRDomainStatus } from "./enums";

export interface DomainMetric {
  name: string;
  value: number;
  weight: number;
  numerator: number | null;
  denominator: number | null;
}

export type RiskSeverity = "CRIT" | "WARN" | "INFO";

export interface RiskVector {
  severity: RiskSeverity;
  message: string;
}

export interface DomainReport {
  executive_summary: string;
  health_pct: number;
  status: string;
  metrics: DomainMetric[];
  asset_roster: Array<Record<string, unknown>>;
  tactical_assessment: string;
  risk_vectors: RiskVector[];
  recommended_actions: string[];
  cross_domain_impacts: string[];
}

export interface C5ISRStatus {
  id: string;
  operationId: string;
  domain: C5ISRDomain;
  status: C5ISRDomainStatus;
  healthPct: number;
  detail: string;
  // Structured metrics for tactical display
  numerator: number | null;
  denominator: number | null;
  metricLabel: string;
  report: DomainReport | null;
}
