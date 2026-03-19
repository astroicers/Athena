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
 * Mermaid configuration matching Athena Deep Gemstone v3 design language.
 * Dark theme with JetBrains Mono, sapphire accent, zinc grays.
 */
export const ATHENA_MERMAID_CONFIG: MermaidConfig = {
  theme: "base",
  themeVariables: {
    darkMode: true,
    background: "#09090B",
    mainBkg: "#18181B",
    secondBkg: "#27272A",
    primaryTextColor: "#D4D4D8",
    secondaryTextColor: "#71717A",
    lineColor: "#1E6091",
    primaryBorderColor: "#27272A",
    primaryColor: "#18181B",
    secondaryColor: "#27272A",
    tertiaryColor: "#18181B",
    nodeBorder: "#27272A",
    nodeTextColor: "#D4D4D8",
    fontFamily: "JetBrains Mono, monospace",
    fontSize: "12px",
    clusterBkg: "#18181B",
    clusterBorder: "#27272A",
    edgeLabelBackground: "#09090B",
    titleColor: "#D4D4D8",
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
 * to ensure Deep Gemstone v3 visual consistency.
 */
export const MERMAID_CSS_OVERRIDES = `
  .mermaid-container .node rect,
  .mermaid-container .node polygon {
    fill: #18181B !important;
    stroke: #27272A !important;
    rx: 6;
    ry: 6;
  }
  .mermaid-container .cluster rect {
    fill: #18181B !important;
    stroke: #27272A !important;
    rx: 8;
    ry: 8;
  }
  .mermaid-container .cluster span {
    color: #71717A !important;
    font-family: JetBrains Mono, monospace !important;
    font-size: 11px !important;
    font-weight: 600 !important;
  }
  .mermaid-container .edgeLabel {
    background-color: #09090B !important;
    color: #71717A !important;
    font-size: 10px !important;
  }
  .mermaid-container .label {
    color: #D4D4D8 !important;
    font-family: JetBrains Mono, monospace !important;
  }
  .mermaid-container .edgePath .path {
    stroke: #1E6091 !important;
    stroke-width: 1.5px;
  }
  .mermaid-container .node.active rect {
    stroke: #1E6091 !important;
    stroke-width: 2px !important;
    filter: drop-shadow(0 0 6px rgba(30, 96, 145, 0.4));
  }
  .mermaid-container .node.healthy rect {
    stroke: #059669 !important;
  }
  .mermaid-container .node.degraded rect {
    stroke: #B45309 !important;
  }
  .mermaid-container .node.critical rect {
    stroke: #B91C1C !important;
  }
  .mermaid-container .edgePath.constraint-edge .path {
    stroke: #B91C1C !important;
    stroke-dasharray: 5, 3;
  }
  .mermaid-container .edgePath.feedback-edge .path {
    stroke: #059669 !important;
    stroke-width: 2px;
  }
`;
