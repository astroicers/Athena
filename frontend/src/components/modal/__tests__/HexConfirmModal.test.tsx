import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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
    );
    expect(container.innerHTML).toBe("");
  });

  it("shows title and risk label when open", () => {
    render(<HexConfirmModal isOpen={true} {...defaultProps} />);
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
    );
    expect(screen.getByText("CONFIRM EXECUTE")).toBeInTheDocument();
    expect(
      screen.getByText(/double confirmation/),
    ).toBeInTheDocument();
  });
});
