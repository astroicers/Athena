import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { StatusDot } from "@/components/atoms/StatusDot";

describe("StatusDot", () => {
  it("renders with correct color class for alive status", () => {
    const { container } = render(<StatusDot status="alive" />);
    const dot = container.querySelector(".bg-athena-success");
    expect(dot).not.toBeNull();
  });
});
