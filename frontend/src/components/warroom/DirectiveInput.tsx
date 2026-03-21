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

import { useState } from "react";
import { useTranslations } from "next-intl";

interface DirectiveInputProps {
  iterationId: string;
  autoMode: boolean;
  onToggleAutoMode: () => void;
  onSubmit: (directive: string) => void;
  submittedDirective?: string;
  aiSuggestion?: string;
}

export function DirectiveInput({
  iterationId,
  autoMode,
  onToggleAutoMode,
  onSubmit,
  submittedDirective,
  aiSuggestion,
}: DirectiveInputProps) {
  const t = useTranslations("WarRoom");
  const [draft, setDraft] = useState("");

  const handleSubmit = () => {
    if (draft.trim()) {
      onSubmit(draft.trim());
      setDraft("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="bg-athena-elevated border border-[var(--color-border)] rounded-[var(--radius)] p-3 font-mono">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-athena-text-tertiary uppercase tracking-wider font-semibold">
          {t("nextDirective")}
        </span>

        {/* Auto Mode toggle */}
        <button
          onClick={onToggleAutoMode}
          className="flex items-center gap-2 text-[10px] uppercase tracking-wider"
          type="button"
        >
          <span className="text-athena-text-tertiary">{t("autoMode")}</span>
          <span
            className={`relative inline-flex h-4 w-7 items-center rounded-full transition-colors ${
              autoMode ? "bg-athena-accent" : "bg-athena-border"
            }`}
          >
            <span
              className={`inline-block h-3 w-3 rounded-full bg-white transition-transform ${
                autoMode ? "translate-x-3.5" : "translate-x-0.5"
              }`}
            />
          </span>
        </button>
      </div>

      {/* Auto mode ON */}
      {autoMode && (
        <p className="text-xs text-athena-accent">
          {t("autoModeOn")}
        </p>
      )}

      {/* Auto mode OFF */}
      {!autoMode && !submittedDirective && (
        <div className="flex flex-col gap-2">
          {/* AI suggestion */}
          {aiSuggestion && (
            <p className="text-[11px] text-athena-text-tertiary">
              AI suggests: {aiSuggestion}
            </p>
          )}

          {/* Textarea */}
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter your directive..."
            rows={2}
            className="bg-athena-bg border border-[var(--color-border)] rounded-[var(--radius)] p-2 text-xs text-athena-text-light placeholder:text-athena-text-tertiary resize-none focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)] font-mono"
          />

          {/* Submit button */}
          <button
            onClick={handleSubmit}
            disabled={!draft.trim()}
            type="button"
            className="self-start bg-athena-surface border border-[var(--color-border)] text-athena-text text-[10px] uppercase tracking-wider font-semibold px-3 py-1.5 rounded-[var(--radius)] hover:bg-athena-elevated transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {t("submitDirective")}
          </button>
        </div>
      )}

      {/* Submitted directive */}
      {submittedDirective && (
        <div className="border-l-[3px] border-[var(--color-accent)] pl-3 py-1 mt-1">
          <span className="text-xs text-athena-text-secondary">
            {submittedDirective}
          </span>
        </div>
      )}
    </div>
  );
}
