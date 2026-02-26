import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "@/components/atoms/Button";

describe("Button", () => {
  it("renders children text", () => {
    render(<Button>Execute</Button>);
    expect(screen.getByRole("button", { name: "Execute" })).toBeInTheDocument();
  });

  it("applies variant class", () => {
    render(<Button variant="danger">Delete</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-athena-error");
  });

  it("calls onClick handler", () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(handleClick).toHaveBeenCalledOnce();
  });
});
