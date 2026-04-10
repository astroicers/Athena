// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

/**
 * Tech-debt D3: Vitest test for the War Room error boundary.
 *
 * Tests that the Next.js App Router error.tsx boundary:
 *   1. Renders the error message from the Error object
 *   2. Renders a Retry button that calls the reset callback
 *   3. Does not crash on Error objects with optional digest field
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import WarRoomError from "../error";

// next-intl useTranslations mock — the error boundary uses t() for
// localised strings; we stub it to return the key itself so assertions
// can match on the translation key names.
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

describe("WarRoomError boundary", () => {
  afterEach(cleanup);

  it("renders the error message", () => {
    const error = new Error("Something went wrong in render");
    render(<WarRoomError error={error} reset={vi.fn()} />);

    expect(
      screen.getByText(/Something went wrong in render/),
    ).toBeDefined();
  });

  it("renders the retry button and calls reset on click", () => {
    const reset = vi.fn();
    render(
      <WarRoomError error={new Error("crash")} reset={reset} />,
    );

    const button = screen.getByRole("button");
    expect(button).toBeDefined();
    fireEvent.click(button);
    expect(reset).toHaveBeenCalledOnce();
  });

  it("renders the error boundary title via translation key", () => {
    render(
      <WarRoomError error={new Error("test")} reset={vi.fn()} />,
    );

    // The mock returns the key itself as text
    expect(screen.getByText("errorBoundaryTitle")).toBeDefined();
  });

  it("renders the digest when present", () => {
    const error = Object.assign(new Error("test"), {
      digest: "abc-123",
    });
    render(<WarRoomError error={error} reset={vi.fn()} />);

    expect(screen.getByText(/abc-123/)).toBeDefined();
  });

  it("does not crash when digest is undefined", () => {
    const error = new Error("no digest");
    render(<WarRoomError error={error} reset={vi.fn()} />);

    // Should render without throwing
    expect(screen.getByText(/no digest/)).toBeDefined();
  });
});
