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
import { render, screen, fireEvent } from "@testing-library/react";
import { useEffect } from "react";
import { ToastProvider, useToast } from "@/contexts/ToastContext";
import { ToastContainer } from "@/components/ui/Toast";
import type { ToastSeverity } from "@/contexts/ToastContext";

// Helper: renders ToastContainer inside provider and injects toasts
function ToastHarness({
  messages,
}: {
  messages: Array<{ msg: string; sev: ToastSeverity }>;
}) {
  const { addToast } = useToast();
  useEffect(() => {
    messages.forEach(({ msg, sev }) => addToast(msg, sev));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <ToastContainer />;
}

function renderWithProvider(
  messages: Array<{ msg: string; sev: ToastSeverity }>,
) {
  return render(
    <ToastProvider>
      <ToastHarness messages={messages} />
    </ToastProvider>,
  );
}

describe("ToastContainer", () => {
  it("renders nothing when no toasts", () => {
    const { container } = render(
      <ToastProvider>
        <ToastContainer />
      </ToastProvider>,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders severity labels correctly", () => {
    renderWithProvider([
      { msg: "Info msg", sev: "info" },
      { msg: "Ok msg", sev: "success" },
    ]);
    expect(screen.getByText("[INFO]")).toBeInTheDocument();
    expect(screen.getByText("[OK]")).toBeInTheDocument();
    expect(screen.getByText("Info msg")).toBeInTheDocument();
  });

  it("clicking toast dismisses it", () => {
    renderWithProvider([{ msg: "Click me", sev: "warning" }]);
    expect(screen.getByText("Click me")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Click me"));
    expect(screen.queryByText("Click me")).not.toBeInTheDocument();
  });
});
