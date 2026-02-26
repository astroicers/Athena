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
    const allTab = screen.getByText("All");
    expect(allTab.className).toContain("bg-athena-accent");

    fireEvent.click(screen.getByText("Active"));
    expect(handleChange).toHaveBeenCalledWith("active");
  });
});
