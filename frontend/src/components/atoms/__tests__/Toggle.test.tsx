// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

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
