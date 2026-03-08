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
import { render, screen, fireEvent } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { TopologyLegend } from "../TopologyLegend";
import en from "../../../../messages/en.json";
import zhTW from "../../../../messages/zh-TW.json";

describe("TopologyLegend", () => {
  it("renders collapsed state by default", () => {
    render(<TopologyLegend />, { wrapper: IntlWrapper });
    // In collapsed state the legend title button is visible
    expect(screen.getByText(/LEGEND/i)).toBeTruthy();
  });

  it("expands when clicking the collapsed button", () => {
    render(<TopologyLegend />, { wrapper: IntlWrapper });
    const toggleBtn = screen.getByText(/LEGEND/i);
    fireEvent.click(toggleBtn);
    // After expansion, node status section should be visible
    expect(screen.getByText(/NODE STATUS/i)).toBeTruthy();
    expect(screen.getByText(/CONNECTIONS/i)).toBeTruthy();
  });

  it("shows all node status entries when expanded", () => {
    render(<TopologyLegend />, { wrapper: IntlWrapper });
    fireEvent.click(screen.getByText(/LEGEND/i));
    // Some labels appear in both NODE_ENTRIES and EDGE_ENTRIES (shared translation keys),
    // so use getAllByText to avoid "multiple elements" errors.
    expect(screen.getAllByText("Active Session").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Attacking").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Scanning").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Idle Target").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("C2 Server")).toBeTruthy();
  });

  it("shows all edge entries when expanded", () => {
    render(<TopologyLegend />, { wrapper: IntlWrapper });
    fireEvent.click(screen.getByText(/LEGEND/i));
    // Edge entries use the same translation keys as node entries for some
    // but "Lateral Move" is edge-only
    expect(screen.getByText("Lateral Move")).toBeTruthy();
  });

  it("shows status badges section when expanded", () => {
    render(<TopologyLegend />, { wrapper: IntlWrapper });
    fireEvent.click(screen.getByText(/LEGEND/i));
    expect(screen.getByText(/STATUS BADGES/i)).toBeTruthy();
    expect(screen.getByText("Recon Complete")).toBeTruthy();
    expect(screen.getByText("Compromised")).toBeTruthy();
    expect(screen.getByText("Privilege Level")).toBeTruthy();
    expect(screen.getByText("Persistence / Lateral")).toBeTruthy();
  });

  it("shows kill chain progress section when expanded", () => {
    render(<TopologyLegend />, { wrapper: IntlWrapper });
    fireEvent.click(screen.getByText(/LEGEND/i));
    expect(screen.getByText("Kill Chain Progress")).toBeTruthy();
    expect(screen.getByText("RECON")).toBeTruthy();
    expect(screen.getByText("ACTION")).toBeTruthy();
  });

  it("collapses back when clicking the expanded header", () => {
    render(<TopologyLegend />, { wrapper: IntlWrapper });
    // Expand
    fireEvent.click(screen.getByText(/LEGEND/i));
    expect(screen.getByText(/NODE STATUS/i)).toBeTruthy();
    // Collapse — the expanded header also contains "LEGEND"
    const collapseBtn = screen.getByText(/LEGEND/i);
    fireEvent.click(collapseBtn);
    // After collapse, detailed sections should no longer be visible
    expect(screen.queryByText(/NODE STATUS/i)).toBeNull();
  });

  // ── SPEC-042: Attack Path legend entry ──

  it("has 'attackPath' key in EDGE_ENTRIES (Legend.attackPath i18n key exists in en.json)", () => {
    // Verify the i18n key exists — this is a prerequisite for SPEC-042 Phase 5
    const legendKeys = en.Legend as Record<string, string>;
    expect(legendKeys).toHaveProperty("attackPath");
    expect(legendKeys.attackPath).toBe("Attack Path (Recommended)");
  });

  it("has 'attackPath' key in zh-TW.json Legend section", () => {
    const legendKeys = zhTW.Legend as Record<string, string>;
    expect(legendKeys).toHaveProperty("attackPath");
    // Chinese translation
    expect(typeof legendKeys.attackPath).toBe("string");
    expect(legendKeys.attackPath.length).toBeGreaterThan(0);
  });

  it("i18n: Legend.attackPath values are non-empty in both locales", () => {
    const enVal = (en.Legend as Record<string, string>).attackPath;
    const zhVal = (zhTW.Legend as Record<string, string>).attackPath;
    expect(enVal).toBeTruthy();
    expect(zhVal).toBeTruthy();
    // They should be different (one English, one Chinese)
    expect(enVal).not.toBe(zhVal);
  });
});
