// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LocaleSwitcher } from "@/components/layout/LocaleSwitcher";

const mockSetLocale = vi.fn();

vi.mock("next-intl", () => ({
  useLocale: vi.fn(() => "en"),
}));

vi.mock("@/app/actions", () => ({
  setLocale: (...args: unknown[]) => mockSetLocale(...args),
}));

describe("LocaleSwitcher", () => {
  beforeEach(() => {
    mockSetLocale.mockClear();
  });

  it('shows the Chinese label when current locale is "en"', () => {
    render(<LocaleSwitcher />);
    expect(screen.getByRole("button", { name: /中文/ })).toBeInTheDocument();
  });

  it('shows the English label when current locale is "zh-TW"', async () => {
    const nextIntl = await import("next-intl");
    (nextIntl.useLocale as ReturnType<typeof vi.fn>).mockReturnValue("zh-TW");

    render(<LocaleSwitcher />);
    expect(screen.getByRole("button", { name: "EN" })).toBeInTheDocument();
  });

  it("calls setLocale with the opposite locale on click", async () => {
    const nextIntl = await import("next-intl");
    (nextIntl.useLocale as ReturnType<typeof vi.fn>).mockReturnValue("en");

    render(<LocaleSwitcher />);
    fireEvent.click(screen.getByRole("button"));

    // setLocale is called inside startTransition, which runs synchronously in tests
    expect(mockSetLocale).toHaveBeenCalledWith("zh-TW");
  });

  it('switches to "en" when current locale is "zh-TW"', async () => {
    const nextIntl = await import("next-intl");
    (nextIntl.useLocale as ReturnType<typeof vi.fn>).mockReturnValue("zh-TW");

    render(<LocaleSwitcher />);
    fireEvent.click(screen.getByRole("button"));

    expect(mockSetLocale).toHaveBeenCalledWith("en");
  });
});
