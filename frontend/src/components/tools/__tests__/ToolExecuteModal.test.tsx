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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ToolExecuteModal } from "@/components/tools/ToolExecuteModal";
import { IntlWrapper } from "@/test/intl-wrapper";
import type { ToolRegistryEntry } from "@/types/tool";

vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

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

describe("ToolExecuteModal", () => {
  it("renders nothing when tool is null", () => {
    const { container } = render(
      <ToolExecuteModal tool={null} onClose={vi.fn()} />,
      { wrapper: IntlWrapper },
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders modal with tool name when tool is provided", () => {
    render(
      <ToolExecuteModal tool={makeTool()} onClose={vi.fn()} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("Nmap Scanner")).toBeInTheDocument();
  });

  it("shows MCP server info when configJson has mcpServer", () => {
    render(
      <ToolExecuteModal
        tool={makeTool({ configJson: { mcpServer: "mcp-nmap" } })}
        onClose={vi.fn()}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("MCP: mcp-nmap")).toBeInTheDocument();
  });

  it("shows MCP server info with mcp_server key (snake_case)", () => {
    render(
      <ToolExecuteModal
        tool={makeTool({ configJson: { mcp_server: "mcp-hydra" } })}
        onClose={vi.fn()}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("MCP: mcp-hydra")).toBeInTheDocument();
  });

  it("does not show MCP line when no server configured", () => {
    render(
      <ToolExecuteModal
        tool={makeTool({ configJson: {} })}
        onClose={vi.fn()}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.queryByText(/^MCP:/)).not.toBeInTheDocument();
  });

  it("renders arguments textarea with default JSON", () => {
    render(
      <ToolExecuteModal tool={makeTool()} onClose={vi.fn()} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("Arguments (JSON)")).toBeInTheDocument();
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveValue("{}");
  });

  it("renders Execute button", () => {
    render(
      <ToolExecuteModal tool={makeTool()} onClose={vi.fn()} />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("Execute")).toBeInTheDocument();
  });

  it("calls onClose when close button (x) is clicked", () => {
    const onClose = vi.fn();
    render(
      <ToolExecuteModal tool={makeTool()} onClose={onClose} />,
      { wrapper: IntlWrapper },
    );
    fireEvent.click(screen.getByText("x"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when clicking the backdrop", () => {
    const onClose = vi.fn();
    const { container } = render(
      <ToolExecuteModal tool={makeTool()} onClose={onClose} />,
      { wrapper: IntlWrapper },
    );
    // The backdrop is the outermost fixed div
    const backdrop = container.querySelector(".fixed.inset-0")!;
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose when clicking inside the modal panel", () => {
    const onClose = vi.fn();
    render(
      <ToolExecuteModal tool={makeTool()} onClose={onClose} />,
      { wrapper: IntlWrapper },
    );
    // Click on the tool name inside the modal content
    fireEvent.click(screen.getByText("Nmap Scanner"));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("shows error for invalid JSON input", async () => {
    render(
      <ToolExecuteModal tool={makeTool()} onClose={vi.fn()} />,
      { wrapper: IntlWrapper },
    );
    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: "not valid json" } });
    fireEvent.click(screen.getByText("Execute"));

    await waitFor(() => {
      expect(
        screen.getByText("Invalid JSON. Please check your input."),
      ).toBeInTheDocument();
    });
  });

  it("calls api.post with correct path and arguments on execute", async () => {
    const { api } = await import("@/lib/api");
    const mockPost = vi.mocked(api.post);
    mockPost.mockResolvedValue({ output: "scan complete" });

    render(
      <ToolExecuteModal
        tool={makeTool({ id: "uuid-42" })}
        onClose={vi.fn()}
      />,
      { wrapper: IntlWrapper },
    );

    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, {
      target: { value: '{"target": "10.0.0.1"}' },
    });
    fireEvent.click(screen.getByText("Execute"));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        "/tools/uuid-42/execute",
        { arguments: { target: "10.0.0.1" } },
        { timeoutMs: 120_000 },
      );
    });
  });

  it("displays result as formatted JSON on success", async () => {
    const { api } = await import("@/lib/api");
    const mockPost = vi.mocked(api.post);
    mockPost.mockResolvedValue({ output: "done" });

    render(
      <ToolExecuteModal tool={makeTool()} onClose={vi.fn()} />,
      { wrapper: IntlWrapper },
    );
    fireEvent.click(screen.getByText("Execute"));

    await waitFor(() => {
      expect(screen.getByText(/"output": "done"/)).toBeInTheDocument();
    });
  });

  it("displays error message when api call fails", async () => {
    const { api } = await import("@/lib/api");
    const mockPost = vi.mocked(api.post);
    mockPost.mockRejectedValue({ detail: "Server unreachable" });

    render(
      <ToolExecuteModal tool={makeTool()} onClose={vi.fn()} />,
      { wrapper: IntlWrapper },
    );
    fireEvent.click(screen.getByText("Execute"));

    await waitFor(() => {
      expect(screen.getByText("Server unreachable")).toBeInTheDocument();
    });
  });
});
