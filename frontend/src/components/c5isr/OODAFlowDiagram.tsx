// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use client";

import { useMemo } from "react";
import { MermaidRenderer } from "./MermaidRenderer";
import { buildOODAC5ISRFlow } from "@/lib/buildFlowDefinition";
import type { C5ISRStatus } from "@/types/c5isr";
import type { OperationalConstraints } from "@/types/constraint";

interface OodaDashboard {
  currentPhase: string;
  iterationCount: number;
}

interface OODAFlowDiagramProps {
  dashboard: OodaDashboard | null;
  constraints: OperationalConstraints | null;
  c5isrDomains: C5ISRStatus[];
}

/**
 * Real-time Mermaid flowchart showing OODA <-> C5ISR mutual influence.
 * Re-generates the diagram definition whenever data changes.
 */
export function OODAFlowDiagram({
  dashboard,
  constraints,
  c5isrDomains,
}: OODAFlowDiagramProps) {
  const definition = useMemo(() => {
    if (!dashboard) return "";
    return buildOODAC5ISRFlow(dashboard, constraints, c5isrDomains);
  }, [dashboard, constraints, c5isrDomains]);

  if (!definition) {
    return (
      <div
        className="rounded-[var(--radius)] border font-mono text-athena-floor flex items-center justify-center bg-athena-surface border-[var(--color-border)] text-athena-text-tertiary p-6 min-h-[120px]"
      >
        Waiting for OODA data...
      </div>
    );
  }

  return (
    <div>
      <span
        className="font-mono text-athena-floor font-bold uppercase tracking-wider mb-2 block text-[#ffffff20]"
      >
        DECISION FLOW
      </span>
      <MermaidRenderer definition={definition} />
    </div>
  );
}
