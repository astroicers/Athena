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

import { useTranslations } from "next-intl";
import { RiskLevel } from "@/types/enums";

const RISK_STYLES: Record<string, { labelKey: "lowRisk" | "mediumRisk" | "highRisk" | "critical" }> = {
  [RiskLevel.LOW]: { labelKey: "lowRisk" },
  [RiskLevel.MEDIUM]: { labelKey: "mediumRisk" },
  [RiskLevel.HIGH]: { labelKey: "highRisk" },
  [RiskLevel.CRITICAL]: { labelKey: "critical" },
};

interface HexConfirmModalProps {
  isOpen: boolean;
  title: string;
  riskLevel: RiskLevel;
  onConfirm: () => void;
  onCancel: () => void;
}

export function HexConfirmModal({
  isOpen,
  title,
  riskLevel,
  onConfirm,
  onCancel,
}: HexConfirmModalProps) {
  const t = useTranslations("HexConfirm");
  const tCommon = useTranslations("Common");

  if (!isOpen) return null;

  const style = RISK_STYLES[riskLevel] || RISK_STYLES[RiskLevel.MEDIUM];
  const isCritical = riskLevel === RiskLevel.CRITICAL;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center">
      <div
        className="w-[420px] bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius)] overflow-hidden"
      >
        {/* Warning bar */}
        <div className="bg-[var(--color-error)]/[0.12] px-4 py-3 flex justify-center">
          <span className="text-xs font-mono font-bold text-[var(--color-error)] uppercase">
            {t(style.labelKey)}
          </span>
        </div>

        {/* Body */}
        <div className="px-6 py-5 text-center">
          <h2 className="text-base font-mono font-bold text-[var(--color-text-primary)]">
            {title}
          </h2>

          {isCritical && (
            <p className="text-xs font-mono text-[var(--color-text-secondary)] mt-2 leading-relaxed">
              {t("criticalWarning")}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-center gap-4 px-6 py-4 border-t border-[var(--color-border)]">
          <button
            onClick={onCancel}
            className="px-6 py-2 text-xs font-mono font-semibold bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)] rounded-[var(--radius)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)] transition-colors"
          >
            {tCommon("abort")}
          </button>
          <button
            onClick={onConfirm}
            className="px-6 py-2 text-xs font-mono font-semibold bg-[var(--color-error)]/[0.12] border border-[var(--color-error)]/[0.25] rounded-[var(--radius)] text-[var(--color-error)] hover:bg-[var(--color-error)]/20 transition-colors"
          >
            {isCritical ? t("confirmExecute") : tCommon("execute")}
          </button>
        </div>
      </div>
    </div>
  );
}
