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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0A0E17]/80 backdrop-blur-sm">
      <div
        className="bg-[#0A0E17] border border-[#1f2937] rounded-athena-md shadow-2xl flex flex-col"
        style={{ width: "720px", height: "480px" }}
        onClick={() => inputRef.current?.focus()}
      >
        {/* Title bar */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-[#1f2937] bg-[#111827] rounded-t-lg shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-[#22C55E]">●</span>
            <span className="text-xs font-mono text-[#e5e7eb]">
              {t("title")} {targetName} ({targetIp})
            </span>
            {!isConnected && (
              <span className="text-sm font-mono text-[#EF4444]">{tCommon("disconnected")}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={clear}
              className="text-sm font-mono text-[#9ca3af] hover:text-[#3b82f6] px-1"
            >
              {tCommon("clear")}
            </button>
            <button
              onClick={onClose}
              className="text-sm font-mono text-[#9ca3af] hover:text-[#EF4444] px-1"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Terminal output */}
        <div className="relative flex-1 overflow-y-auto p-3 font-mono text-xs leading-relaxed athena-scanline">
          {entries.map((entry, i) => (
            <div key={i}>
              {entry.type === "input" ? (
                <div className="text-[#3b82f6]">
                  <span className="text-[#9ca3af]">{prompt}</span>
                  {entry.text}
                </div>
              ) : entry.type === "error" ? (
                <div className="text-[#EF4444]">{entry.text}</div>
              ) : entry.type === "system" ? (
                <div className="text-[#9ca3af] italic">{entry.text}</div>
              ) : (
                <pre className="text-[#e5e7eb] whitespace-pre-wrap break-all">{entry.text}</pre>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-2 px-3 py-2 border-t border-[#1f2937] shrink-0"
        >
          <span className="text-[#9ca3af] font-mono text-xs shrink-0">
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
            className="flex-1 bg-transparent font-mono text-xs text-[#3b82f6] outline-none placeholder-[#6b7280]/70 focus:outline-none focus:ring-2 focus:ring-[#3b82f6]"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
          />
          <button
            type="submit"
            disabled={!isConnected || !input.trim()}
            className="text-sm font-mono text-[#9ca3af] hover:text-[#3b82f6] disabled:opacity-30 px-1"
          >
            {tCommon("send")}
          </button>
        </form>
      </div>
    </div>
  );
}
