// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import type { Technique } from "@/types/technique";
import type { ToolRegistryEntry } from "@/types/tool";

/** Canonical MITRE ATT&CK tactic order (14 tactics). */
export const TACTIC_ORDER = [
  "reconnaissance",
  "resource-development",
  "initial-access",
  "execution",
  "persistence",
  "privilege-escalation",
  "defense-evasion",
  "credential-access",
  "discovery",
  "lateral-movement",
  "collection",
  "command-and-control",
  "exfiltration",
  "impact",
] as const;

/** Map MITRE tactic IDs → slugs. */
export const TACTIC_ID_TO_SLUG: Record<string, string> = {
  TA0043: "reconnaissance",
  TA0042: "resource-development",
  TA0001: "initial-access",
  TA0002: "execution",
  TA0003: "persistence",
  TA0004: "privilege-escalation",
  TA0005: "defense-evasion",
  TA0006: "credential-access",
  TA0007: "discovery",
  TA0008: "lateral-movement",
  TA0009: "collection",
  TA0011: "command-and-control",
  TA0010: "exfiltration",
  TA0040: "impact",
};

/** Reverse: slug → tactic ID. */
export const SLUG_TO_TACTIC_ID: Record<string, string> = Object.fromEntries(
  Object.entries(TACTIC_ID_TO_SLUG).map(([k, v]) => [v, k]),
);

/** Normalize a free-form tactic name into a slug. */
export function normalizeTactic(tactic: string): string {
  return tactic.toLowerCase().replace(/\s+/g, "-");
}

/** Convert a slug like "credential-access" to "Credential Access". */
export function tacticLabel(tactic: string): string {
  return tactic
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Key used for tools that have no MITRE technique mappings. */
export const GENERAL_TACTIC_KEY = "__general__";

/**
 * Group tools by MITRE tactic using the technique catalog as a bridge.
 * A tool can appear in multiple tactics if its techniques span them.
 * Tools with empty mitreTechniques go into GENERAL_TACTIC_KEY.
 */
export function groupToolsByTactic(
  tools: ToolRegistryEntry[],
  techniques: Technique[],
): Record<string, ToolRegistryEntry[]> {
  // Build mitreId → tacticSlug lookup
  const mitreToTactic = new Map<string, string>();
  for (const tech of techniques) {
    const slug = TACTIC_ID_TO_SLUG[tech.tacticId] || normalizeTactic(tech.tactic);
    mitreToTactic.set(tech.mitreId, slug);
  }

  const result: Record<string, ToolRegistryEntry[]> = {};

  for (const tool of tools) {
    if (!tool.mitreTechniques || tool.mitreTechniques.length === 0) {
      if (!result[GENERAL_TACTIC_KEY]) result[GENERAL_TACTIC_KEY] = [];
      result[GENERAL_TACTIC_KEY].push(tool);
      continue;
    }

    const seenTactics = new Set<string>();
    for (const techId of tool.mitreTechniques) {
      const tactic = mitreToTactic.get(techId);
      if (tactic && !seenTactics.has(tactic)) {
        seenTactics.add(tactic);
        if (!result[tactic]) result[tactic] = [];
        result[tactic].push(tool);
      }
    }

    // If none of the technique IDs matched, put in general
    if (seenTactics.size === 0) {
      if (!result[GENERAL_TACTIC_KEY]) result[GENERAL_TACTIC_KEY] = [];
      result[GENERAL_TACTIC_KEY].push(tool);
    }
  }

  return result;
}

/**
 * Filter tools whose mitreTechniques include the given MITRE technique ID.
 */
export function getToolsForTechnique(
  tools: ToolRegistryEntry[],
  mitreId: string,
): ToolRegistryEntry[] {
  return tools.filter(
    (t) => t.mitreTechniques && t.mitreTechniques.includes(mitreId),
  );
}
