// Copyright 2026 Athena Contributors
//
// Use of this software is governed by the Business Source License 1.1
// included in the LICENSE file.
//
// Change Date: Four years from release date of each version
// Change License: Apache License, Version 2.0
//
// For commercial licensing, contact: [TODO: contact email]

"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useTerminal } from "@/hooks/useTerminal";

interface TerminalPanelProps {
  operationId: string;
  targetId: string;
  targetName: string;
  targetIp: string;
  onClose: () => void;
}

export function TerminalPanel({
  operationId,
  targetId,
  targetName,
  targetIp,
  onClose,
}: TerminalPanelProps) {
  const t = useTranslations("Terminal");
  const tCommon = useTranslations("Common");
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { entries, prompt, isConnected, sendCommand, clear } = useTerminal(
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-athena-bg/80 backdrop-blur-sm">
      <div
        className="bg-athena-bg border border-athena-border rounded-athena-md shadow-2xl flex flex-col"
        style={{ width: "720px", height: "480px" }}
        onClick={() => inputRef.current?.focus()}
      >
        {/* Title bar */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-athena-border bg-athena-surface rounded-t-athena-md shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-athena-success">●</span>
            <span className="text-xs font-mono text-athena-text">
              {t("title")} {targetName} ({targetIp})
            </span>
            {!isConnected && (
              <span className="text-[10px] font-mono text-athena-error">{tCommon("disconnected")}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={clear}
              className="text-[10px] font-mono text-athena-text-secondary hover:text-athena-accent px-1"
            >
              {tCommon("clear")}
            </button>
            <button
              onClick={onClose}
              className="text-[10px] font-mono text-athena-text-secondary hover:text-athena-error px-1"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Terminal output */}
        <div className="flex-1 overflow-y-auto p-3 font-mono text-xs leading-relaxed">
          {entries.map((entry, i) => (
            <div key={i}>
              {entry.type === "input" ? (
                <div className="text-athena-accent">
                  <span className="text-athena-text-secondary/60">{prompt}</span>
                  {entry.text}
                </div>
              ) : entry.type === "error" ? (
                <div className="text-athena-error">{entry.text}</div>
              ) : entry.type === "system" ? (
                <div className="text-athena-text-secondary/60 italic">{entry.text}</div>
              ) : (
                <pre className="text-athena-text whitespace-pre-wrap break-all">{entry.text}</pre>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-2 px-3 py-2 border-t border-athena-border shrink-0"
        >
          <span className="text-athena-text-secondary/60 font-mono text-xs shrink-0">
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
            className="flex-1 bg-transparent font-mono text-xs text-athena-accent outline-none placeholder-athena-text-secondary/40"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
          />
          <button
            type="submit"
            disabled={!isConnected || !input.trim()}
            className="text-[10px] font-mono text-athena-text-secondary hover:text-athena-accent disabled:opacity-30 px-1"
          >
            {tCommon("send")}
          </button>
        </form>
      </div>
    </div>
  );
}
