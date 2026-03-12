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
import { NotificationCenter } from "@/components/layout/NotificationCenter";
import { IntlWrapper } from "@/test/intl-wrapper";

interface OpsecAlert {
  id: string;
  message: string;
  severity: "warning" | "error";
  timestamp: string;
}

interface ConstraintAlert {
  active: boolean;
  messages: string[];
  domains: string[];
}

const emptyConstraint: ConstraintAlert = {
  active: false,
  messages: [],
  domains: [],
};

const sampleOpsecAlerts: OpsecAlert[] = [
  {
    id: "1",
    message: "High noise detected on port scan",
    severity: "warning",
    timestamp: "2026-03-12T10:30:00Z",
  },
  {
    id: "2",
    message: "Credential spray triggered IDS alert",
    severity: "error",
    timestamp: "2026-03-12T10:31:00Z",
  },
];

const sampleConstraint: ConstraintAlert = {
  active: true,
  messages: ["Rate limit exceeded for target subnet"],
  domains: ["cyber"],
};

describe("NotificationCenter", () => {
  const onClose = vi.fn();

  beforeEach(() => {
    onClose.mockClear();
  });

  it("returns null when closed", () => {
    const { container } = render(
      <NotificationCenter
        isOpen={false}
        onClose={onClose}
        opsecAlerts={[]}
        constraintAlert={emptyConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders when open", () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={onClose}
        opsecAlerts={[]}
        constraintAlert={emptyConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Notifications")).toBeInTheDocument();
  });

  it("shows empty state when no alerts", () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={onClose}
        opsecAlerts={[]}
        constraintAlert={emptyConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("No notifications")).toBeInTheDocument();
  });

  it("shows constraint alerts when active", () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={onClose}
        opsecAlerts={[]}
        constraintAlert={sampleConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("Pinned Constraints")).toBeInTheDocument();
    expect(
      screen.getByText("Rate limit exceeded for target subnet"),
    ).toBeInTheDocument();
  });

  it("shows opsec alerts", () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={onClose}
        opsecAlerts={sampleOpsecAlerts}
        constraintAlert={emptyConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("OPSEC Warnings")).toBeInTheDocument();
    expect(
      screen.getByText("High noise detected on port scan"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Credential spray triggered IDS alert"),
    ).toBeInTheDocument();
  });

  it("shows severity badges for opsec alerts", () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={onClose}
        opsecAlerts={sampleOpsecAlerts}
        constraintAlert={emptyConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    // "warning" maps to "HIGH", "error" maps to "CRITICAL"
    expect(screen.getByText("HIGH")).toBeInTheDocument();
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
  });

  it("displays the correct total count badge", () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={onClose}
        opsecAlerts={sampleOpsecAlerts}
        constraintAlert={sampleConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    // 2 opsec alerts + 1 constraint group = 3
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("does not show count badge when there are no alerts", () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={onClose}
        opsecAlerts={[]}
        constraintAlert={emptyConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    // totalCount is 0, so the badge span should not render
    const badge = screen.queryByText("0");
    expect(badge).not.toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={onClose}
        opsecAlerts={[]}
        constraintAlert={emptyConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    fireEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the backdrop is clicked", () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={onClose}
        opsecAlerts={[]}
        constraintAlert={emptyConstraint}
      />,
      { wrapper: IntlWrapper },
    );
    // The backdrop is the first div with aria-hidden="true"
    const backdrop = document.querySelector('[aria-hidden="true"]')!;
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
