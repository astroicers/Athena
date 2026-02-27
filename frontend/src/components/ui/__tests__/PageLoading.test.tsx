import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PageLoading } from "@/components/ui/PageLoading";

describe("PageLoading", () => {
  it("renders INITIALIZING SYSTEMS text", () => {
    render(<PageLoading />);
    expect(screen.getByText("INITIALIZING SYSTEMS")).toBeInTheDocument();
  });

  it("renders 4 animated dots", () => {
    const { container } = render(<PageLoading />);
    const dots = container.querySelectorAll(".rounded-full");
    expect(dots).toHaveLength(4);
  });
});
