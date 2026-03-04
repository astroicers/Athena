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
import { IntlWrapper } from "@/test/intl-wrapper";
import { OODAIndicator } from "@/components/ooda/OODAIndicator";
import { OODAPhase } from "@/types/enums";

describe("OODAIndicator", () => {
  it("highlights the active phase", () => {
    render(<OODAIndicator currentPhase={OODAPhase.ORIENT} />, { wrapper: IntlWrapper });
    const orient = screen.getByText("ORIENT");
    expect(orient.closest("div")).toHaveClass("bg-athena-accent/20");
  });
});
