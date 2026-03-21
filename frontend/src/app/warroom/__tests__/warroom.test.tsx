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

function makeDashboard(overrides: Record<string, unknown> = {}) {
  return {
    currentPhase: "observe",
    iterationCount: 2,
    latestIteration: {
      id: "iter-002",
      iterationNumber: 2,
      phase: "observe",
      observeSummary: "Scanning target network",
      orientSummary: null,
      decideSummary: null,
      actSummary: null,
      startedAt: "2026-01-15T10:00:00Z",
      completedAt: null,
    },
    recentIterations: [
      {
        id: "iter-001",
        iterationNumber: 1,
        phase: "act",
        observeSummary: "Initial recon complete",
        orientSummary: "3 services identified",
        decideSummary: "Target SSH service",
        actSummary: "Executed T1021.004",
        startedAt: "2026-01-15T08:00:00Z",
        completedAt: "2026-01-15T09:30:00Z",
      },
      {
        id: "iter-002",
        iterationNumber: 2,
        phase: "observe",
        observeSummary: "Scanning target network",
        orientSummary: null,
        decideSummary: null,
        actSummary: null,
        startedAt: "2026-01-15T10:00:00Z",
        completedAt: null,
      },
    ],
    ...overrides,
  };
}

function makeTimeline() {
  return [
    {
      iterationNumber: 1,
      phase: "observe",
      summary: "Started network scan",
      timestamp: "2026-01-15T08:00:00Z",
    },
    {
      iterationNumber: 1,
      phase: "orient",
      summary: "Analyzed scan results",
      timestamp: "2026-01-15T08:30:00Z",
    },
  ];
}

/**
 * Set up api.get to always return dashboard + timeline for any call.
 * The war room page uses setInterval which causes extra calls;
 * mockResolvedValue (not Once) prevents unresolved promises.
 */
function setupApiMocks(
  dashboard: ReturnType<typeof makeDashboard> | null = null,
  timeline: ReturnType<typeof makeTimeline> = [],
) {
  mockApi.get.mockImplementation((path: string) => {
    if (path.includes("/ooda/dashboard")) {
      return dashboard
        ? Promise.resolve(dashboard)
        : Promise.reject(new Error("Not found"));
    }
    if (path.includes("/ooda/timeline")) {
      return Promise.resolve(timeline);
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

  it("renders campaign timeline with OODA dashboard data", async () => {
    const dashboard = makeDashboard();
    const timeline = makeTimeline();
    setupApiMocks(dashboard, timeline);

    render(<WarRoomPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(screen.getByText("CAMPAIGN TIMELINE")).toBeInTheDocument();
    });

    // OODA iteration count appears in both the header and timeline block
    const oodaLabels = screen.getAllByText("OODA #2");
    expect(oodaLabels.length).toBeGreaterThanOrEqual(1);
    expect(mockApi.get).toHaveBeenCalledWith(
      "/operations/op-0001/ooda/dashboard",
    );
    expect(mockApi.get).toHaveBeenCalledWith(
      "/operations/op-0001/ooda/timeline",
    );
  });

  it("shows loading state initially", () => {
    // Never resolve the API calls to keep component in loading state
    mockApi.get.mockReturnValue(new Promise(() => {}));

    render(<WarRoomPage />, { wrapper: IntlWrapper });

    expect(screen.getByText(/War Room/)).toBeInTheDocument();
  });

  it("renders MANUAL mode button by default", async () => {
    setupApiMocks(makeDashboard());

    render(<WarRoomPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      expect(screen.getByText("MANUAL")).toBeInTheDocument();
    });
  });

  it("renders mission objective section", async () => {
    setupApiMocks(makeDashboard());

    render(<WarRoomPage />, { wrapper: IntlWrapper });

    await waitFor(() => {
      // MissionObjective renders as "OBJECTIVE: Domain Admin on corp.local"
      expect(
        screen.getByText(/Domain Admin on corp\.local/),
      ).toBeInTheDocument();
    });
  });

  it("handles API errors gracefully", async () => {
    mockApi.get.mockRejectedValue(new Error("Network error"));

    render(<WarRoomPage />, { wrapper: IntlWrapper });

    // After error, loading should finish and the page should render
    // without dashboard data but still showing the campaign timeline header
    await waitFor(() => {
      expect(screen.getByText("CAMPAIGN TIMELINE")).toBeInTheDocument();
    });
  });
});
