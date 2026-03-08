// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IntlWrapper } from "@/test/intl-wrapper";
import { TerminalPanel } from "@/components/terminal/TerminalPanel";
import type { UseTerminalReturn, TerminalEntry } from "@/hooks/useTerminal";

// jsdom does not implement scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// ---------------------------------------------------------------------------
// Mock useTerminal hook
// ---------------------------------------------------------------------------
const mockSendCommand = vi.fn();
const mockClear = vi.fn();

let mockEntries: TerminalEntry[] = [];
let mockIsConnected = true;

vi.mock("@/hooks/useTerminal", () => ({
  useTerminal: (): UseTerminalReturn => ({
    entries: mockEntries,
    prompt: "user@target:~$ ",
    isConnected: mockIsConnected,
    sendCommand: mockSendCommand,
    clear: mockClear,
  }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const defaultProps = {
  operationId: "op-1",
  targetId: "t-1",
  targetName: "victim",
  targetIp: "10.0.0.5",
  onClose: vi.fn(),
};

function renderPanel(overrides: Partial<typeof defaultProps> = {}) {
  return render(<TerminalPanel {...defaultProps} {...overrides} />, {
    wrapper: IntlWrapper,
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe("TerminalPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEntries = [];
    mockIsConnected = true;
  });

  it("renders the terminal title with target name and IP", () => {
    renderPanel();
    expect(screen.getByText(/victim/)).toBeInTheDocument();
    expect(screen.getByText(/10\.0\.0\.5/)).toBeInTheDocument();
  });

  it("renders terminal entries of different types", () => {
    mockEntries = [
      { type: "input", text: "whoami", timestamp: "2026-03-08T00:00:00Z" },
      { type: "output", text: "root", timestamp: "2026-03-08T00:00:01Z" },
      { type: "error", text: "permission denied", timestamp: "2026-03-08T00:00:02Z" },
      { type: "system", text: "Connection closed.", timestamp: "2026-03-08T00:00:03Z" },
    ];
    renderPanel();
    expect(screen.getByText("whoami")).toBeInTheDocument();
    expect(screen.getByText("root")).toBeInTheDocument();
    expect(screen.getByText("permission denied")).toBeInTheDocument();
    expect(screen.getByText("Connection closed.")).toBeInTheDocument();
  });

  it("calls sendCommand on form submit", async () => {
    renderPanel();
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "id");
    fireEvent.submit(input.closest("form")!);
    expect(mockSendCommand).toHaveBeenCalledWith("id");
  });

  it("does not send empty commands", async () => {
    renderPanel();
    const input = screen.getByRole("textbox");
    fireEvent.submit(input.closest("form")!);
    expect(mockSendCommand).not.toHaveBeenCalled();
  });

  // -----------------------------------------------------------------------
  // SPEC-024: Arrow keys navigate command history
  // -----------------------------------------------------------------------
  describe("command history via arrow keys", () => {
    it("ArrowUp recalls previous commands", async () => {
      renderPanel();
      const input = screen.getByRole("textbox");

      // Submit two commands
      await userEvent.type(input, "ls");
      fireEvent.submit(input.closest("form")!);
      await userEvent.type(input, "pwd");
      fireEvent.submit(input.closest("form")!);

      // ArrowUp should recall "pwd" (most recent, index 0 in history)
      fireEvent.keyDown(input, { key: "ArrowUp" });
      expect(input).toHaveValue("pwd");

      // ArrowUp again should recall "ls"
      fireEvent.keyDown(input, { key: "ArrowUp" });
      expect(input).toHaveValue("ls");
    });

    it("ArrowDown navigates forward through history", async () => {
      renderPanel();
      const input = screen.getByRole("textbox");

      // Submit commands
      await userEvent.type(input, "ls");
      fireEvent.submit(input.closest("form")!);
      await userEvent.type(input, "pwd");
      fireEvent.submit(input.closest("form")!);

      // Navigate up twice
      fireEvent.keyDown(input, { key: "ArrowUp" });
      fireEvent.keyDown(input, { key: "ArrowUp" });
      expect(input).toHaveValue("ls");

      // Navigate down once — back to "pwd"
      fireEvent.keyDown(input, { key: "ArrowDown" });
      expect(input).toHaveValue("pwd");

      // Navigate down again — clears input (back to live prompt)
      fireEvent.keyDown(input, { key: "ArrowDown" });
      expect(input).toHaveValue("");
    });

    it("ArrowUp at end of history stays on oldest entry", async () => {
      renderPanel();
      const input = screen.getByRole("textbox");

      await userEvent.type(input, "only-cmd");
      fireEvent.submit(input.closest("form")!);

      fireEvent.keyDown(input, { key: "ArrowUp" });
      expect(input).toHaveValue("only-cmd");

      // Pressing up again should not change
      fireEvent.keyDown(input, { key: "ArrowUp" });
      expect(input).toHaveValue("only-cmd");
    });

    it("ArrowDown with no history does nothing", () => {
      renderPanel();
      const input = screen.getByRole("textbox");
      fireEvent.keyDown(input, { key: "ArrowDown" });
      expect(input).toHaveValue("");
    });
  });

  // -----------------------------------------------------------------------
  // SPEC-024: sendCommand calls addEntry (verified via mock)
  // -----------------------------------------------------------------------
  describe("sendCommand integration", () => {
    it("sendCommand is invoked with the typed command text", async () => {
      renderPanel();
      const input = screen.getByRole("textbox");

      await userEvent.type(input, "nmap -sV 10.0.0.1");
      fireEvent.submit(input.closest("form")!);

      expect(mockSendCommand).toHaveBeenCalledTimes(1);
      expect(mockSendCommand).toHaveBeenCalledWith("nmap -sV 10.0.0.1");
    });

    it("clears the input field after submission", async () => {
      renderPanel();
      const input = screen.getByRole("textbox");

      await userEvent.type(input, "whoami");
      fireEvent.submit(input.closest("form")!);

      expect(input).toHaveValue("");
    });
  });

  // -----------------------------------------------------------------------
  // Disconnected state
  // -----------------------------------------------------------------------
  describe("disconnected state", () => {
    it("disables input when not connected", () => {
      mockIsConnected = false;
      renderPanel();
      const input = screen.getByRole("textbox");
      expect(input).toBeDisabled();
    });

    it("shows disconnected indicator when not connected", () => {
      mockIsConnected = false;
      renderPanel();
      expect(screen.getByText("DISCONNECTED")).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // Clear and close buttons
  // -----------------------------------------------------------------------
  it("calls clear when clear button is clicked", async () => {
    renderPanel();
    const clearButton = screen.getByText("CLEAR");
    await userEvent.click(clearButton);
    expect(mockClear).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when close button is clicked", async () => {
    renderPanel();
    // The close button renders the "x" character
    const closeButton = screen.getByRole("button", { name: /✕/ });
    await userEvent.click(closeButton);
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });
});
