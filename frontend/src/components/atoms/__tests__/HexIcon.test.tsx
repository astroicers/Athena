import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HexIcon } from "@/components/atoms/HexIcon";

describe("HexIcon", () => {
  it("renders the icon text", () => {
    render(<HexIcon icon="⬡" />);
    expect(screen.getByText("⬡")).toBeInTheDocument();
  });
});
