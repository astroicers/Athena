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

/* ── Mock external dependencies ─────────────────────────────────── */

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/operations",
}));

const mockAddToast = vi.fn();
vi.mock("@/contexts/ToastContext", () => ({
  useToast: () => ({ toasts: [], addToast: mockAddToast, removeToast: vi.fn() }),
}));

const mockSetOperationId = vi.fn();
vi.mock("@/contexts/OperationContext", () => ({
  useOperationContext: () => ({
    operationId: "op-0001",
    setOperationId: mockSetOperationId,
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

import { api } from "@/lib/api";
import OperationsPage from "../page";

const mockApi = vi.mocked(api);

/* ── Helpers ─────────────────────────────────────────────────────── */

function makeOperation(overrides: Record<string, unknown> = {}) {
  return {
    id: "op-001",
    code: "op-0001",
    name: "External Pentest Q1",
    codename: "IRON TEMPEST",
    strategicIntent: "Assess external attack surface",
    status: "active",
    currentOodaPhase: "observe",
    oodaIterationCount: 3,
    threatLevel: 2,
    successRate: 0.75,
    techniquesExecuted: 5,
    techniquesTotal: 12,
    activeAgents: 2,
    automationMode: "manual",
    riskThreshold: "medium",
    missionProfile: "SR",
    operatorId: "user-1",
    createdAt: "2026-01-15T10:00:00Z",
    updatedAt: "2026-01-15T12:00:00Z",
    ...overrides,
  };
}

/* ── Tests ───────────────────────────────────────────────────────── */

describe("Operations Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders operation cards from API data", async () => {
    const ops = [
      makeOperation({ id: "op-001", codename: "IRON TEMPEST", status: "active" }),
      makeOperation({ id: "op-002", codename: "SHADOW FALCON", status: "planning", missionProfile: "CO" }),
    ];
    mockApi.get.mockResolvedValueOnce(ops);

    render(<OperationsPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(screen.getByText("IRON TEMPEST")).toBeInTheDocument();
    });

    expect(screen.getByText("SHADOW FALCON")).toBeInTheDocument();
    expect(screen.getAllByText("active").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("planning").length).toBeGreaterThanOrEqual(1);
    expect(mockApi.get).toHaveBeenCalledWith("/operations");
  });

  it("shows empty state when no operations", async () => {
    mockApi.get.mockResolvedValueOnce([]);

    render(<OperationsPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(
        screen.getByText("No operations found. Create one to get started."),
      ).toBeInTheDocument();
    });
  });

  it("displays mission profile badges", async () => {
    const ops = [
      makeOperation({ id: "op-001", missionProfile: "SR" }),
      makeOperation({ id: "op-002", missionProfile: "CO", codename: "SHADOW OPS" }),
    ];
    mockApi.get.mockResolvedValueOnce(ops);

    render(<OperationsPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(screen.getByText("SR")).toBeInTheDocument();
    });
    expect(screen.getByText("CO")).toBeInTheDocument();
  });

  it("displays OODA phase for each operation", async () => {
    const ops = [
      makeOperation({ id: "op-001", currentOodaPhase: "orient" }),
    ];
    mockApi.get.mockResolvedValueOnce(ops);

    render(<OperationsPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(screen.getByText("OODA: orient")).toBeInTheDocument();
    });
  });

  it("shows toast on API failure", async () => {
    mockApi.get.mockRejectedValueOnce(new Error("Network error"));

    render(<OperationsPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith(
        "Failed to load operations",
        "error",
      );
    });
  });
});
