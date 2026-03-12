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
import { PageHeader } from "@/components/layout/PageHeader";

describe("PageHeader", () => {
  it("renders the title", () => {
    render(<PageHeader title="Reconnaissance" />);
    expect(screen.getByText("Reconnaissance")).toBeInTheDocument();
  });

  it("renders operationCode badge when provided", () => {
    render(<PageHeader title="Dashboard" operationCode="OP-NIGHTFALL" />);
    expect(screen.getByText("OP-NIGHTFALL")).toBeInTheDocument();
  });

  it("does not render operationCode badge when absent", () => {
    const { container } = render(<PageHeader title="Dashboard" />);
    // The badge is a span inside the header — when no operationCode, only the h2 exists
    const spans = container.querySelectorAll("span");
    expect(spans.length).toBe(0);
  });

  it("renders trailing content when provided", () => {
    render(
      <PageHeader
        title="Tools"
        trailing={<button>Settings</button>}
      />
    );
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("does not render trailing wrapper when trailing is absent", () => {
    const { container } = render(<PageHeader title="Tools" />);
    // header > div.flex (left side only), no trailing div
    const header = container.querySelector("header")!;
    expect(header.children.length).toBe(1);
  });
});
