// Copyright 2026 Athena Contributors
// SPEC-052: War Room Command Bar — Global directive input (bottom-fixed, cross-tab)

"use client";

import { useState, useCallback, useRef, type KeyboardEvent } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";

interface CommandBarProps {
  operationId: string;
  isAutoMode: boolean;
  onToggleMode: () => void;
  onCycleTriggered?: () => void;
  aiSuggestion?: string;
}

export function CommandBar({
  operationId,
  isAutoMode,
  onToggleMode,
  onCycleTriggered,
  aiSuggestion,
}: CommandBarProps) {
  const t = useTranslations("CommandBar");
  const tToast = useTranslations("WarRoom");
  const [directive, setDirective] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(async () => {
    if (!directive.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      // If in auto mode, stop auto first (intervention)
      if (isAutoMode) {
        await api.delete(`/operations/${operationId}/ooda/auto-stop`);
        onToggleMode();
      }

      // Submit directive
      await api.post(`/operations/${operationId}/ooda/directive`, {
        directive: directive.trim(),
        scope: "next_cycle",
      });

      // Trigger OODA cycle
      await api.post(`/operations/${operationId}/ooda/trigger`);
      onCycleTriggered?.();

      setDirective("");
    } catch {
      // Error handling via toast in parent
    } finally {
      setIsSubmitting(false);
    }
  }, [directive, isSubmitting, isAutoMode, operationId, onToggleMode, onCycleTriggered]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const handleAdopt = useCallback(() => {
    if (aiSuggestion) {
      setDirective(aiSuggestion);
      inputRef.current?.focus();
    }
  }, [aiSuggestion]);

  return (
    <div className="border-t border-[var(--color-border)] bg-[var(--color-bg-surface)] px-4 py-2 flex flex-col gap-1.5">
      {/* AI suggestion row */}
      {aiSuggestion && !dismissed && (
        <div className="flex items-center gap-2 min-h-[20px]">
          <span className="text-athena-floor font-mono font-semibold text-[var(--color-accent)] shrink-0">
            AI:
          </span>
          <span className="text-athena-floor font-mono text-[var(--color-text-secondary)] flex-1 truncate">
            {aiSuggestion}
          </span>
          {!isAutoMode && (
            <>
              <button
                onClick={handleAdopt}
                className="shrink-0 text-athena-floor font-mono text-[var(--color-accent)] hover:text-[var(--color-text-primary)] transition-colors px-2 py-0.5 rounded border border-[var(--color-accent)]/30 hover:border-[var(--color-accent)]"
              >
                {t("adopt")}
              </button>
              <button
                onClick={() => setDismissed(true)}
                className="shrink-0 text-athena-floor font-mono text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] transition-colors px-2 py-0.5"
              >
                {t("dismiss")}
              </button>
            </>
          )}
          {isAutoMode && (
            <span className="shrink-0 text-[10px] font-mono text-[var(--color-success)] bg-[var(--color-success)]/10 px-2 py-0.5 rounded">
              AUTO
            </span>
          )}
        </div>
      )}

      {/* Input row */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 flex-1 h-8 rounded bg-[var(--color-bg-elevated)] border border-[var(--color-border)] focus-within:border-[var(--color-accent)] transition-colors px-2.5">
          <span className="text-[13px] font-mono font-bold text-[var(--color-text-tertiary)]">
            &gt;
          </span>
          <input
            ref={inputRef}
            type="text"
            value={directive}
            onChange={(e) => setDirective(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isAutoMode
                ? t("autonomousPlaceholder")
                : t("manualPlaceholder")
            }
            disabled={isSubmitting}
            className="flex-1 bg-transparent text-athena-floor font-mono text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] outline-none"
          />
        </div>

        {/* Execute / Intervene button */}
        <button
          onClick={handleSubmit}
          disabled={!directive.trim() || isSubmitting}
          className={`px-3.5 py-1.5 rounded text-athena-floor font-mono font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
            isAutoMode
              ? "bg-[#B4530920] border border-[var(--color-warning)] text-[var(--color-warning)] hover:bg-[#B4530940]"
              : "bg-[#1E609120] border border-[var(--color-accent)] text-[var(--color-accent)] hover:bg-[#1E609140]"
          }`}
        >
          {isAutoMode ? t("intervene") : t("execute")}
        </button>
      </div>
    </div>
  );
}
