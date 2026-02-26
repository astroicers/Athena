import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OODATimeline } from "@/components/ooda/OODATimeline";
import type { OODATimelineEntry } from "@/types/ooda";

describe("OODATimeline", () => {
  it("renders timeline entries", () => {
    const entries: OODATimelineEntry[] = [
      { iterationNumber: 1, phase: "observe", summary: "Scanned 5 hosts", timestamp: "2026-02-26T14:00:00Z" },
      { iterationNumber: 1, phase: "orient", summary: "Analyzed results", timestamp: "2026-02-26T14:01:00Z" },
    ];
    render(<OODATimeline entries={entries} />);
    expect(screen.getByText("Scanned 5 hosts")).toBeInTheDocument();
    expect(screen.getByText("Analyzed results")).toBeInTheDocument();
  });
});
