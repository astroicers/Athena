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
import { MITRECell } from "@/components/mitre/MITRECell";
import { TechniqueStatus } from "@/types/enums";

describe("MITRECell", () => {
  it("renders MITRE ID with success color class", () => {
    render(
      <MITRECell mitreId="T1003.001" name="LSASS Dump" status={TechniqueStatus.SUCCESS} />,
    );
    expect(screen.getByText("T1003.001")).toBeInTheDocument();
    const button = screen.getByRole("button");
    expect(button.className).toContain("bg-[#22C55E20]");
  });
});
