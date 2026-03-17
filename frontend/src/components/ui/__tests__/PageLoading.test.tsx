// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { PageLoading } from "@/components/ui/PageLoading";

describe("PageLoading", () => {
  it("renders INITIALIZING SYSTEMS text", () => {
    render(<PageLoading />, { wrapper: IntlWrapper });
    expect(screen.getByText("INITIALIZING SYSTEMS")).toBeInTheDocument();
  });

  it("renders 4 animated dots", () => {
    const { container } = render(<PageLoading />, { wrapper: IntlWrapper });
    const dots = container.querySelectorAll(".rounded-full");
    expect(dots).toHaveLength(4);
  });
});
