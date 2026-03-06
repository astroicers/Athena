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
}
