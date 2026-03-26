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

import { useCallback, useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import {
  ATHENA_MERMAID_CONFIG,
  MERMAID_CSS_OVERRIDES,
} from "@/lib/mermaidTheme";

let mermaidInitialized = false;

function ensureInit() {
  if (!mermaidInitialized) {
    mermaid.initialize(ATHENA_MERMAID_CONFIG);
    mermaidInitialized = true;
  }
}

interface MermaidRendererProps {
  definition: string;
  className?: string;
}

/**
 * Generic Mermaid diagram renderer with Athena v2 dark theme.
 * Re-renders whenever `definition` changes.
 */
export function MermaidRenderer({
  definition,
  className = "",
}: MermaidRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const renderIdRef = useRef(0);

  const renderDiagram = useCallback(async (def: string) => {
    ensureInit();
    const id = `mermaid-${++renderIdRef.current}`;
    try {
      const { svg: rendered } = await mermaid.render(id, def);
      setSvg(rendered);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mermaid render failed");
      // Clean up failed render element
      const el = document.getElementById(id);
      el?.remove();
    }
  }, []);

  useEffect(() => {
    if (definition.trim()) {
      renderDiagram(definition);
    }
  }, [definition, renderDiagram]);

  if (error) {
    return (
      <div
        className={`rounded-[var(--radius)] border p-4 font-mono text-athena-floor bg-athena-surface text-athena-error ${className}`}
        style={{
          borderColor: "color-mix(in srgb, var(--color-error) 40%, transparent)",
        }}
      >
        Diagram error: {error}
      </div>
    );
  }

  return (
    <>
      <style>{MERMAID_CSS_OVERRIDES}</style>
      <div
        ref={containerRef}
        className={`mermaid-container rounded-[var(--radius)] border overflow-hidden bg-athena-surface border-[var(--color-border)] p-3 ${className}`}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    </>
  );
}
