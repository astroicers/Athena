import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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
  calderaAbilityId: null,
  platforms: ["windows"],
  latestStatus: TechniqueStatus.SUCCESS,
  latestExecutionId: "exec-1",
};

describe("TechniqueCard", () => {
  it("shows MITRE ID and name", () => {
    render(<TechniqueCard technique={mockTechnique} />);
    expect(screen.getByText("T1003.001")).toBeInTheDocument();
    expect(screen.getByText("LSASS Memory Dump")).toBeInTheDocument();
  });
});
