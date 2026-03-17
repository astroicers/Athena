// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.

import { describe, it, expect } from "vitest";
import { buildOODAC5ISRFlow } from "@/lib/buildFlowDefinition";
import type { C5ISRStatus } from "@/types/c5isr";
import type { OperationalConstraints } from "@/types/constraint";

function makeDomain(
  domain: string,
  healthPct: number,
  status = "operational",
): C5ISRStatus {
  return {
    id: `id-${domain}`,
    operationId: "op-1",
    domain: domain as C5ISRStatus["domain"],
    status: status as C5ISRStatus["status"],
    healthPct,
    detail: "",
    numerator: null,
    denominator: null,
    metricLabel: "",
  };
}

const HEALTHY_DOMAINS: C5ISRStatus[] = [
  makeDomain("command", 94),
  makeDomain("control", 91),
  makeDomain("comms", 88),
  makeDomain("computers", 85),
  makeDomain("cyber", 81),
  makeDomain("isr", 96),
];

const baseDashboard = { currentPhase: "orient", iterationCount: 3 };

describe("buildOODAC5ISRFlow", () => {
  it("generates valid flowchart header", () => {
    const result = buildOODAC5ISRFlow(baseDashboard, null, HEALTHY_DOMAINS);
    expect(result).toMatch(/^flowchart LR/);
  });

  it("includes OODA subgraph with 4 phases", () => {
    const result = buildOODAC5ISRFlow(baseDashboard, null, HEALTHY_DOMAINS);
    expect(result).toContain('subgraph OODA["OODA Cycle');
    expect(result).toContain("OBS");
    expect(result).toContain("ORI");
    expect(result).toContain("DEC");
    expect(result).toContain("ACT");
    expect(result).toContain("OBS --> ORI --> DEC --> ACT");
  });

  it("highlights active phase with class", () => {
    const result = buildOODAC5ISRFlow(baseDashboard, null, HEALTHY_DOMAINS);
    expect(result).toContain("class ORI active");
  });

  it("includes C5ISR subgraph with 6 domains", () => {
    const result = buildOODAC5ISRFlow(baseDashboard, null, HEALTHY_DOMAINS);
    expect(result).toContain('subgraph C5ISR["C5ISR Domain Health"]');
    expect(result).toContain("CMD");
    expect(result).toContain("CTRL");
    expect(result).toContain("COMMS");
    expect(result).toContain("COMP");
    expect(result).toContain("CYBER");
    expect(result).toContain("ISR");
  });

  it("classifies healthy domains correctly", () => {
    const result = buildOODAC5ISRFlow(baseDashboard, null, HEALTHY_DOMAINS);
    expect(result).toContain("class CMD,CTRL,COMMS,COMP,CYBER,ISR healthy");
  });

  it("classifies degraded/critical domains", () => {
    const mixed = [
      makeDomain("command", 94),
      makeDomain("control", 60, "degraded"),
      makeDomain("comms", 20, "critical"),
      makeDomain("computers", 85),
      makeDomain("cyber", 45, "degraded"),
      makeDomain("isr", 96),
    ];
    const result = buildOODAC5ISRFlow(baseDashboard, null, mixed);
    expect(result).toContain("class CMD,COMP,ISR healthy");
    expect(result).toContain("class CTRL degraded");
    expect(result).toContain("class COMMS,CYBER critical");
  });

  it("omits constraint subgraph when no constraints", () => {
    const result = buildOODAC5ISRFlow(baseDashboard, null, HEALTHY_DOMAINS);
    expect(result).not.toContain("Active Constraints");
  });

  it("includes constraint subgraph when hard limits exist", () => {
    const constraints: OperationalConstraints = {
      warnings: [],
      hardLimits: [
        {
          domain: "comms",
          healthPct: 20,
          rule: "max_parallel_1",
          effect: { max_parallel_override: 1 },
          suggestedAction: "Check MCP tools",
        },
      ],
      orientMaxOptions: 3,
      minConfidenceOverride: null,
      maxParallelOverride: 1,
      blockedTargets: [],
      forcedMode: null,
      noiseBudgetRemaining: 50,
      activeOverrides: [],
    };
    const result = buildOODAC5ISRFlow(baseDashboard, constraints, HEALTHY_DOMAINS);
    expect(result).toContain("Active Constraints");
    expect(result).toContain("HL0");
    expect(result).toContain("COMMS -->|");
    expect(result).toContain('-->|"constrains"|');
  });

  it("shows reduced orient options in OODA node label", () => {
    const constraints: OperationalConstraints = {
      warnings: [],
      hardLimits: [],
      orientMaxOptions: 2,
      minConfidenceOverride: null,
      maxParallelOverride: null,
      blockedTargets: [],
      forcedMode: null,
      noiseBudgetRemaining: 50,
      activeOverrides: [],
    };
    const result = buildOODAC5ISRFlow(baseDashboard, constraints, HEALTHY_DOMAINS);
    expect(result).toContain("2/3 options");
  });

  it("shows min confidence in DECIDE node label", () => {
    const constraints: OperationalConstraints = {
      warnings: [],
      hardLimits: [],
      orientMaxOptions: 3,
      minConfidenceOverride: 0.75,
      maxParallelOverride: null,
      blockedTargets: [],
      forcedMode: null,
      noiseBudgetRemaining: 50,
      activeOverrides: [],
    };
    const result = buildOODAC5ISRFlow(baseDashboard, constraints, HEALTHY_DOMAINS);
    expect(result).toContain("min conf: 0.75");
  });

  it("includes feedback edge from ACT to C5ISR", () => {
    const result = buildOODAC5ISRFlow(baseDashboard, null, HEALTHY_DOMAINS);
    expect(result).toContain("ACT ==>|");
    expect(result).toContain("C5ISR");
  });

  it("shows forced mode in ACT node label", () => {
    const constraints: OperationalConstraints = {
      warnings: [],
      hardLimits: [],
      orientMaxOptions: 3,
      minConfidenceOverride: null,
      maxParallelOverride: null,
      blockedTargets: [],
      forcedMode: "recovery",
      noiseBudgetRemaining: 50,
      activeOverrides: [],
    };
    const result = buildOODAC5ISRFlow(baseDashboard, constraints, HEALTHY_DOMAINS);
    expect(result).toContain("mode: recovery");
  });
});
