import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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

function renderPanel(
  rec: OrientRecommendation | null,
  onAccepted?: () => void,
) {
  return render(
    <ToastProvider>
      <RecommendationPanel
        recommendation={rec}
        operationId="op-1"
        onAccepted={onAccepted}
      />
    </ToastProvider>,
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
    expect(screen.getByText("85%")).toBeInTheDocument();
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

  it("accept calls API and triggers onAccepted", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      }),
    );
    const onAccepted = vi.fn();
    renderPanel(mockRec, onAccepted);
    fireEvent.click(screen.getByText("ACCEPT RECOMMENDATION"));
    await waitFor(() => expect(onAccepted).toHaveBeenCalledOnce());
  });

  it("shows ACCEPTED badge when already decided", () => {
    renderPanel({ ...mockRec, accepted: true });
    expect(screen.getByText("ACCEPTED")).toBeInTheDocument();
    expect(
      screen.queryByText("ACCEPT RECOMMENDATION"),
    ).not.toBeInTheDocument();
  });
});
