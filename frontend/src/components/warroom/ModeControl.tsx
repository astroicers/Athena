// Copyright 2026 Athena Contributors
// SPEC-052: OODA Mode Control — Segmented Control with confirmation dialog

"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

interface ModeControlProps {
  isAutoMode: boolean;
  onToggle: () => void;
  isLoading?: boolean;
}

export function ModeControl({ isAutoMode, onToggle, isLoading }: ModeControlProps) {
  const t = useTranslations("CommandBar");
  const [showConfirm, setShowConfirm] = useState(false);

  const handleClick = () => {
    setShowConfirm(true);
  };

  const handleConfirm = () => {
    setShowConfirm(false);
    onToggle();
  };

  return (
    <div className="relative flex items-center">
      {/* Segmented Control */}
      <div className="flex items-center rounded border border-[var(--color-border)] overflow-hidden">
        <button
          onClick={() => !isAutoMode && handleClick()}
          disabled={isLoading}
          className={`px-3 py-1 text-athena-floor font-mono transition-all duration-200 ${
            isAutoMode
              ? "bg-[var(--color-success)]/15 text-[var(--color-success)] font-semibold"
              : "text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)]"
          }`}
        >
          {isAutoMode && (
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--color-success)] mr-1.5 animate-pulse" />
          )}
          {t("autonomousMode")}
        </button>
        <div className="w-px h-4 bg-[var(--color-border)]" />
        <button
          onClick={() => isAutoMode && handleClick()}
          disabled={isLoading}
          className={`px-3 py-1 text-athena-floor font-mono transition-all duration-200 ${
            !isAutoMode
              ? "bg-[var(--color-accent)]/15 text-[var(--color-accent)] font-semibold"
              : "text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-elevated)]"
          }`}
        >
          {t("manualMode")}
        </button>
      </div>

      {/* Confirmation Popover */}
      {showConfirm && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowConfirm(false)}
          />
          {/* Popover */}
          <div className="absolute right-0 top-full mt-2 z-50 w-64 rounded border border-[var(--color-border)] bg-[var(--color-bg-surface)] shadow-lg p-3">
            <p className="text-athena-floor font-mono text-[var(--color-text-primary)] mb-3">
              {isAutoMode
                ? t("confirmManual")
                : t("confirmAutonomous")}
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-3 py-1 rounded text-athena-floor font-mono text-[var(--color-text-tertiary)] border border-[var(--color-border)] hover:bg-[var(--color-bg-elevated)] transition-colors"
              >
                {t("cancel")}
              </button>
              <button
                onClick={handleConfirm}
                className={`px-3 py-1 rounded text-athena-floor font-mono font-semibold transition-colors ${
                  isAutoMode
                    ? "bg-[var(--color-accent)]/20 text-[var(--color-accent)] border border-[var(--color-accent)]/40 hover:bg-[var(--color-accent)]/30"
                    : "bg-[var(--color-success)]/20 text-[var(--color-success)] border border-[var(--color-success)]/40 hover:bg-[var(--color-success)]/30"
                }`}
              >
                {t("confirm")}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
