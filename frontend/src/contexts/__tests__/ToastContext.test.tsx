// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { ToastProvider, useToast } from "@/contexts/ToastContext";
import type { ReactNode } from "react";

const wrapper = ({ children }: { children: ReactNode }) => (
  <ToastProvider>{children}</ToastProvider>
);

describe("useToast", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("throws when used outside ToastProvider", () => {
    expect(() => renderHook(() => useToast())).toThrow(
      "useToast must be used inside ToastProvider",
    );
  });

  it("addToast adds a toast with default severity info", () => {
    const { result } = renderHook(() => useToast(), { wrapper });
    act(() => result.current.addToast("Hello"));
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe("Hello");
    expect(result.current.toasts[0].severity).toBe("info");
  });

  it("removeToast removes by id", () => {
    const { result } = renderHook(() => useToast(), { wrapper });
    act(() => result.current.addToast("A"));
    const id = result.current.toasts[0].id;
    act(() => result.current.removeToast(id));
    expect(result.current.toasts).toHaveLength(0);
  });

  it("auto-removes after 4000ms", () => {
    const { result } = renderHook(() => useToast(), { wrapper });
    act(() => result.current.addToast("Temp"));
    expect(result.current.toasts).toHaveLength(1);
    act(() => vi.advanceTimersByTime(4000));
    expect(result.current.toasts).toHaveLength(0);
  });
});
