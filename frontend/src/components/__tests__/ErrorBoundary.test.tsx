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
 * Unit tests for the generic ErrorBoundary component.
 *
 * Covers:
 *   1. Normal render — children appear when no error
 *   2. Error fallback — default UI with error message shown on throw
 *   3. Retry/reset — clicking retry resets state and re-renders children
 *   4. Custom fallback — `fallback` prop takes priority over default UI
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ErrorBoundary } from "../ErrorBoundary";

// A component that throws on demand
function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("Test explosion");
  return <div>Child rendered OK</div>;
}

describe("ErrorBoundary", () => {
  afterEach(cleanup);

  // Suppress React error boundary console.error noise during tests
  const originalConsoleError = console.error;
  beforeAll(() => {
    console.error = (...args: unknown[]) => {
      const msg = typeof args[0] === "string" ? args[0] : "";
      if (msg.includes("Error: Uncaught") || msg.includes("The above error")) return;
      originalConsoleError(...args);
    };
  });
  afterAll(() => {
    console.error = originalConsoleError;
  });

  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <div>Hello world</div>
      </ErrorBoundary>,
    );

    expect(screen.getByText("Hello world")).toBeDefined();
  });

  it("shows default fallback UI with error message when child throws", () => {
    const labels = {
      title: "Oops",
      message: "Something broke",
      retry: "Retry now",
    };

    render(
      <ErrorBoundary labels={labels}>
        <ThrowingChild shouldThrow />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Oops")).toBeDefined();
    expect(screen.getByText("Test explosion")).toBeDefined();
    expect(screen.getByRole("button", { name: "Retry now" })).toBeDefined();
  });

  it("resets and re-renders children when retry button is clicked", () => {
    let shouldThrow = true;

    function ConditionalChild() {
      if (shouldThrow) throw new Error("boom");
      return <div>Recovered</div>;
    }

    render(
      <ErrorBoundary>
        <ConditionalChild />
      </ErrorBoundary>,
    );

    // Should show default fallback (no labels → hardcoded English)
    expect(screen.getByText("Something went wrong")).toBeDefined();

    // Fix the child, then click retry
    shouldThrow = false;
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(screen.getByText("Recovered")).toBeDefined();
  });

  it("renders custom fallback prop instead of default UI", () => {
    render(
      <ErrorBoundary fallback={<div>Custom error view</div>}>
        <ThrowingChild shouldThrow />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Custom error view")).toBeDefined();
    // Default UI should NOT be present
    expect(screen.queryByText("Something went wrong")).toBeNull();
  });
});
