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
import { HexIcon } from "@/components/atoms/HexIcon";

describe("HexIcon", () => {
  it("renders the icon text", () => {
    render(<HexIcon icon="⬡" />);
    expect(screen.getByText("⬡")).toBeInTheDocument();
  });
});
