// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import type { C5ISRStatus } from "@/types/c5isr";
import type { OperationalConstraints } from "@/types/constraint";

interface OodaDashboardInput {
  currentPhase: string;
  iterationCount: number;
}

/** Escape special characters for Mermaid labels */
function esc(s: string): string {
  return s.replace(/"/g, "&quot;").replace(/#/g, "&num;");
}

/** Map a constraint rule to the OODA phase it affects */
function ruleToPhase(rule: string): string {
  if (rule.includes("orient")) return "ORI";
  if (rule.includes("confidence")) return "DEC";
  return "ACT";
}

/** Classify domain health into a CSS class */
function healthClass(pct: number): string {
  if (pct >= 80) return "healthy";
  if (pct >= 50) return "degraded";
  return "critical";
}

/** Health status symbol */
function healthSymbol(pct: number): string {
  if (pct >= 80) return "OK";
  if (pct >= 50) return "WARN";
  return "CRIT";
}

/** Domain short names for Mermaid node IDs */
const DOMAIN_IDS: Record<string, string> = {
  command: "CMD",
  control: "CTRL",
  comms: "COMMS",
  computers: "COMP",
  cyber: "CYBER",
  isr: "ISR",
};

/**
 * Build a Mermaid flowchart definition showing OODA <-> C5ISR mutual influence.
 *
 * The diagram dynamically reflects:
 * - Current OODA phase (highlighted node)
 * - C5ISR domain health (color-coded nodes)
 * - Active constraints and their impact edges
 * - Feedback loop from ACT back to C5ISR
 */
export function buildOODAC5ISRFlow(
  dashboard: OodaDashboardInput,
  constraints: OperationalConstraints | null,
  domains: C5ISRStatus[],
): string {
  const phase = dashboard.currentPhase?.toLowerCase() ?? "idle";
  const iter = dashboard.iterationCount ?? 0;
  const lines: string[] = [];

  lines.push("flowchart LR");

  // --- OODA Subgraph ---
  lines.push(`  subgraph OODA["OODA Cycle &num;${iter}"]`);
  lines.push("    direction TB");

  const orientLabel =
    constraints && constraints.orientMaxOptions < 3
      ? `ORIENT\\n(${constraints.orientMaxOptions}/3 options)`
      : "ORIENT\\n(analysis)";
  const decideLabel =
    constraints?.minConfidenceOverride != null
      ? `DECIDE\\n(min conf: ${constraints.minConfidenceOverride.toFixed(2)})`
      : "DECIDE\\n(evaluation)";
  const actLabel =
    constraints?.maxParallelOverride != null
      ? `ACT\\n(parallel: ${constraints.maxParallelOverride})`
      : constraints?.forcedMode
        ? `ACT\\n(mode: ${constraints.forcedMode})`
        : "ACT\\n(execution)";

  lines.push(`    OBS["OBSERVE\\n(collection)"]`);
  lines.push(`    ORI["${esc(orientLabel)}"]`);
  lines.push(`    DEC["${esc(decideLabel)}"]`);
  lines.push(`    ACT["${esc(actLabel)}"]`);
  lines.push("    OBS --> ORI --> DEC --> ACT");
  lines.push('    ACT -.->|"feedback"| OBS');
  lines.push("  end");

  // --- C5ISR Subgraph ---
  lines.push('  subgraph C5ISR["C5ISR Domain Health"]');
  lines.push("    direction TB");

  const domainMap = new Map<string, C5ISRStatus>(domains.map((d) => [d.domain as string, d]));
  const domainOrder = ["command", "control", "comms", "computers", "cyber", "isr"];

  for (const domainKey of domainOrder) {
    const d = domainMap.get(domainKey);
    const id = DOMAIN_IDS[domainKey] ?? domainKey.toUpperCase();
    const pct = d?.healthPct ?? 0;
    const sym = healthSymbol(pct);
    lines.push(`    ${id}["${id}\\n${Math.round(pct)}%% ${sym}"]`);
  }

  lines.push("  end");

  // --- Constraints Subgraph (conditional) ---
  const allConstraints = [
    ...(constraints?.warnings ?? []),
    ...(constraints?.hardLimits ?? []),
  ];

  if (allConstraints.length > 0 && constraints) {
    lines.push('  subgraph CONSTR["Active Constraints"]');
    lines.push("    direction TB");

    // Add constraint nodes from hard_limits
    constraints.hardLimits.forEach((limit, i) => {
      const nodeId = `HL${i}`;
      lines.push(`    ${nodeId}["${esc(limit.rule)}"]`);
    });

    // Add warning nodes
    constraints.warnings.forEach((warn, i) => {
      const nodeId = `W${i}`;
      lines.push(`    ${nodeId}["${esc(warn.message).substring(0, 40)}"]`);
    });

    lines.push("  end");

    // Draw edges: degraded domain -> constraint -> OODA phase
    constraints.hardLimits.forEach((limit, i) => {
      const domId = DOMAIN_IDS[limit.domain] ?? limit.domain.toUpperCase();
      const nodeId = `HL${i}`;
      const targetPhase = ruleToPhase(limit.rule);
      lines.push(
        `  ${domId} -->|"health ${Math.round(limit.healthPct)}%%"| ${nodeId}`,
      );
      lines.push(`  ${nodeId} -->|"constrains"| ${targetPhase}`);
    });

    constraints.warnings.forEach((warn, i) => {
      const domId = DOMAIN_IDS[warn.domain] ?? warn.domain.toUpperCase();
      const nodeId = `W${i}`;
      const targetPhase = "ORI";
      lines.push(
        `  ${domId} -.->|"health ${Math.round(warn.healthPct)}%%"| ${nodeId}`,
      );
      lines.push(`  ${nodeId} -.->|"advisory"| ${targetPhase}`);
    });
  }

  // --- Feedback edge: ACT -> C5ISR ---
  lines.push('  ACT ==>|"results update\\nhealth"| C5ISR');

  // --- Style classes ---
  lines.push("  classDef active stroke:#3b82f6,stroke-width:2px,fill:#111827");
  lines.push("  classDef healthy stroke:#22C55E,fill:#111827");
  lines.push("  classDef degraded stroke:#F59E0B,fill:#111827");
  lines.push("  classDef critical stroke:#EF4444,fill:#111827");

  // Apply active class to current OODA phase
  const phaseMap: Record<string, string> = {
    observe: "OBS",
    orient: "ORI",
    decide: "DEC",
    act: "ACT",
  };
  const activeNode = phaseMap[phase];
  if (activeNode) {
    lines.push(`  class ${activeNode} active`);
  }

  // Apply health classes to C5ISR domains
  const healthGroups: Record<string, string[]> = {
    healthy: [],
    degraded: [],
    critical: [],
  };

  for (const domainKey of domainOrder) {
    const d = domainMap.get(domainKey);
    const id = DOMAIN_IDS[domainKey] ?? domainKey.toUpperCase();
    const cls = healthClass(d?.healthPct ?? 0);
    healthGroups[cls].push(id);
  }

  for (const [cls, ids] of Object.entries(healthGroups)) {
    if (ids.length > 0) {
      lines.push(`  class ${ids.join(",")} ${cls}`);
    }
  }

  return lines.join("\n");
}
