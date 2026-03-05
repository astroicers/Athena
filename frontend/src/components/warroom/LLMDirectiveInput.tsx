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

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { OODAPhase } from "@/types/enums";

interface LLMDirectiveInputProps {
  operationId: string;
  currentOodaPhase: OODAPhase | null;
  onSubmit: (directive: string) => Promise<void>;
}

export function LLMDirectiveInput({
  currentOodaPhase,
  onSubmit,
}: LLMDirectiveInputProps) {
  const t = useTranslations("WarRoom");
  const [directive, setDirective] = useState("");
  const [lastDirective, setLastDirective] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  // Highlight when cycle is idle (between cycles)
  const isCycleIdle = currentOodaPhase === null;

  async function handleSubmit() {
    const trimmed = directive.trim();
    if (!trimmed || sending) return;
    setSending(true);
    try {
      await onSubmit(trimmed);
      setLastDirective(trimmed);
      setDirective("");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="px-3 py-2 space-y-1">
      {lastDirective && (
        <div className="text-[10px] font-mono text-athena-text-secondary/60 truncate">
          {t("lastDirective")}: {lastDirective}
        </div>
      )}
      <div
        className={`flex gap-2 items-end border rounded-athena-sm p-1.5 transition-colors ${
          isCycleIdle
            ? "border-athena-accent animate-pulse"
            : "border-athena-border"
        }`}
      >
        <textarea
          value={directive}
          onChange={(e) => setDirective(e.target.value)}
          placeholder={t("directivePlaceholder")}
          rows={2}
          className="flex-1 bg-transparent text-xs font-mono text-athena-text resize-none outline-none placeholder:text-athena-text-secondary/40"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!directive.trim() || sending}
          className="shrink-0 px-3 py-1 text-[10px] font-mono uppercase tracking-wider bg-athena-accent/20 text-athena-accent border border-athena-accent/50 rounded-athena-sm hover:bg-athena-accent/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {t("directiveSend")}
        </button>
      </div>
    </div>
  );
}
