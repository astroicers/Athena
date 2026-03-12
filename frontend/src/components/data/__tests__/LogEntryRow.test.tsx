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
import { render, screen } from "@testing-library/react";
import { IntlWrapper } from "@/test/intl-wrapper";
import { LogEntryRow } from "@/components/data/LogEntryRow";
import { LogSeverity } from "@/types/enums";
import type { LogEntry } from "@/types/log";

describe("LogEntryRow", () => {
  it("renders severity label and message", () => {
    const entry: LogEntry = {
      id: "log-1",
      timestamp: "2026-02-26T14:30:00Z",
      severity: LogSeverity.ERROR,
      source: "c2",
      message: "Connection failed",
      operationId: "op-1",
      techniqueId: null,
    };
    render(<LogEntryRow entry={entry} />, { wrapper: IntlWrapper });
    expect(screen.getByText("[ERROR]")).toBeInTheDocument();
    expect(screen.getByText("Connection failed")).toBeInTheDocument();
  });
});
