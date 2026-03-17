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
import { render, screen } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { HexConfirmModal } from "@/components/modal/HexConfirmModal";
import { RiskLevel } from "@/types/enums";

const defaultProps = {
  title: "Execute T1003.001",
  riskLevel: RiskLevel.HIGH,
  onConfirm: vi.fn(),
  onCancel: vi.fn(),
};

describe("HexConfirmModal", () => {
  it("returns null when closed", () => {
    const { container } = render(
      <HexConfirmModal isOpen={false} {...defaultProps} />,
      { wrapper: IntlWrapper },
    );
    expect(container.innerHTML).toBe("");
  });

  it("shows title and risk label when open", () => {
    render(<HexConfirmModal isOpen={true} {...defaultProps} />, { wrapper: IntlWrapper });
    expect(screen.getByText("Execute T1003.001")).toBeInTheDocument();
    expect(screen.getByText("HIGH RISK")).toBeInTheDocument();
  });

  it("shows CONFIRM EXECUTE for critical risk", () => {
    render(
      <HexConfirmModal
        isOpen={true}
        {...defaultProps}
        riskLevel={RiskLevel.CRITICAL}
      />,
      { wrapper: IntlWrapper },
    );
    expect(screen.getByText("CONFIRM EXECUTE")).toBeInTheDocument();
    expect(
      screen.getByText(/double confirmation/),
    ).toBeInTheDocument();
  });
});
