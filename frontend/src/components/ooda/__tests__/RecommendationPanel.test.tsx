import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { ToastProvider } from "@/contexts/ToastContext";
import { RecommendationPanel } from "@/components/ooda/RecommendationPanel";
import type { OrientRecommendation } from "@/types/recommendation";
import { RiskLevel, ExecutionEngine } from "@/types/enums";

const mockRec: OrientRecommendation = {
  id: "rec-1",
  operationId: "op-1",
  oodaIterationId: "ooda-1",
  situationAssessment: "Test assessment",
  recommendedTechniqueId: "T1003.001",
  confidence: 0.85,
  options: [
    {
      techniqueId: "T1003.001",
      techniqueName: "LSASS Memory",
      reasoning: "Best option because...",
      riskLevel: RiskLevel.MEDIUM,
      recommendedEngine: ExecutionEngine.C2,
      confidence: 0.85,
      prerequisites: ["Admin access"],
    },
    {
      techniqueId: "T1134.001",
      techniqueName: "Token Impersonation",
      reasoning: "Alternative option",
      riskLevel: RiskLevel.LOW,
      recommendedEngine: ExecutionEngine.C2,
      confidence: 0.65,
      prerequisites: [],
    },
  ],
  reasoningText: "Overall reasoning",
  accepted: null,
  createdAt: "2026-01-01T00:00:00Z",
};

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <IntlWrapper>
      <ToastProvider>{children}</ToastProvider>
    </IntlWrapper>
  );
}

function renderPanel(rec: OrientRecommendation | null) {
  return render(
    <RecommendationPanel recommendation={rec} />,
    { wrapper: Wrapper },
  );
}

describe("RecommendationPanel", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows empty state when recommendation is null", () => {
    renderPanel(null);
    expect(
      screen.getByText(/No recommendation available/),
    ).toBeInTheDocument();
  });

  it("renders situation assessment and options", () => {
    renderPanel(mockRec);
    expect(screen.getByText("Test assessment")).toBeInTheDocument();
    expect(screen.getByText("T1003.001")).toBeInTheDocument();
    expect(screen.getByText("RECOMMENDED")).toBeInTheDocument();
    expect(screen.getAllByText("85%").length).toBeGreaterThan(0);
  });

  it("expands option on click to show reasoning", () => {
    renderPanel(mockRec);
    expect(
      screen.queryByText("Best option because..."),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("LSASS Memory"));
    expect(screen.getByText("Best option because...")).toBeInTheDocument();
    expect(screen.getByText(/Admin access/)).toBeInTheDocument();
  });

  it("does not show ACCEPT RECOMMENDATION button", () => {
    renderPanel(mockRec);
    expect(
      screen.queryByText("ACCEPT RECOMMENDATION"),
    ).not.toBeInTheDocument();
  });

  it("shows ACCEPTED badge when already decided", () => {
    renderPanel({ ...mockRec, accepted: true });
    expect(screen.getByText("ACCEPTED")).toBeInTheDocument();
  });
});
