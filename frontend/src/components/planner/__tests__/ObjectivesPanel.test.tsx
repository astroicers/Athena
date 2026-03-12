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
import { ToastProvider } from "@/contexts/ToastContext";
import { ObjectivesPanel } from "@/components/planner/ObjectivesPanel";

// ---------------------------------------------------------------------------
// Mock api module
// ---------------------------------------------------------------------------
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <IntlWrapper>
      <ToastProvider>{children}</ToastProvider>
    </IntlWrapper>
  );
}

const sampleObjectives = [
  {
    id: "obj-1",
    objective: "Gain domain admin access",
    category: "tactical",
    priority: 1,
    status: "pending",
    evidence: null,
    createdAt: "2026-01-01T00:00:00Z",
    achievedAt: null,
  },
  {
    id: "obj-2",
    objective: "Exfiltrate sensitive data",
    category: "strategic",
    priority: 2,
    status: "achieved",
    evidence: "hash-dump.txt",
    createdAt: "2026-01-02T00:00:00Z",
    achievedAt: "2026-01-03T00:00:00Z",
  },
];

function renderPanel() {
  return render(<ObjectivesPanel operationId="op-1" />, { wrapper: Wrapper });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("ObjectivesPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockGet.mockReset();
    mockPost.mockReset();
    mockPatch.mockReset();
  });

  // -------------------------------------------------------------------------
  // Loading & data rendering
  // -------------------------------------------------------------------------
  it("shows loading skeleton initially", () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = renderPanel();
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("renders objectives list after fetch", async () => {
    mockGet.mockResolvedValue(sampleObjectives);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Gain domain admin access")).toBeInTheDocument();
    });
    expect(screen.getByText("Exfiltrate sensitive data")).toBeInTheDocument();
    expect(screen.getByText("P1")).toBeInTheDocument();
    expect(screen.getByText("P2")).toBeInTheDocument();
  });

  it("renders category badges for each objective", async () => {
    mockGet.mockResolvedValue(sampleObjectives);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("TACTICAL")).toBeInTheDocument();
    });
    expect(screen.getByText("STRATEGIC")).toBeInTheDocument();
  });

  it("renders status badges for each objective", async () => {
    mockGet.mockResolvedValue(sampleObjectives);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("PENDING")).toBeInTheDocument();
    });
    expect(screen.getByText("ACHIEVED")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------
  it("shows empty state when no objectives exist", async () => {
    mockGet.mockResolvedValue([]);
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("No objectives defined for this operation"),
      ).toBeInTheDocument();
    });
  });

  it("shows empty state when fetch fails", async () => {
    mockGet.mockRejectedValue(new Error("network error"));
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("No objectives defined for this operation"),
      ).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Add objective form
  // -------------------------------------------------------------------------
  it("toggles add form when button is clicked", async () => {
    mockGet.mockResolvedValue([]);
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("ADD OBJECTIVE")).toBeInTheDocument();
    });

    // Form not visible initially
    expect(screen.queryByPlaceholderText("e.g. Gain domain admin access")).not.toBeInTheDocument();

    // Click to show form — the header button (not type="submit")
    const headerBtn = () => screen.getAllByRole("button", { name: "ADD OBJECTIVE" })
      .find((btn) => btn.getAttribute("type") !== "submit")!;

    fireEvent.click(headerBtn());
    expect(screen.getByPlaceholderText("e.g. Gain domain admin access")).toBeInTheDocument();

    // Click header button again to hide form
    fireEvent.click(headerBtn());
    expect(screen.queryByPlaceholderText("e.g. Gain domain admin access")).not.toBeInTheDocument();
  });

  it("submits a new objective and prepends it to the list", async () => {
    mockGet.mockResolvedValue([]);
    mockPost.mockResolvedValue({ id: "obj-new", status: "pending" });
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("ADD OBJECTIVE")).toBeInTheDocument();
    });

    // Open form
    fireEvent.click(screen.getByText("ADD OBJECTIVE"));

    // Fill in the objective text
    const input = screen.getByPlaceholderText("e.g. Gain domain admin access");
    fireEvent.change(input, { target: { value: "Pivot to internal network" } });

    // Submit via the form's submit button (type="submit")
    const submitBtn = screen.getAllByRole("button", { name: "ADD OBJECTIVE" })
      .find((btn) => btn.getAttribute("type") === "submit")!;
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Pivot to internal network")).toBeInTheDocument();
    });

    expect(mockPost).toHaveBeenCalledWith(
      "/operations/op-1/objectives",
      { objective: "Pivot to internal network", category: "tactical", priority: 3 },
    );
  });

  it("disables submit button when objective text is empty", async () => {
    mockGet.mockResolvedValue([]);
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("ADD OBJECTIVE")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("ADD OBJECTIVE"));

    // The submit button shares the same text; find by type="submit"
    const submitBtn = screen.getAllByRole("button", { name: "ADD OBJECTIVE" })
      .find((btn) => btn.getAttribute("type") === "submit");
    expect(submitBtn).toBeDisabled();
  });

  it("closes form via cancel button", async () => {
    mockGet.mockResolvedValue([]);
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("ADD OBJECTIVE")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("ADD OBJECTIVE"));
    expect(screen.getByPlaceholderText("e.g. Gain domain admin access")).toBeInTheDocument();

    fireEvent.click(screen.getByText("CANCEL"));
    expect(screen.queryByPlaceholderText("e.g. Gain domain admin access")).not.toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Toggle status
  // -------------------------------------------------------------------------
  it("toggles objective status from pending to achieved on click", async () => {
    mockGet.mockResolvedValue([sampleObjectives[0]]);
    mockPatch.mockResolvedValue({});
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("PENDING")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("PENDING"));

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith(
        "/operations/op-1/objectives/obj-1",
        { status: "achieved" },
      );
    });
  });

  it("toggles objective status from achieved to pending on click", async () => {
    mockGet.mockResolvedValue([sampleObjectives[1]]);
    mockPatch.mockResolvedValue({});
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("ACHIEVED")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("ACHIEVED"));

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith(
        "/operations/op-1/objectives/obj-2",
        { status: "pending" },
      );
    });
  });

  // -------------------------------------------------------------------------
  // API endpoint
  // -------------------------------------------------------------------------
  it("fetches objectives for the correct operation", async () => {
    mockGet.mockResolvedValue([]);
    renderPanel();

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith("/operations/op-1/objectives");
    });
  });
});
