import { describe, it, expect, vi, beforeEach } from "vitest";
import { toApiBody, fromApiResponse, api } from "@/lib/api";

describe("toApiBody (camelCase → snake_case)", () => {
  it("converts simple camelCase keys", () => {
    const result = toApiBody({ operationId: "op-1", riskLevel: "high" });
    expect(result).toEqual({ operation_id: "op-1", risk_level: "high" });
  });

  it("converts nested objects recursively", () => {
    const result = toApiBody({
      operationData: { currentPhase: "observe", threatLevel: 7 },
    });
    expect(result).toEqual({
      operation_data: { current_phase: "observe", threat_level: 7 },
    });
  });

  it("converts arrays of objects", () => {
    const result = toApiBody([
      { techniqueId: "T1003" },
      { techniqueId: "T1134" },
    ]);
    expect(result).toEqual([
      { technique_id: "T1003" },
      { technique_id: "T1134" },
    ]);
  });

  it("preserves primitive values", () => {
    expect(toApiBody("hello")).toBe("hello");
    expect(toApiBody(42)).toBe(42);
    expect(toApiBody(null)).toBe(null);
  });
});

describe("fromApiResponse (snake_case → camelCase)", () => {
  it("converts simple snake_case keys", () => {
    const result = fromApiResponse<Record<string, string>>({
      operation_id: "op-1",
      risk_level: "high",
    });
    expect(result).toEqual({ operationId: "op-1", riskLevel: "high" });
  });

  it("converts nested response objects", () => {
    const result = fromApiResponse({
      operation_data: { current_phase: "observe" },
    });
    expect(result).toEqual({
      operationData: { currentPhase: "observe" },
    });
  });
});

describe("api.get", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("calls fetch with correct URL and headers", async () => {
    const mockResponse = { operation_id: "op-1", status: "active" };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse),
      }),
    );

    const result = await api.get<{ operationId: string; status: string }>(
      "/operations/op-1",
    );

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/operations/op-1"),
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      }),
    );
    expect(result).toEqual({ operationId: "op-1", status: "active" });
  });
});
