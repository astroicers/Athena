// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { AttackSituationDiagram } from "@/components/situation/AttackSituationDiagram";
import { KillChainStage, TechniqueStatus, RiskLevel } from "@/types/enums";
import type { OODAPhase } from "@/types/enums";
import type { TechniqueWithStatus } from "@/types/technique";

// --- helpers ----------------------------------------------------------------

function makeTechnique(
  overrides: Partial<TechniqueWithStatus> & { killChainStage: KillChainStage },
): TechniqueWithStatus {
  return {
    id: `tech-${Math.random().toString(36).slice(2, 8)}`,
    mitreId: "T1234",
    name: "Test Technique",
    tactic: "test",
    tacticId: "TA0001",
    description: null,
    riskLevel: RiskLevel.MEDIUM,
    c2AbilityId: null,
    platforms: ["linux"],
    latestStatus: null,
    latestExecutionId: null,
    ...overrides,
  };
}

const EMPTY_PROPS = {
  techniques: [] as TechniqueWithStatus[],
  oodaPhase: null as OODAPhase | null,
  executionUpdate: null,
  c5isrDomains: [] as Array<{ domain: string; healthPct: number }>,
};

const KILL_CHAIN_LABELS = [
  "RECON",
  "WEAPON",
  "DELIVER",
  "EXPLOIT",
  "INSTALL",
  "C2",
  "ACTION",
];

// --- tests ------------------------------------------------------------------

