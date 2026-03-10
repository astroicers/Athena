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
import { DomainCard } from "@/components/c5isr/DomainCard";
import { C5ISRDomain, C5ISRDomainStatus } from "@/types/enums";
import { IntlWrapper } from "@/test/intl-wrapper";
import type { DomainReport } from "@/types/c5isr";

const baseProps = {
  id: "c5-1",
  operationId: "op-1",
  domain: C5ISRDomain.CYBER,
  status: C5ISRDomainStatus.OPERATIONAL,
  healthPct: 93,
  detail: "All systems nominal",
  numerator: null,
  denominator: null,
  metricLabel: "",
  report: null,
};

const sampleReport: DomainReport = {
  executive_summary: "3/5 attacks succeeded",
  health_pct: 72.5,
  status: "nominal",
  metrics: [
    { name: "recon_success", value: 80.0, weight: 0.25, numerator: 4, denominator: 5 },
    { name: "exploit_success", value: 60.0, weight: 0.45, numerator: 3, denominator: 5 },
    { name: "recent_trend", value: 80.0, weight: 0.30, numerator: null, denominator: null },
  ],
  asset_roster: [{ type: "target", hostname: "web-01", ip_address: "10.0.0.1" }],
  tactical_assessment: "Recon success high, exploit rate moderate.",
  risk_vectors: [
    { severity: "WARN", message: "Exploit success rate below 70%" },
  ],
  recommended_actions: ["Increase exploit variety"],
  cross_domain_impacts: ["Computers: exploit success drives compromise rate"],
};

describe("DomainCard", () => {
  it("displays domain name, status, and health", () => {
    render(
      <IntlWrapper>
        <DomainCard domain={baseProps} />
      </IntlWrapper>,
    );
    expect(screen.getByText("CYBER")).toBeInTheDocument();
    expect(screen.getByText("OPERATIONAL")).toBeInTheDocument();
    expect(screen.getByText("93%")).toBeInTheDocument();
  });

  it("does not show expand indicator when report is null", () => {
    const { container } = render(
      <IntlWrapper>
        <DomainCard domain={baseProps} />
      </IntlWrapper>,
    );
    // No cursor-pointer class means no expand
    expect(container.querySelector(".cursor-pointer")).toBeNull();
  });

  it("shows expand indicator when report is present", () => {
    const { container } = render(
      <IntlWrapper>
        <DomainCard domain={{ ...baseProps, report: sampleReport }} />
      </IntlWrapper>,
    );
    expect(container.querySelector(".cursor-pointer")).not.toBeNull();
  });

  it("expands and collapses on click", () => {
    render(
      <IntlWrapper>
        <DomainCard domain={{ ...baseProps, report: sampleReport }} />
      </IntlWrapper>,
    );
    // Initially collapsed -- tactical assessment not visible
    expect(screen.queryByText("Recon success high, exploit rate moderate.")).toBeNull();

    // Click to expand
    fireEvent.click(screen.getByText("CYBER").closest("[class*='bg-athena-surface']")!);
    expect(screen.getByText("Recon success high, exploit rate moderate.")).toBeInTheDocument();
    expect(screen.getByText("[WARN] Exploit success rate below 70%")).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(screen.getByText("CYBER").closest("[class*='bg-athena-surface']")!);
    expect(screen.queryByText("Recon success high, exploit rate moderate.")).toBeNull();
  });

  it("report null prevents expand on click", () => {
    render(
      <IntlWrapper>
        <DomainCard domain={baseProps} />
      </IntlWrapper>,
    );
    fireEvent.click(screen.getByText("CYBER").closest("[class*='bg-athena-surface']")!);
    // Nothing expanded -- no report sections visible
    expect(screen.queryByText("Recon success high, exploit rate moderate.")).toBeNull();
  });
});
