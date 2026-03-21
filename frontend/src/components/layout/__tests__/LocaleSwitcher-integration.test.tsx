// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

/**
 * Integration tests for LocaleSwitcher in the context of the global header.
 *
 * Unlike the unit tests in LocaleSwitcher.test.tsx (which test the component
 * in isolation), these tests verify the LocaleSwitcher behaviour when rendered
 * inside a header-like wrapper, exercising the useTransition pending state and
 * the full click -> setLocale flow via userEvent (not fireEvent).
 */

const mockSetLocale = vi.fn(() => Promise.resolve());
const mockUseLocale = vi.fn(() => "en");
let mockIsPending = false;
const mockStartTransition = vi.fn((cb: () => void) => {
  cb();
});

vi.mock("next-intl", () => ({
  useLocale: () => mockUseLocale(),
}));

vi.mock("@/app/actions", () => ({
  setLocale: (...args: unknown[]) => mockSetLocale(...args),
}));

vi.mock("react", async () => {
  const actual = await vi.importActual<typeof import("react")>("react");
  return {
    ...actual,
    useTransition: () => [mockIsPending, mockStartTransition],
  };
});

import { LocaleSwitcher } from "@/components/layout/LocaleSwitcher";

/** Minimal header wrapper that mirrors the PageHeader trailing slot structure. */
function HeaderWrapper() {
  return (
    <header data-testid="global-header" className="flex items-center">
      <div className="flex items-center gap-3">
        <LocaleSwitcher />
      </div>
    </header>
  );
}

describe("LocaleSwitcher integration (in global header)", () => {
  beforeEach(() => {
    mockSetLocale.mockClear();
    mockUseLocale.mockReset();
    mockUseLocale.mockReturnValue("en");
    mockStartTransition.mockClear();
    mockIsPending = false;
  });

  it("renders locale switcher button in header", () => {
    render(<HeaderWrapper />);
    const header = screen.getByTestId("global-header");
    expect(header).toBeInTheDocument();
    const button = screen.getByRole("button");
    expect(header.contains(button)).toBe(true);
  });

  it('shows EN when current locale is zh-TW', () => {
    mockUseLocale.mockReturnValue("zh-TW");
    render(<HeaderWrapper />);
    expect(screen.getByRole("button", { name: "EN" })).toBeInTheDocument();
  });

  it('shows Chinese label when current locale is en', () => {
    mockUseLocale.mockReturnValue("en");
    render(<HeaderWrapper />);
    expect(
      screen.getByRole("button", { name: /中文/ }),
    ).toBeInTheDocument();
  });

  it("calls setLocale on click", async () => {
    mockUseLocale.mockReturnValue("en");
    const user = userEvent.setup();

    render(<HeaderWrapper />);
    await user.click(screen.getByRole("button"));

    expect(mockStartTransition).toHaveBeenCalledTimes(1);
    expect(mockSetLocale).toHaveBeenCalledWith("zh-TW");
  });

  it("button is disabled during transition", () => {
    mockIsPending = true;
    render(<HeaderWrapper />);

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    expect(button.textContent).toBe("...");
  });
});
