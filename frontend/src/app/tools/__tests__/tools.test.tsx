// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import type { ToolRegistryEntry } from "@/types/tool";

/* ── Mock external dependencies ─────────────────────────────────── */

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/tools",
}));

const mockUseTools = vi.fn();
vi.mock("@/hooks/useTools", () => ({
  useTools: (...args: unknown[]) => mockUseTools(...args),
}));

vi.mock("@/hooks/useMCPServers", () => ({
  useMCPServers: () => ({
    servers: [],
    loading: false,
    refetch: vi.fn(),
  }),
}));

const mockAddToast = vi.fn();
vi.mock("@/contexts/ToastContext", () => ({
  useToast: () => ({ toasts: [], addToast: mockAddToast, removeToast: vi.fn() }),
}));

vi.mock("@/contexts/OperationContext", () => ({
  useOperationId: () => "op-0001",
  useOperationContext: () => ({
    operationId: "op-0001",
    setOperationId: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

/* ── Helpers ─────────────────────────────────────────────────────── */

function makeTool(overrides: Partial<ToolRegistryEntry> = {}): ToolRegistryEntry {
  return {
    id: "t-001",
    toolId: "nmap-scanner",
    name: "Nmap Scanner",
    description: "Network mapper and port scanner",
    kind: "tool",
    category: "reconnaissance",
    version: "1.0.0",
    enabled: true,
    source: "seed",
    configJson: {},
    mitreTechniques: ["T1046"],
    riskLevel: "low",
    outputTraits: ["open_ports"],
    createdAt: "2026-01-10T00:00:00Z",
    updatedAt: "2026-01-10T00:00:00Z",
    ...overrides,
  };
}

/* ── Import page after mocks are set up ──────────────────────────── */

import ToolsPage from "../page";

/* ── Tests ───────────────────────────────────────────────────────── */

describe("Tools Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders tool registry table with mocked data", async () => {
    const tools = [
      makeTool({ id: "t-001", toolId: "nmap-scanner", name: "Nmap Scanner" }),
      makeTool({
        id: "t-002",
        toolId: "web-scanner",
        name: "Web Scanner",
        category: "vulnerability_scanning",
        riskLevel: "medium",
        mitreTechniques: ["T1595"],
      }),
    ];

    mockUseTools.mockReturnValue({
      tools,
      loading: false,
      fetchTools: vi.fn(),
      toggleEnabled: vi.fn(),
      deleteTool: vi.fn(),
      createTool: vi.fn(),
    });

    render(<ToolsPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(screen.getByText("Nmap Scanner")).toBeInTheDocument();
    });

    expect(screen.getByText("Web Scanner")).toBeInTheDocument();
    expect(screen.getByText("T1046")).toBeInTheDocument();
    expect(screen.getByText("T1595")).toBeInTheDocument();
  });

  it("shows empty state when no tools registered", async () => {
    mockUseTools.mockReturnValue({
      tools: [],
      loading: false,
      fetchTools: vi.fn(),
      toggleEnabled: vi.fn(),
      deleteTool: vi.fn(),
      createTool: vi.fn(),
    });

    render(<ToolsPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(screen.getByText("No tools registered")).toBeInTheDocument();
    });
  });

  it("renders tab buttons for registry and playbooks", async () => {
    mockUseTools.mockReturnValue({
      tools: [makeTool()],
      loading: false,
      fetchTools: vi.fn(),
      toggleEnabled: vi.fn(),
      deleteTool: vi.fn(),
      createTool: vi.fn(),
    });

    render(<ToolsPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(screen.getByText("REGISTRY")).toBeInTheDocument();
    });
    expect(screen.getByText("PLAYBOOKS")).toBeInTheDocument();
  });

  it("shows loading state while fetching tools", () => {
    mockUseTools.mockReturnValue({
      tools: [],
      loading: true,
      fetchTools: vi.fn(),
      toggleEnabled: vi.fn(),
      deleteTool: vi.fn(),
      createTool: vi.fn(),
    });

    render(<ToolsPage />, { wrapper: IntlWrapper });

    expect(screen.getByText("INITIALIZING SYSTEMS")).toBeInTheDocument();
  });

  it("displays enabled/disabled status for tools", async () => {
    const tools = [
      makeTool({ id: "t-001", name: "Enabled Tool", enabled: true }),
      makeTool({ id: "t-002", toolId: "disabled-tool", name: "Disabled Tool", enabled: false }),
    ];

    mockUseTools.mockReturnValue({
      tools,
      loading: false,
      fetchTools: vi.fn(),
      toggleEnabled: vi.fn(),
      deleteTool: vi.fn(),
      createTool: vi.fn(),
    });

    render(<ToolsPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(screen.getByText("Enabled Tool")).toBeInTheDocument();
    });

    const onLabels = screen.getAllByText("ON");
    const offLabels = screen.getAllByText("OFF");
    expect(onLabels.length).toBeGreaterThanOrEqual(1);
    expect(offLabels.length).toBeGreaterThanOrEqual(1);
  });
});
