// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { TargetSummaryPanel } from "@/components/planner/TargetSummaryPanel";

// ---------------------------------------------------------------------------
// Mock api module
// ---------------------------------------------------------------------------
const mockGet = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const defaultProps = {
  operationId: "op-1",
  targetId: "target-1",
  hostname: "dc01.corp.local",
  onClose: vi.fn(),
};

const fullSummaryData = {
  target_id: "target-1",
  hostname: "dc01.corp.local",
  summary: "Domain controller running Windows Server 2019. Multiple services exposed.",
  attack_surface: [
    "SMB (445) - signing not required",
    "LDAP (389) - anonymous bind allowed",
    "RDP (3389) - NLA disabled",
  ],
  recommended_techniques: [
    {
      technique_id: "T1003.001",
      name: "LSASS Memory",
      rationale: "Domain controller with admin access enables credential dump",
    },
    {
      technique_id: "T1021.002",
      name: "SMB/Windows Admin Shares",
      rationale: "SMB signing not required allows relay attacks",
    },
  ],
};

function renderPanel(overrides: Partial<typeof defaultProps> = {}) {
  return render(<TargetSummaryPanel {...defaultProps} {...overrides} />, {
    wrapper: IntlWrapper,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("TargetSummaryPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockGet.mockReset();
    defaultProps.onClose.mockReset();
  });

  // -------------------------------------------------------------------------
  // Header
  // -------------------------------------------------------------------------
  it("renders header with hostname", async () => {
    mockGet.mockResolvedValue(fullSummaryData);
    renderPanel();
    expect(screen.getByText(/dc01\.corp\.local/)).toBeInTheDocument();
    expect(screen.getByText(/AI SUMMARY/)).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------
  it("shows loading state while fetching", () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    renderPanel();
    expect(screen.getByText("Analyzing target...")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Full data rendering
  // -------------------------------------------------------------------------
  it("renders summary text after successful fetch", async () => {
    mockGet.mockResolvedValue(fullSummaryData);
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText(/Domain controller running Windows Server 2019/),
      ).toBeInTheDocument();
    });
  });

  it("renders attack surface items", async () => {
    mockGet.mockResolvedValue(fullSummaryData);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Attack Surface")).toBeInTheDocument();
    });
    expect(screen.getByText("SMB (445) - signing not required")).toBeInTheDocument();
    expect(screen.getByText("LDAP (389) - anonymous bind allowed")).toBeInTheDocument();
    expect(screen.getByText("RDP (3389) - NLA disabled")).toBeInTheDocument();
  });

  it("renders recommended techniques with IDs and names", async () => {
    mockGet.mockResolvedValue(fullSummaryData);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Recommended Techniques")).toBeInTheDocument();
    });
    expect(screen.getByText("T1003.001")).toBeInTheDocument();
    expect(screen.getByText("LSASS Memory")).toBeInTheDocument();
    expect(screen.getByText("T1021.002")).toBeInTheDocument();
    expect(screen.getByText("SMB/Windows Admin Shares")).toBeInTheDocument();
  });

  it("renders technique rationale", async () => {
    mockGet.mockResolvedValue(fullSummaryData);
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("Domain controller with admin access enables credential dump"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText("SMB signing not required allows relay attacks"),
    ).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Missing / empty data
  // -------------------------------------------------------------------------
  it("shows no-summary message when summary is empty string", async () => {
    mockGet.mockResolvedValue({ ...fullSummaryData, summary: "" });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("No AI summary available")).toBeInTheDocument();
    });
  });

  it("does not render attack surface section when array is empty", async () => {
    mockGet.mockResolvedValue({ ...fullSummaryData, attack_surface: [] });
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText(/Domain controller running Windows Server 2019/),
      ).toBeInTheDocument();
    });
    expect(screen.queryByText("Attack Surface")).not.toBeInTheDocument();
  });

  it("does not render techniques section when array is empty", async () => {
    mockGet.mockResolvedValue({ ...fullSummaryData, recommended_techniques: [] });
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText(/Domain controller running Windows Server 2019/),
      ).toBeInTheDocument();
    });
    expect(screen.queryByText("Recommended Techniques")).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------
  it("shows error message when fetch fails", async () => {
    mockGet.mockRejectedValue(new Error("network error"));
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("No AI summary available")).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Close button
  // -------------------------------------------------------------------------
  it("calls onClose when close button is clicked", async () => {
    mockGet.mockResolvedValue(fullSummaryData);
    renderPanel();

    const closeButton = screen.getByRole("button", { name: /Close/ });
    fireEvent.click(closeButton);
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  // -------------------------------------------------------------------------
  // API endpoint
  // -------------------------------------------------------------------------
  it("fetches summary for the correct operation and target", () => {
    mockGet.mockResolvedValue(fullSummaryData);
    renderPanel();
    expect(mockGet).toHaveBeenCalledWith(
      "/operations/op-1/targets/target-1/summary",
    );
  });
});
