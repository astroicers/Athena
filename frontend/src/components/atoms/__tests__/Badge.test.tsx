import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/atoms/Badge";

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>ACTIVE</Badge>);
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  });

  it("applies variant styles", () => {
    render(<Badge variant="success">OK</Badge>);
    expect(screen.getByText("OK").className).toContain("text-athena-success");
  });
});
