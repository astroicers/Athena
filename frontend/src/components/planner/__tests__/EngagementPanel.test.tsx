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
import { EngagementPanel } from "@/components/planner/EngagementPanel";

// ---------------------------------------------------------------------------
// Mock api module
// ---------------------------------------------------------------------------
const mockGet = vi.fn();
const mockPatch = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const draftEngagement = {
  id: "eng-1",
  operationId: "op-1",
  clientName: "Acme Corp",
  contactEmail: "security@acme.com",
  scopeType: "internal",
  inScope: ["10.0.0.0/24", "192.168.1.0/24"],
  outOfScope: ["10.0.0.1 (production DB)"],
  startTime: "2026-03-01T00:00:00Z",
  endTime: "2026-03-15T00:00:00Z",
  emergencyContact: "+1-555-0911",
  status: "draft",
};

const activeEngagement = {
  ...draftEngagement,
  status: "active",
};

const suspendedEngagement = {
  ...draftEngagement,
  status: "suspended",
};

function renderPanel() {
  return render(<EngagementPanel operationId="op-1" />, {
    wrapper: IntlWrapper,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("EngagementPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockGet.mockReset();
    mockPatch.mockReset();
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------
  it("shows loading skeleton initially", () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = renderPanel();
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // No engagement state
  // -------------------------------------------------------------------------
  it("shows empty state when no engagement exists", async () => {
    mockGet.mockRejectedValue(new Error("not found"));
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("No ROE defined for this operation"),
      ).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Rendering client info
  // -------------------------------------------------------------------------
  it("renders client name and contact email", async () => {
    mockGet.mockResolvedValue(draftEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    });
    expect(screen.getByText("security@acme.com")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Scope rendering
  // -------------------------------------------------------------------------
  it("renders in-scope items", async () => {
    mockGet.mockResolvedValue(draftEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("10.0.0.0/24")).toBeInTheDocument();
    });
    expect(screen.getByText("192.168.1.0/24")).toBeInTheDocument();
  });

  it("renders out-of-scope items", async () => {
    mockGet.mockResolvedValue(draftEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("10.0.0.1 (production DB)")).toBeInTheDocument();
    });
  });

  it("shows placeholder when in-scope is empty", async () => {
    mockGet.mockResolvedValue({ ...draftEngagement, inScope: [] });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    });
    // The component renders "--" for empty scope lists
    const placeholders = screen.getAllByText("--");
    expect(placeholders.length).toBeGreaterThanOrEqual(1);
  });

  it("shows placeholder when out-of-scope is empty", async () => {
    mockGet.mockResolvedValue({ ...draftEngagement, outOfScope: [] });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    });
    const placeholders = screen.getAllByText("--");
    expect(placeholders.length).toBeGreaterThanOrEqual(1);
  });

  // -------------------------------------------------------------------------
  // Emergency contact
  // -------------------------------------------------------------------------
  it("renders emergency contact when present", async () => {
    mockGet.mockResolvedValue(draftEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("+1-555-0911")).toBeInTheDocument();
    });
  });

  it("does not render emergency contact when null", async () => {
    mockGet.mockResolvedValue({ ...draftEngagement, emergencyContact: null });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    });
    expect(screen.queryByText("Emergency Contact")).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Status badge
  // -------------------------------------------------------------------------
  it("renders DRAFT status badge for draft engagement", async () => {
    mockGet.mockResolvedValue(draftEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("DRAFT")).toBeInTheDocument();
    });
  });

  it("renders ACTIVE status badge for active engagement", async () => {
    mockGet.mockResolvedValue(activeEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    });
  });

  it("renders SUSPENDED status badge for suspended engagement", async () => {
    mockGet.mockResolvedValue(suspendedEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("SUSPENDED")).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Activate button (draft only)
  // -------------------------------------------------------------------------
  it("shows Activate button for draft engagement", async () => {
    mockGet.mockResolvedValue(draftEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Activate")).toBeInTheDocument();
    });
  });

  it("does not show Activate button for active engagement", async () => {
    mockGet.mockResolvedValue(activeEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    });
    expect(screen.queryByText("Activate")).not.toBeInTheDocument();
  });

  it("calls activate API when Activate button is clicked", async () => {
    mockGet.mockResolvedValue(draftEngagement);
    mockPatch.mockResolvedValue(activeEngagement);
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("Activate")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Activate"));

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith(
        "/operations/op-1/engagement/activate",
      );
    });
  });

  // -------------------------------------------------------------------------
  // Suspend button (active only)
  // -------------------------------------------------------------------------
  it("shows Suspend button for active engagement", async () => {
    mockGet.mockResolvedValue(activeEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Suspend")).toBeInTheDocument();
    });
  });

  it("does not show Suspend button for draft engagement", async () => {
    mockGet.mockResolvedValue(draftEngagement);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Activate")).toBeInTheDocument();
    });
    expect(screen.queryByText("Suspend")).not.toBeInTheDocument();
  });

  it("calls suspend API when Suspend button is clicked", async () => {
    mockGet.mockResolvedValue(activeEngagement);
    mockPatch.mockResolvedValue(suspendedEngagement);
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("Suspend")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Suspend"));

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith(
        "/operations/op-1/engagement/suspend",
      );
    });
  });

  // -------------------------------------------------------------------------
  // API endpoint
  // -------------------------------------------------------------------------
  it("fetches engagement for the correct operation", () => {
    mockGet.mockResolvedValue(draftEngagement);
    renderPanel();
    expect(mockGet).toHaveBeenCalledWith("/operations/op-1/engagement");
  });
});
