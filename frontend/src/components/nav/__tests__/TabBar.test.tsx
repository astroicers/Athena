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
import { TabBar } from "@/components/nav/TabBar";

describe("TabBar", () => {
  it("highlights active tab and calls onChange", () => {
    const handleChange = vi.fn();
    render(
      <TabBar
        tabs={[
          { id: "all", label: "All" },
          { id: "active", label: "Active" },
        ]}
        activeTab="all"
        onChange={handleChange}
      />,
    );
    // Active tab should have the accent color class (underline-style)
    const allTab = screen.getByText("All");
    expect(allTab.className).toContain("text-athena-accent");

    // Inactive tab should not have accent color
    const activeTab = screen.getByText("Active");
    expect(activeTab.className).toContain("text-athena-text-secondary");

    fireEvent.click(screen.getByText("Active"));
    expect(handleChange).toHaveBeenCalledWith("active");
  });
});
