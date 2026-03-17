// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MockBanner } from "@/components/layout/MockBanner";

describe("MockBanner", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "/api");
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllEnvs();
  });

  it("returns null when health endpoint has no mock_mode", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ status: "ok", services: {} }),
    });

    const { container } = render(<MockBanner />);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    });
    expect(container.innerHTML).toBe("");
  });

  it("returns null when mock_mode is empty object", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      json: () =>
        Promise.resolve({
          status: "ok",
          services: { mock_mode: {} },
        }),
    });

    const { container } = render(<MockBanner />);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    });
    expect(container.innerHTML).toBe("");
  });

  it("returns null when fetch fails", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

    const { container } = render(<MockBanner />);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    });
    expect(container.innerHTML).toBe("");
  });

  it("shows active mock services when mock_mode data is present", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      json: () =>
        Promise.resolve({
          status: "ok",
          services: {
            mock_mode: { llm: true, c2: true, metasploit: false },
          },
        }),
    });

    render(<MockBanner />);
    await waitFor(() => {
      expect(screen.getByText("MOCK MODE")).toBeInTheDocument();
    });
    // Only active (true) services are listed, uppercased
    expect(
      screen.getByText(/LLM, C2 — using simulated data, not real services/)
    ).toBeInTheDocument();
  });

  it("calls the correct health endpoint URL", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ status: "ok", services: {} }),
    });

    render(<MockBanner />);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/health");
    });
  });
});
