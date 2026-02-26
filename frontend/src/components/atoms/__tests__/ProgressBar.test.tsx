import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { ProgressBar } from "@/components/atoms/ProgressBar";

describe("ProgressBar", () => {
  it("renders with correct width percentage", () => {
    const { container } = render(<ProgressBar value={75} />);
    const bar = container.querySelector("[style]") as HTMLElement;
    expect(bar.style.width).toBe("75%");
  });

  it("clamps to 0% for zero value", () => {
    const { container } = render(<ProgressBar value={0} />);
    const bar = container.querySelector("[style]") as HTMLElement;
    expect(bar.style.width).toBe("0%");
  });
});
