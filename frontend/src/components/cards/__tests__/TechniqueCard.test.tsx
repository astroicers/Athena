// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { TechniqueCard } from "@/components/cards/TechniqueCard";
import { KillChainStage, RiskLevel, TechniqueStatus } from "@/types/enums";
import type { TechniqueWithStatus } from "@/types/technique";

const mockTechnique: TechniqueWithStatus = {
  id: "tech-1",
  mitreId: "T1003.001",
  name: "LSASS Memory Dump",
  tactic: "Credential Access",
  tacticId: "TA0006",
  description: "Dump LSASS process memory to extract credentials",
  killChainStage: KillChainStage.EXPLOIT,
  riskLevel: RiskLevel.MEDIUM,
  c2AbilityId: null,
  platforms: ["windows"],
  latestStatus: TechniqueStatus.SUCCESS,
  latestExecutionId: "exec-1",
};

describe("TechniqueCard", () => {
  it("shows MITRE ID and name", () => {
    render(<TechniqueCard technique={mockTechnique} />, { wrapper: IntlWrapper });
    expect(screen.getByText("T1003.001")).toBeInTheDocument();
    expect(screen.getByText("LSASS Memory Dump")).toBeInTheDocument();
  });
});