describe("AttackSituationDiagram", () => {
  it("renders without crashing with empty data", () => {
    const { container } = render(
      <AttackSituationDiagram {...EMPTY_PROPS} />,
      { wrapper: IntlWrapper },
    );
    // The main SVG element should be present
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("renders all 7 Kill Chain stage labels", () => {
    render(<AttackSituationDiagram {...EMPTY_PROPS} />, {
      wrapper: IntlWrapper,
    });

    for (const label of KILL_CHAIN_LABELS) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("renders 7 stage node groups", () => {
    const { container } = render(
      <AttackSituationDiagram {...EMPTY_PROPS} />,
      { wrapper: IntlWrapper },
    );

    // Each SituationNode renders a <g transform="translate(...)"> with the label text.
    // Count the label texts inside the SVG as a proxy for node count.
    const svgEl = container.querySelector("svg")!;
    const matchingTexts = KILL_CHAIN_LABELS.filter((label) => {
      const els = svgEl.querySelectorAll("text");
      return Array.from(els).some((el) => el.textContent === label);
    });
    expect(matchingTexts).toHaveLength(7);
  });

  it("renders 6 edges between stages", () => {
    const { container } = render(
      <AttackSituationDiagram {...EMPTY_PROPS} />,
      { wrapper: IntlWrapper },
    );

    // Each SituationEdge renders a visible <path> with a stroke url(#edge-grad-N).
    // The edge group also contains a hidden reference path and a visible path.
    // We look for linearGradient IDs edge-grad-0 through edge-grad-5.
    const svgEl = container.querySelector("svg")!;
    for (let i = 0; i < 6; i++) {
      const grad = svgEl.querySelector(`#edge-grad-${i}`);
      expect(grad).toBeInTheDocument();
    }
    // Verify there is no 7th edge gradient
    expect(svgEl.querySelector("#edge-grad-6")).toBeNull();
  });

  it("displays technique counts on nodes when techniques are provided", () => {
    const techniques: TechniqueWithStatus[] = [
      makeTechnique({
        killChainStage: KillChainStage.RECON,
        latestStatus: TechniqueStatus.SUCCESS,
      }),
      makeTechnique({
        killChainStage: KillChainStage.RECON,
        latestStatus: TechniqueStatus.FAILED,
      }),
      makeTechnique({
        killChainStage: KillChainStage.RECON,
        latestStatus: TechniqueStatus.SUCCESS,
      }),
    ];

    render(
      <AttackSituationDiagram
        {...EMPTY_PROPS}
        techniques={techniques}
      />,
      { wrapper: IntlWrapper },
    );

    // RECON node should show "2/3" (2 successes out of 3 total)
    expect(screen.getByText("2/3")).toBeInTheDocument();
  });

  it("shows em-dash for stages with no techniques", () => {
    const { container } = render(
      <AttackSituationDiagram {...EMPTY_PROPS} />,
      { wrapper: IntlWrapper },
    );

    // All 7 stages are empty, so each renders "\u2014" (em-dash)
    const svgEl = container.querySelector("svg")!;
    const emDashes = Array.from(svgEl.querySelectorAll("text")).filter(
      (el) => el.textContent === "\u2014",
    );
    expect(emDashes).toHaveLength(7);
  });

  it("renders the C5ISR health bar section", () => {
    const c5isrDomains = [
      { domain: "command", healthPct: 85 },
      { domain: "control", healthPct: 70 },
      { domain: "comms", healthPct: 60 },
      { domain: "computers", healthPct: 90 },
      { domain: "cyber", healthPct: 75 },
      { domain: "isr", healthPct: 80 },
    ];

    const { container } = render(
      <AttackSituationDiagram {...EMPTY_PROPS} c5isrDomains={c5isrDomains} />,
      { wrapper: IntlWrapper },
    );

    // C5ISRMiniBar is rendered outside the SVG, inside a border-t div
    // Verify the container has content beyond just the SVG
    const borderDivs = container.querySelectorAll(".border-t");
    expect(borderDivs.length).toBeGreaterThan(0);
  });

  it("displays header with title and progress", () => {
    render(<AttackSituationDiagram {...EMPTY_PROPS} />, {
      wrapper: IntlWrapper,
    });

    expect(screen.getByText("Attack Situation Diagram")).toBeInTheDocument();
    // With no techniques, progress should be 0%
    expect(screen.getByText("Progress: 0%")).toBeInTheDocument();
  });

  it("shows correct progress percentage when stages have successes", () => {
    const techniques: TechniqueWithStatus[] = [
      makeTechnique({
        killChainStage: KillChainStage.RECON,
        latestStatus: TechniqueStatus.SUCCESS,
      }),
      makeTechnique({
        killChainStage: KillChainStage.EXPLOIT,
        latestStatus: TechniqueStatus.SUCCESS,
      }),
    ];

    render(
      <AttackSituationDiagram
        {...EMPTY_PROPS}
        techniques={techniques}
      />,
      { wrapper: IntlWrapper },
    );

    // 2 out of 7 stages have successes => ~29%
    expect(screen.getByText("Progress: 29%")).toBeInTheDocument();
  });

  it("applies pulse animation class to active stage nodes", () => {
    const techniques: TechniqueWithStatus[] = [
      makeTechnique({
        killChainStage: KillChainStage.DELIVER,
        latestStatus: TechniqueStatus.RUNNING,
      }),
    ];

    const { container } = render(
      <AttackSituationDiagram
        {...EMPTY_PROPS}
        techniques={techniques}
      />,
      { wrapper: IntlWrapper },
    );

    // Active nodes get the situation-node-pulse class on their polygon/text elements
    const pulsingElements = container.querySelectorAll(".situation-node-pulse");
    expect(pulsingElements.length).toBeGreaterThan(0);
  });

  it("shows running indicator text for stages with running techniques", () => {
    const techniques: TechniqueWithStatus[] = [
      makeTechnique({
        killChainStage: KillChainStage.RECON,
        latestStatus: TechniqueStatus.RUNNING,
      }),
      makeTechnique({
        killChainStage: KillChainStage.RECON,
        latestStatus: TechniqueStatus.RUNNING,
      }),
    ];

    render(
      <AttackSituationDiagram
        {...EMPTY_PROPS}
        techniques={techniques}
      />,
      { wrapper: IntlWrapper },
    );

    expect(screen.getByText("2 running")).toBeInTheDocument();
  });
});
