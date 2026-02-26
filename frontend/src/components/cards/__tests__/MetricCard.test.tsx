import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricCard } from "@/components/cards/MetricCard";

describe("MetricCard", () => {
  it("renders value", () => {
    render(<MetricCard title="Agents" value="12" />);
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(<MetricCard title="Success" value="73%" subtitle="+5% vs last op" />);
    expect(screen.getByText("+5% vs last op")).toBeInTheDocument();
  });
});
