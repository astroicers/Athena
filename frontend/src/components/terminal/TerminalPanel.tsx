// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: azz093093.830330@gmail.com

"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useTerminal } from "@/hooks/useTerminal";

type TerminalMode = "winrm" | "ssh" | "msf" | "psql";

const MODE_LABEL: Record<TerminalMode, string> = {
  winrm: "WinRM",
  ssh: "SSH",
  msf: "MSF",
  psql: "PSQL",
};

interface TerminalPanelProps {
  operationId: string;
  targetId: string;
  targetName: string;
  targetIp: string;
  onClose: () => void;
  terminalMode?: TerminalMode;
  credentialUser?: string;
  privilegeLevel?: string;
}

export function TerminalPanel({
  operationId,
  targetId,
  targetName,
  targetIp,
  onClose,
  terminalMode,
  credentialUser,
  privilegeLevel,
}: TerminalPanelProps) {
  const t = useTranslations("Terminal");
  const tCommon = useTranslations("Common");
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { entries, prompt, isConnected, pending, sendCommand, clear } = useTerminal(
    operationId,
    targetId,
    true,
  );

  // Auto-scroll to bottom on new output
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cmd = input.trim();
    if (!cmd) return;
    setHistory((prev) => [cmd, ...prev.slice(0, 99)]);
    setHistoryIdx(-1);
    setInput("");
    sendCommand(cmd);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowUp") {
      e.preventDefault();
      const idx = Math.min(historyIdx + 1, history.length - 1);
      setHistoryIdx(idx);
      setInput(history[idx] ?? "");
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      const idx = Math.max(historyIdx - 1, -1);
      setHistoryIdx(idx);
      setInput(idx === -1 ? "" : (history[idx] ?? ""));
    }
  }

  return (
    <div
      className="fixed bottom-0 left-[200px] right-0 z-40 h-[300px] bg-[var(--color-bg-primary)] border-t border-[var(--color-border)] flex flex-col"
      onClick={() => inputRef.current?.focus()}
    >
      {/* Header bar */}
      <div className="h-9 bg-[var(--color-bg-surface)] border-b border-[var(--color-border)] flex items-center justify-between px-3 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="w-2.5 h-2.5 bg-[var(--color-success)] rounded-full shrink-0" />
          <span className="text-athena-floor font-mono text-[var(--color-text-primary)] truncate">
            {t("title")} — {targetName} ({targetIp})
          </span>
          {terminalMode && (
            <span className="text-athena-floor font-mono px-1 border border-[var(--color-accent)] text-[var(--color-accent)] rounded shrink-0">
              {MODE_LABEL[terminalMode]}
            </span>
          )}
          {credentialUser && (
            <span className="text-athena-floor font-mono px-1 border border-[var(--color-border)] text-[var(--color-text-secondary)] rounded shrink-0">
              {credentialUser}
            </span>
          )}
          {privilegeLevel && privilegeLevel !== "none" && (
            <span
              className={`text-athena-floor font-mono px-1 border rounded shrink-0 ${
                ["administrator", "root", "system"].includes(privilegeLevel.toLowerCase())
                  ? "border-[var(--color-error)] text-[var(--color-error)]"
                  : "border-[var(--color-border)] text-[var(--color-text-tertiary)]"
              }`}
            >
              {privilegeLevel}
            </span>
          )}
          {!isConnected && (
            <span className="text-athena-floor font-mono text-[var(--color-error)] shrink-0">{tCommon("disconnected")}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clear}
            className="text-athena-floor font-mono text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] px-1"
          >
            {tCommon("clear")}
          </button>
          <button
            onClick={onClose}
            className="text-athena-floor font-mono text-[var(--color-text-tertiary)] hover:text-[var(--color-error)] px-1"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Terminal output */}
      <div className="flex-1 overflow-y-auto p-3 font-mono text-athena-floor text-[var(--color-success)] bg-[var(--color-bg-primary)]">
        {entries.map((entry, i) => (
          <div key={i}>
            {entry.type === "input" ? (
              <div className="text-[var(--color-accent)]">
                <span className="text-[var(--color-text-tertiary)]">{prompt}</span>
                {entry.text}
              </div>
            ) : entry.type === "error" ? (
              <div className="text-[var(--color-error)]">{entry.text}</div>
            ) : entry.type === "system" ? (
              <div className="text-[var(--color-text-tertiary)] italic">{entry.text}</div>
            ) : (
              <pre className="text-[var(--color-success)] whitespace-pre-wrap break-all">{entry.text}</pre>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 px-3 py-2 border-t border-[var(--color-border)] bg-[var(--color-bg-surface)] shrink-0"
      >
        <span className="text-[var(--color-text-tertiary)] font-mono text-athena-floor shrink-0">
          {prompt}
        </span>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!isConnected}
          placeholder={isConnected ? "" : t("connecting")}
          className="flex-1 bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-[var(--radius)] px-3 py-1.5 text-athena-floor font-mono text-[var(--color-success)] outline-none placeholder:text-[var(--color-text-secondary)]/70 focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
        />
        <button
          type="submit"
          disabled={!isConnected || !input.trim() || pending}
          className="px-3 py-1.5 text-athena-floor font-mono font-semibold bg-[var(--color-accent)]/[0.12] border border-[var(--color-accent)]/[0.25] text-[var(--color-accent)] rounded-[var(--radius)] hover:bg-[var(--color-accent)]/[0.2] disabled:opacity-30"
        >
          {pending ? t("commandPending") : tCommon("send")}
        </button>
      </form>
    </div>
  );
}
