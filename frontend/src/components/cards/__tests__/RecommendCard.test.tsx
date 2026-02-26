import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RecommendCard } from "@/components/cards/RecommendCard";
import { ExecutionEngine, RiskLevel } from "@/types/enums";
import type { PentestGPTRecommendation } from "@/types/recommendation";

const mockRec: PentestGPTRecommendation = {
  id: "rec-1",
  operationId: "op-1",
  oodaIterationId: "iter-1",
  situationAssessment: "Initial access established",
  recommendedTechniqueId: "T1003.001",
  confidence: 0.87,
  options: [
    {
      techniqueId: "T1003.001",
      techniqueName: "LSASS Dump",
      reasoning: "Admin access available",
      riskLevel: RiskLevel.MEDIUM,
      recommendedEngine: ExecutionEngine.CALDERA,
      confidence: 0.87,
      prerequisites: [],
    },
  ],
  reasoningText: "Test reasoning",
  accepted: null,
  createdAt: "2026-02-26T00:00:00Z",
};

describe("RecommendCard", () => {
  it("displays confidence percentage", () => {
    render(<RecommendCard recommendation={mockRec} />);
    expect(screen.getByText("87% confidence")).toBeInTheDocument();
  });
});
