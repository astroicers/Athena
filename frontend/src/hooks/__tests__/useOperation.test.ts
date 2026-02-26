import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useOperation } from "@/hooks/useOperation";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useOperation", () => {
  it("fetches operation data", async () => {
    const mockOp = {
      id: "op-1",
      name: "PHANTOM-EYE",
      status: "active",
      current_ooda_phase: "observe",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockOp),
      }),
    );

    const { result } = renderHook(() => useOperation("op-1"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.operation).toBeTruthy();
    expect(result.current.operation?.name).toBe("PHANTOM-EYE");
  });

  it("starts with loading state", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockReturnValue(new Promise(() => {})),
    );

    const { result } = renderHook(() => useOperation("op-1"));
    expect(result.current.isLoading).toBe(true);
    expect(result.current.operation).toBeNull();
  });
});
