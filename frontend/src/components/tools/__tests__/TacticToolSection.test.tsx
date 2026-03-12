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
import { render, screen, fireEvent } from "@testing-library/react";
import { TacticToolSection } from "@/components/tools/TacticToolSection";
import { IntlWrapper } from "@/test/intl-wrapper";
import type { ToolRegistryEntry } from "@/types/tool";

function makeTool(overrides: Partial<ToolRegistryEntry> = {}): ToolRegistryEntry {
  return {
    id: "uuid-1",
    toolId: "nmap-scanner",
    name: "Nmap Scanner",
    description: "Network discovery and port scanning",
    kind: "tool",
    category: "reconnaissance",
    version: "1.0.0",
    enabled: true,
    source: "seed",
    configJson: {},
    mitreTechniques: ["T1046"],
    riskLevel: "low",
    outputTraits: ["ports"],
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const defaultProps = {
  tacticSlug: "reconnaissance",
  tacticLabel: "RECONNAISSANCE",
  tacticId: "TA0043",
  tools: [makeTool()],
  onToggleEnabled: vi.fn().mockResolvedValue(undefined),
  onDelete: vi.fn().mockResolvedValue(undefined),
  containerStatuses: {} as Record<string, boolean>,
};

describe("TacticToolSection", () => {
  it("renders the tactic label and ID", () => {
    render(
      <TacticToolSection {...defaultProps} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("RECONNAISSANCE")).toBeInTheDocument();
    expect(screen.getByText("TA0043")).toBeInTheDocument();
  });

  it("displays the tool count", () => {
    render(
      <TacticToolSection {...defaultProps} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("1 tools")).toBeInTheDocument();
  });

  it("displays count for multiple tools", () => {
    const tools = [
      makeTool({ id: "1", toolId: "tool-a" }),
      makeTool({ id: "2", toolId: "tool-b" }),
      makeTool({ id: "3", toolId: "tool-c" }),
    ];
    render(
      <TacticToolSection {...defaultProps} tools={tools} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("3 tools")).toBeInTheDocument();
  });

  it("is collapsed by default (does not show tool table)", () => {
    render(
      <TacticToolSection {...defaultProps} />,
      { wrapper: IntlWrapper },
    );
    // Tool name from the inner ToolRegistryTable should not be visible
    expect(screen.queryByText("Nmap Scanner")).not.toBeInTheDocument();
  });

  it("expands to show tools when header is clicked", () => {
    render(
      <TacticToolSection {...defaultProps} />,
      { wrapper: IntlWrapper },
    );
    fireEvent.click(screen.getByText("RECONNAISSANCE"));
    expect(screen.getByText("Nmap Scanner")).toBeInTheDocument();
  });

  it("collapses when header is clicked a second time", () => {
    render(
      <TacticToolSection {...defaultProps} />,
      { wrapper: IntlWrapper },
    );
    const header = screen.getByText("RECONNAISSANCE");
    fireEvent.click(header);
    expect(screen.getByText("Nmap Scanner")).toBeInTheDocument();

    fireEvent.click(header);
    expect(screen.queryByText("Nmap Scanner")).not.toBeInTheDocument();
  });

  it("renders open by default when defaultOpen is true", () => {
    render(
      <TacticToolSection {...defaultProps} defaultOpen={true} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("Nmap Scanner")).toBeInTheDocument();
  });

  it("auto-expands when highlightToolId matches a tool in the section", () => {
    render(
      <TacticToolSection
        {...defaultProps}
        highlightToolId="nmap-scanner"
      />,
      { wrapper: IntlWrapper },
    );
    // Should be auto-expanded because highlightToolId matches tool.toolId
    expect(screen.getByText("Nmap Scanner")).toBeInTheDocument();
  });

  it("stays collapsed when highlightToolId does not match any tool", () => {
    render(
      <TacticToolSection
        {...defaultProps}
        highlightToolId="non-existent-tool"
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.queryByText("Nmap Scanner")).not.toBeInTheDocument();
  });

  it("sets the section id attribute based on tacticSlug", () => {
    const { container } = render(
      <TacticToolSection {...defaultProps} />,
      { wrapper: IntlWrapper },
    );
    const section = container.querySelector("#tactic-reconnaissance");
    expect(section).toBeInTheDocument();
  });

  it("shows empty state when expanded with no tools", () => {
    render(
      <TacticToolSection
        {...defaultProps}
        tools={[]}
        defaultOpen={true}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("No tools registered")).toBeInTheDocument();
  });
});
