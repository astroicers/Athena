// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sidebar } from "@/components/layout/Sidebar";
import { IntlWrapper } from "@/test/intl-wrapper";
import { NAV_ITEMS } from "@/lib/constants";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/operations"),
}));

// NavItem renders a Link with a title attribute — stub Link as a plain anchor
vi.mock("next/link", () => ({
  __esModule: true,
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

describe("Sidebar", () => {
  it("renders the logo", () => {
    render(<Sidebar />, { wrapper: IntlWrapper });
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("renders all nav items", () => {
    render(<Sidebar />, { wrapper: IntlWrapper });
    // Each NAV_ITEMS entry produces a link with a title attribute
    expect(screen.getByTitle("Operations")).toBeInTheDocument();
    expect(screen.getByTitle("Mission Planner")).toBeInTheDocument();
    expect(screen.getByTitle("War Room")).toBeInTheDocument();
    expect(screen.getByTitle("AI Decisions")).toBeInTheDocument();
    expect(screen.getByTitle("Tool Registry")).toBeInTheDocument();
    // Total links: nav items + the GitHub star link
    const links = screen.getAllByRole("link");
    expect(links.length).toBe(NAV_ITEMS.length + 1);
  });

  it("highlights the active item based on pathname", async () => {
    const { usePathname } = await import("next/navigation");
    (usePathname as ReturnType<typeof vi.fn>).mockReturnValue("/planner");

    render(<Sidebar />, { wrapper: IntlWrapper });

    const plannerLink = screen.getByTitle("Mission Planner");
    expect(plannerLink.className).toContain("bg-[#3b82f620]");

    // Non-active items should not have the active class
    const operationsLink = screen.getByTitle("Operations");
    expect(operationsLink.className).not.toContain("bg-[#3b82f620]");
  });

  it("renders the GitHub star link", () => {
    render(<Sidebar />, { wrapper: IntlWrapper });
    const ghLink = screen.getByTitle("astroicers/Athena");
    expect(ghLink).toBeInTheDocument();
    expect(ghLink).toHaveAttribute(
      "href",
      "https://github.com/astroicers/Athena",
    );
    expect(ghLink).toHaveAttribute("target", "_blank");
  });
});
