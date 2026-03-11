import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { WarRoomSidePanel } from "../WarRoomSidePanel";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, ...props }: { children: React.ReactNode; href: string }) => (
    <a {...props}>{children}</a>
  ),
}));

const defaultProps = {
  activeTechniqueId: null,
  activeEngine: null,
  activeStatus: null,
  activeTechniqueName: null,
  activeKillChainStage: null,
  activeConfidence: null,
  llmThinking: false,
  llmBackend: null,
  llmLatencyMs: null,
  recommendation: null,
  oodaTimeline: [],
  currentOodaPhase: null,
  agents: [],
  allLogs: [],
  operationId: "op-1",
  onDirectiveSubmit: vi.fn(),
  onOodaTrigger: vi.fn(),
};

describe("WarRoomSidePanel", () => {
  it("renders translated section titles (not raw i18n keys)", () => {
    render(<WarRoomSidePanel {...defaultProps} />, { wrapper: IntlWrapper });

    // These should show translated text, NOT raw keys like "WarRoom.sidePanel.aiDecision"
    // Some labels may appear in both section title and child panel, so use getAllByText
    expect(screen.getAllByText("AI Decision").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Recommendation").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("OODA Timeline").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Agents").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Logs").length).toBeGreaterThanOrEqual(1);
  });

  it("shows 'No agents' when agents list is empty", () => {
    render(<WarRoomSidePanel {...defaultProps} />, { wrapper: IntlWrapper });
    expect(screen.getByText("No agents")).toBeInTheDocument();
  });

  it("shows agent count summary", () => {
    const props = {
      ...defaultProps,
      agents: [
        { id: "a1", paw: "abc", status: "alive", privilege: "user", platform: "linux", lastBeacon: "2026-01-01" },
        { id: "a2", paw: "def", status: "dead", privilege: "root", platform: "linux", lastBeacon: "2026-01-01" },
      ] as any,
    };
    render(<WarRoomSidePanel {...props} />, { wrapper: IntlWrapper });
    // 1 alive agent → "1 active"
    expect(screen.getByText("1 active")).toBeInTheDocument();
  });
});
