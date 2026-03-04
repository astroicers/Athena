// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

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
