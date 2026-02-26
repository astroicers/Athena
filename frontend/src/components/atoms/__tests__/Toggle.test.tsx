import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Toggle } from "@/components/atoms/Toggle";

describe("Toggle", () => {
  it("renders with label text", () => {
    render(<Toggle checked={false} onChange={() => {}} label="Auto mode" />);
    expect(screen.getByText("Auto mode")).toBeInTheDocument();
  });

  it("sets aria-checked when checked", () => {
    render(<Toggle checked={true} onChange={() => {}} />);
    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "true");
  });

  it("calls onChange with toggled value on click", () => {
    const handleChange = vi.fn();
    render(<Toggle checked={true} onChange={handleChange} />);
    fireEvent.click(screen.getByRole("switch"));
    expect(handleChange).toHaveBeenCalledWith(false);
  });
});
