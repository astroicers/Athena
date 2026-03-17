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
import { render, screen, fireEvent } from "@testing-library/react";
import { ConstraintBanner } from "@/components/layout/ConstraintBanner";

describe("ConstraintBanner", () => {
  it("returns null when constraints are inactive", () => {
    const { container } = render(
      <ConstraintBanner
        constraints={{ active: false, messages: ["ROE limit reached"] }}
      />
    );
    expect(container.innerHTML).toBe("");
  });

  it("returns null when messages array is empty", () => {
    const { container } = render(
      <ConstraintBanner constraints={{ active: true, messages: [] }} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders constraint messages when active", () => {
    render(
      <ConstraintBanner
        constraints={{
          active: true,
          messages: ["Time window closing", "Bandwidth limited"],
        }}
      />
    );
    expect(screen.getByText("CONSTRAINT ACTIVE")).toBeInTheDocument();
    expect(
      screen.getByText("Time window closing, Bandwidth limited")
    ).toBeInTheDocument();
  });

  it("uses red styling for critical keyword messages", () => {
    const { container } = render(
      <ConstraintBanner
        constraints={{ active: true, messages: ["critical ROE violation"] }}
      />
    );
    const banner = container.firstChild as HTMLElement;
    expect(banner.className).toContain("bg-red-500");
  });

  it("uses red styling for breach keyword messages", () => {
    const { container } = render(
      <ConstraintBanner
        constraints={{ active: true, messages: ["OPSEC breach detected"] }}
      />
    );
    const banner = container.firstChild as HTMLElement;
    expect(banner.className).toContain("bg-red-500");
  });

  it("uses amber styling for non-critical messages", () => {
    const { container } = render(
      <ConstraintBanner
        constraints={{ active: true, messages: ["Bandwidth limited"] }}
      />
    );
    const banner = container.firstChild as HTMLElement;
    expect(banner.className).toContain("bg-amber-600");
  });

  it("dismisses banner when dismiss button is clicked", () => {
    const { container } = render(
      <ConstraintBanner
        constraints={{ active: true, messages: ["Time window closing"] }}
      />
    );
    expect(screen.getByText("CONSTRAINT ACTIVE")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Dismiss constraint banner"));
    expect(container.innerHTML).toBe("");
  });

  it("renders domain override buttons and calls onOverride", () => {
    const handleOverride = vi.fn();
    render(
      <ConstraintBanner
        constraints={{
          active: true,
          messages: ["Scope restricted"],
          domains: ["network", "webapp"],
        }}
        onOverride={handleOverride}
      />
    );

    const networkBtn = screen.getByText("Override network");
    const webappBtn = screen.getByText("Override webapp");
    expect(networkBtn).toBeInTheDocument();
    expect(webappBtn).toBeInTheDocument();

    fireEvent.click(networkBtn);
    expect(handleOverride).toHaveBeenCalledWith("network");
  });

  it("does not render override buttons when onOverride is absent", () => {
    render(
      <ConstraintBanner
        constraints={{
          active: true,
          messages: ["Scope restricted"],
          domains: ["network"],
        }}
      />
    );
    expect(screen.queryByText("Override network")).not.toBeInTheDocument();
  });

  it("does not render override buttons when domains is empty", () => {
    const handleOverride = vi.fn();
    render(
      <ConstraintBanner
        constraints={{
          active: true,
          messages: ["Scope restricted"],
          domains: [],
        }}
        onOverride={handleOverride}
      />
    );
    expect(screen.queryByText(/Override/)).not.toBeInTheDocument();
  });
});
