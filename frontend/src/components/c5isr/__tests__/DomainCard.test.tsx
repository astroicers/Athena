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
import { DomainCard } from "@/components/c5isr/DomainCard";
import { C5ISRDomain, C5ISRDomainStatus } from "@/types/enums";

describe("DomainCard", () => {
  it("displays domain name, status, and health", () => {
    render(
      <DomainCard
        domain={{
          id: "c5-1",
          operationId: "op-1",
          domain: C5ISRDomain.CYBER,
          status: C5ISRDomainStatus.OPERATIONAL,
          healthPct: 93,
          detail: "All systems nominal",
        }}
      />,
    );
    expect(screen.getByText("CYBER")).toBeInTheDocument();
    expect(screen.getByText("OPERATIONAL")).toBeInTheDocument();
    expect(screen.getByText("93%")).toBeInTheDocument();
  });
});
