import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MITRECell } from "@/components/mitre/MITRECell";
import { TechniqueStatus } from "@/types/enums";

describe("MITRECell", () => {
  it("renders MITRE ID with success color class", () => {
    render(
      <MITRECell mitreId="T1003.001" name="LSASS Dump" status={TechniqueStatus.SUCCESS} />,
    );
    expect(screen.getByText("T1003.001")).toBeInTheDocument();
    const button = screen.getByRole("button");
    expect(button.className).toContain("bg-athena-success");
  });
});
