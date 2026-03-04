// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { AIDecisionPanel } from "../AIDecisionPanel";
import { KillChainStage } from "@/types/enums";

const nullProps = {
  activeTechniqueId: null,
  activeEngine: null,
  activeStatus: null,
  activeTechniqueName: null,
  activeKillChainStage: null,
  activeConfidence: null,
};

describe("AIDecisionPanel", () => {
  it("shows empty state when no active technique", () => {
    render(<AIDecisionPanel {...nullProps} />, { wrapper: IntlWrapper });
    expect(screen.getByText(/NO ACTIVE TECHNIQUE/i)).toBeTruthy();
  });

  it("shows techniqueId when provided", () => {
    render(<AIDecisionPanel {...nullProps} activeTechniqueId="T1595.001" />, { wrapper: IntlWrapper });
    expect(screen.getByText("T1595.001")).toBeTruthy();
  });

  it("applies animate-pulse class when status is running", () => {
    const { container } = render(
      <AIDecisionPanel {...nullProps} activeTechniqueId="T1595.001" activeStatus="running" />,
      { wrapper: IntlWrapper },
    );
    const pulsingEl = container.querySelector(".animate-pulse");
    expect(pulsingEl).toBeTruthy();
  });

  it("shows engine label when provided", () => {
    render(<AIDecisionPanel {...nullProps} activeTechniqueId="T1595.001" activeEngine="c2" />, { wrapper: IntlWrapper });
    expect(screen.getByText(/C2/i)).toBeTruthy();
  });

  it("shows confidence percentage when provided", () => {
    render(<AIDecisionPanel {...nullProps} activeTechniqueId="T1595.001" activeConfidence={0.87} />, { wrapper: IntlWrapper });
    expect(screen.getByText(/87%/)).toBeTruthy();
  });
});
