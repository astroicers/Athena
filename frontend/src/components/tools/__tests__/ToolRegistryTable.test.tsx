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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ToolRegistryTable } from "@/components/tools/ToolRegistryTable";
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
    configJson: { mcpServer: "mcp-nmap" },
    mitreTechniques: ["T1046"],
    riskLevel: "low",
    outputTraits: ["ports"],
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const defaultProps = {
  onToggleEnabled: vi.fn().mockResolvedValue(undefined),
  onDelete: vi.fn().mockResolvedValue(undefined),
  containerStatuses: {} as Record<string, boolean>,
};

describe("ToolRegistryTable", () => {
  it("renders the empty state when tools array is empty", () => {
    render(
      <ToolRegistryTable {...defaultProps} tools={[]} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("No tools registered")).toBeInTheDocument();
  });

  it("renders table headers", () => {
    render(
      <ToolRegistryTable {...defaultProps} tools={[makeTool()]} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Category")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Risk")).toBeInTheDocument();
    expect(screen.getByText("MITRE")).toBeInTheDocument();
    expect(screen.getByText("Container")).toBeInTheDocument();
    expect(screen.getByText("Actions")).toBeInTheDocument();
  });

  it("renders tool name and description", () => {
    render(
      <ToolRegistryTable {...defaultProps} tools={[makeTool()]} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("Nmap Scanner")).toBeInTheDocument();
    expect(screen.getByText("Network discovery and port scanning")).toBeInTheDocument();
  });

  it("renders multiple tools as table rows", () => {
    const tools = [
      makeTool({ id: "1", toolId: "tool-a", name: "Tool Alpha" }),
      makeTool({ id: "2", toolId: "tool-b", name: "Tool Bravo" }),
      makeTool({ id: "3", toolId: "tool-c", name: "Tool Charlie" }),
    ];
    render(
      <ToolRegistryTable {...defaultProps} tools={tools} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("Tool Alpha")).toBeInTheDocument();
    expect(screen.getByText("Tool Bravo")).toBeInTheDocument();
    expect(screen.getByText("Tool Charlie")).toBeInTheDocument();
  });

  it("displays risk badge with correct text", () => {
    render(
      <ToolRegistryTable
        {...defaultProps}
        tools={[makeTool({ riskLevel: "high" })]}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("HIGH")).toBeInTheDocument();
  });

  it("displays MITRE technique IDs", () => {
    render(
      <ToolRegistryTable
        {...defaultProps}
        tools={[makeTool({ mitreTechniques: ["T1046", "T1595"] })]}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("T1046")).toBeInTheDocument();
    expect(screen.getByText("T1595")).toBeInTheDocument();
  });

  it("shows container ONLINE status when server is running", () => {
    render(
      <ToolRegistryTable
        {...defaultProps}
        containerStatuses={{ "mcp-nmap": true }}
        tools={[makeTool({ configJson: { mcpServer: "mcp-nmap" } })]}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("ONLINE")).toBeInTheDocument();
  });

  it("shows container OFFLINE status when server is down", () => {
    render(
      <ToolRegistryTable
        {...defaultProps}
        containerStatuses={{ "mcp-nmap": false }}
        tools={[makeTool({ configJson: { mcpServer: "mcp-nmap" } })]}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("OFFLINE")).toBeInTheDocument();
  });

  it("shows N/A when tool has no MCP server", () => {
    render(
      <ToolRegistryTable
        {...defaultProps}
        tools={[makeTool({ configJson: {} })]}
      />,
      { wrapper: IntlWrapper },
    );
    // New design uses "--" for N/A container status
    const dashes = screen.getAllByText("--");
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("shows Execute button only for enabled tools", () => {
    const tools = [
      makeTool({ id: "1", toolId: "enabled-tool", name: "Enabled", enabled: true }),
      makeTool({ id: "2", toolId: "disabled-tool", name: "Disabled", enabled: false }),
    ];
    render(
      <ToolRegistryTable {...defaultProps} tools={tools} />,
      { wrapper: IntlWrapper },
    );
    const executeButtons = screen.getAllByText("Execute");
    expect(executeButtons).toHaveLength(1);
  });

  it("shows delete button only for user-source tools", () => {
    const tools = [
      makeTool({ id: "1", toolId: "seed-tool", name: "Seed Tool", source: "seed" }),
      makeTool({ id: "2", toolId: "user-tool", name: "User Tool", source: "user" }),
    ];
    render(
      <ToolRegistryTable {...defaultProps} tools={tools} />,
      { wrapper: IntlWrapper },
    );
    const delButtons = screen.getAllByText("DEL");
    expect(delButtons).toHaveLength(1);
  });

  it("calls onDelete when delete button is clicked", async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined);
    render(
      <ToolRegistryTable
        {...defaultProps}
        onDelete={onDelete}
        tools={[makeTool({ source: "user", toolId: "user-tool-1" })]}
      />,
      { wrapper: IntlWrapper },
    );
    fireEvent.click(screen.getByText("DEL"));
    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith("user-tool-1");
    });
  });

  it("calls onToggleEnabled when toggle is clicked", () => {
    const onToggleEnabled = vi.fn().mockResolvedValue(undefined);
    render(
      <ToolRegistryTable
        {...defaultProps}
        onToggleEnabled={onToggleEnabled}
        tools={[makeTool({ enabled: true, toolId: "my-tool" })]}
      />,
      { wrapper: IntlWrapper },
    );
    const toggle = screen.getByRole("switch");
    fireEvent.click(toggle);
    expect(onToggleEnabled).toHaveBeenCalledWith("my-tool", false);
  });

  it("opens execute modal when Execute button is clicked", () => {
    render(
      <ToolRegistryTable
        {...defaultProps}
        tools={[makeTool({ name: "Nmap Scanner", enabled: true })]}
      />,
      { wrapper: IntlWrapper },
    );
    fireEvent.click(screen.getByText("Execute"));
    // Modal should now be open - it shows the tool name in the header
    // and an Arguments label
    expect(screen.getByText("Arguments (JSON)")).toBeInTheDocument();
  });
});
