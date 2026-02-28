// Copyright 2026 Athena Contributors
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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
    render(<AIDecisionPanel {...nullProps} />);
    expect(screen.getByText(/NO ACTIVE TECHNIQUE/i)).toBeTruthy();
  });

  it("shows techniqueId when provided", () => {
    render(<AIDecisionPanel {...nullProps} activeTechniqueId="T1595.001" />);
    expect(screen.getByText("T1595.001")).toBeTruthy();
  });

  it("applies animate-pulse class when status is running", () => {
    const { container } = render(
      <AIDecisionPanel {...nullProps} activeTechniqueId="T1595.001" activeStatus="running" />
    );
    const pulsingEl = container.querySelector(".animate-pulse");
    expect(pulsingEl).toBeTruthy();
  });

  it("shows engine label when provided", () => {
    render(<AIDecisionPanel {...nullProps} activeTechniqueId="T1595.001" activeEngine="caldera" />);
    expect(screen.getByText(/CALDERA/i)).toBeTruthy();
  });

  it("shows confidence percentage when provided", () => {
    render(<AIDecisionPanel {...nullProps} activeTechniqueId="T1595.001" activeConfidence={0.87} />);
    expect(screen.getByText(/87%/)).toBeTruthy();
  });
});
