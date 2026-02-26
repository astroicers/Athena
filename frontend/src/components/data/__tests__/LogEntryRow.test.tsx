import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LogEntryRow } from "@/components/data/LogEntryRow";
import { LogSeverity } from "@/types/enums";
import type { LogEntry } from "@/types/log";

describe("LogEntryRow", () => {
  it("renders severity label and message", () => {
    const entry: LogEntry = {
      id: "log-1",
      timestamp: "2026-02-26T14:30:00Z",
      severity: LogSeverity.ERROR,
      source: "caldera",
      message: "Connection failed",
      operationId: "op-1",
      techniqueId: null,
    };
    render(<LogEntryRow entry={entry} />);
    expect(screen.getByText("[error]")).toBeInTheDocument();
    expect(screen.getByText("Connection failed")).toBeInTheDocument();
  });
});
