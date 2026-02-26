import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OODAIndicator } from "@/components/ooda/OODAIndicator";
import { OODAPhase } from "@/types/enums";

describe("OODAIndicator", () => {
  it("highlights the active phase", () => {
    render(<OODAIndicator currentPhase={OODAPhase.ORIENT} />);
    const orient = screen.getByText("ORIENT");
    expect(orient.closest("div")).toHaveClass("bg-athena-accent");
  });
});
