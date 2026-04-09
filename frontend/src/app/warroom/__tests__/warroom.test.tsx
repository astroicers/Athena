// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";

/* ── Mock external dependencies ─────────────────────────────────── */

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/warroom",
}));

vi.mock("@/contexts/OperationContext", () => ({
  useOperationId: () => "op-0001",
  useOperationContext: () => ({
    operationId: "op-0001",
    setOperationId: vi.fn(),
  }),
}));

vi.mock("@/contexts/ToastContext", () => ({
  useToast: () => ({
    addToast: vi.fn(),
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

vi.mock("@/hooks/useWebSocket", () => ({
  useWebSocket: () => ({
    isConnected: false,
    events: [],
    send: vi.fn(),
    subscribe: vi.fn(() => vi.fn()),
  }),
}));

vi.mock("@/hooks/useC5ISRData", () => ({
  useC5ISRData: () => ({
    domains: [],
    constraints: null,
    override: vi.fn(),
    fetchReport: vi.fn(),
  }),
}));

import { api } from "@/lib/api";
import WarRoomPage from "../page";

const mockApi = vi.mocked(api);

/* ── Helpers ─────────────────────────────────────────────────────── */

function setupApiMocks() {
  mockApi.get.mockImplementation((path: string) => {
    if (path.includes("/ooda/dashboard")) {
      return Promise.resolve({
        currentPhase: "observe",
        iterationCount: 2,
        latestIteration: {
          id: "iter-002",
          iterationNumber: 2,
          phase: "observe",
          observeSummary: "Scanning target network",
          startedAt: "2026-01-15T10:00:00Z",
          completedAt: null,
        },
        recentIterations: [],
      });
    }
    if (path.includes("/ooda/timeline")) {
      return Promise.resolve([]);
    }
    if (path.includes("/targets")) {
      return Promise.resolve([]);
    }
    if (path.includes("/ooda/directive/latest")) {
      return Promise.resolve(null);
    }
    if (path.includes("/c5isr")) {
      return Promise.resolve([]);
    }
    if (path.includes("/constraints")) {
      return Promise.resolve(null);
    }
    if (path.includes("/missions/steps")) {
      return Promise.resolve([]);
    }
    return Promise.resolve(null);
  });
}

/* ── Tests ───────────────────────────────────────────────────────── */

describe("War Room Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders page with tab bar", async () => {
    setupApiMocks();
    render(<WarRoomPage />, { wrapper: IntlWrapper });

    // Page should render with tab buttons visible
    await waitFor(() => {
      expect(screen.getByText("TIMELINE")).toBeInTheDocument();
    });
    expect(screen.getByText("TARGETS")).toBeInTheDocument();
    expect(screen.getByText("MISSION")).toBeInTheDocument();
  });

  it("shows loading state initially", () => {
    mockApi.get.mockReturnValue(new Promise(() => {}));
    render(<WarRoomPage />, { wrapper: IntlWrapper });

    // Page should render a main element even during loading
    expect(document.body.querySelector("main")).toBeTruthy();
  });

  it("fetches OODA dashboard on mount", async () => {
    setupApiMocks();
    render(<WarRoomPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(mockApi.get).toHaveBeenCalledWith(
        expect.stringContaining("/ooda/dashboard"),
      );
    });
  });

  it("fetches targets on mount", async () => {
    setupApiMocks();
    render(<WarRoomPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(mockApi.get).toHaveBeenCalledWith(
        expect.stringContaining("/targets"),
      );
    });
  });

  it("handles API errors gracefully", async () => {
    mockApi.get.mockRejectedValue(new Error("Network error"));
    render(<WarRoomPage />, { wrapper: IntlWrapper });

    // Page should still render after errors — tab bar visible
    await waitFor(() => {
      expect(screen.getByText("TIMELINE")).toBeInTheDocument();
    });
  });
});
