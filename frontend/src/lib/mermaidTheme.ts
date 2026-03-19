// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import type { MermaidConfig } from "mermaid";

/**
 * Mermaid configuration matching Athena v2 design language.
 * Dark theme with IBM Plex Mono, accent blue, surface grays.
 */
export const ATHENA_MERMAID_CONFIG: MermaidConfig = {
  theme: "base",
  themeVariables: {
    darkMode: true,
    background: "#0a0e17",
    mainBkg: "#111827",
    secondBkg: "#1e293b",
    primaryTextColor: "#e5e7eb",
    secondaryTextColor: "#9ca3af",
    lineColor: "#3b82f6",
    primaryBorderColor: "#1f2937",
    primaryColor: "#111827",
    secondaryColor: "#1e293b",
    tertiaryColor: "#0f1729",
    nodeBorder: "#1f2937",
    nodeTextColor: "#e5e7eb",
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: "12px",
    clusterBkg: "#0f172a",
    clusterBorder: "#1f2937",
    edgeLabelBackground: "#0a0e17",
    titleColor: "#e5e7eb",
  },
  flowchart: {
    htmlLabels: true,
    curve: "basis",
    padding: 12,
    nodeSpacing: 40,
    rankSpacing: 50,
  },
  securityLevel: "loose",
  startOnLoad: false,
};

/**
 * CSS overrides injected into the Mermaid SVG container
 * to ensure v2 visual consistency.
 */
export const MERMAID_CSS_OVERRIDES = `
  .mermaid-container .node rect,
  .mermaid-container .node polygon {
    fill: #111827 !important;
    stroke: #1f2937 !important;
    rx: 6;
    ry: 6;
  }
  .mermaid-container .cluster rect {
    fill: #0f172a !important;
    stroke: #1f2937 !important;
    rx: 8;
    ry: 8;
  }
  .mermaid-container .cluster span {
    color: #9ca3af !important;
    font-family: IBM Plex Mono, monospace !important;
    font-size: 11px !important;
    font-weight: 600 !important;
  }
  .mermaid-container .edgeLabel {
    background-color: #0a0e17 !important;
    color: #9ca3af !important;
    font-size: 10px !important;
  }
  .mermaid-container .label {
    color: #e5e7eb !important;
    font-family: IBM Plex Mono, monospace !important;
  }
  .mermaid-container .edgePath .path {
    stroke: #3b82f6 !important;
    stroke-width: 1.5px;
  }
  .mermaid-container .node.active rect {
    stroke: #3b82f6 !important;
    stroke-width: 2px !important;
    filter: drop-shadow(0 0 6px rgba(59, 130, 246, 0.4));
  }
  .mermaid-container .node.healthy rect {
    stroke: #22C55E !important;
  }
  .mermaid-container .node.degraded rect {
    stroke: #F59E0B !important;
  }
  .mermaid-container .node.critical rect {
    stroke: #EF4444 !important;
  }
  .mermaid-container .edgePath.constraint-edge .path {
    stroke: #EF4444 !important;
    stroke-dasharray: 5, 3;
  }
  .mermaid-container .edgePath.feedback-edge .path {
    stroke: #22C55E !important;
    stroke-width: 2px;
  }
`;
