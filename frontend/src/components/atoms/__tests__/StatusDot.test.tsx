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
import { render } from "@testing-library/react";
import { StatusDot } from "@/components/atoms/StatusDot";

describe("StatusDot", () => {
  it("renders with correct color class for alive status", () => {
    const { container } = render(<StatusDot status="alive" />);
    const dot = container.querySelector("span span");
    expect(dot?.className).toContain("bg-[#22C55E20]");
  });
});
